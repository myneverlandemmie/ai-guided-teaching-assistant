"""智学导评 V0.2 后端入口。"""

from __future__ import annotations

import shutil
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlparse
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from starlette.concurrency import run_in_threadpool

from app.db.base import create_database_tables
from app.db.session import engine, get_db
from app.models.course import Course
from app.models.course_plan import CoursePlanUpload, PlannedLesson
from app.models.knowledge_outline import KnowledgeOutline
from app.models.lesson import Lesson, LessonMaterial
from app.services.course_plan.import_service import create_lessons_from_confirmed_planned_lessons, import_course_plan
from app.services.ai import provider as ai_provider
from app.services.ai.deepseek_client import DeepSeekProviderError
from app.services.ai.session_key_store import (
    SESSION_COOKIE_NAME,
    clear_session_api_key,
    delete_session_cookie,
    get_session_api_key,
    mask_api_key,
    resolve_session_id,
    set_session_cookie,
    set_session_api_key,
)
from app.services.lesson_materials.document_text_extractor import (
    LessonMaterialExtractionError,
    SUPPORTED_MATERIAL_SUFFIXES,
    extract_text_from_lesson_material,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
COURSE_PLAN_UPLOAD_DIR = PROJECT_ROOT / "data" / "uploads" / "course-plans"
LESSON_MATERIAL_UPLOAD_DIR = PROJECT_ROOT / "data" / "uploads" / "lesson-materials"
MATERIAL_TYPE_LABELS = {
    "pasted_text": "粘贴文本",
    "lesson_plan": "教案（DOCX）",
    "course_ppt": "课程 PPT（PPTX）",
    "training_guide": "实训指导书（MD / DOCX）",
    "supplementary": "补充资料（TXT / MD / DOCX / PPTX）",
    "text": "粘贴文本",
    "ppt_text": "课程 PPT（PPTX）",
    "other": "补充资料",
}
LESSON_STATUS_LABELS = {"draft": "草稿", "published": "已发布", "archived": "已归档"}
KNOWLEDGE_OUTLINE_STATUS_LABELS = {"draft": "草稿", "reviewed": "已复核", "published": "已发布"}
DEFAULT_MATERIAL_TITLE_LABELS = {
    "pasted_text": "粘贴文本",
    "lesson_plan": "教案",
    "course_ppt": "课程PPT",
    "training_guide": "实训指导书",
    "supplementary": "补充资料",
}


def sanitize_next_path(next_path: str | None) -> str | None:
    """清洗 AI 设置页返回路径，只允许站内相对路径。

    Args:
        next_path: 用户提供的返回路径。

    Returns:
        合法时返回原路径；非法或为空时返回 None。

    Raises:
        不主动抛出业务异常。
    """

    if not next_path:
        return None

    if not next_path.startswith("/") or next_path.startswith("//"):
        return None
    if "\\" in next_path:
        return None
    if any(ord(char) < 32 or ord(char) == 127 for char in next_path):
        return None

    parsed_next = urlparse(next_path)
    if parsed_next.scheme or parsed_next.netloc:
        return None
    return next_path


def _ai_settings_context(
    session_id: str,
    message: str | None = None,
    next_path: str | None = None,
) -> dict[str, object]:
    """构造 AI 设置页面上下文。"""

    api_key = get_session_api_key(session_id)
    return {
        "is_api_key_set": bool(api_key),
        "masked_api_key": mask_api_key(api_key),
        "message": message,
        "ai_provider": ai_provider.get_ai_provider_name(),
        "next_path": sanitize_next_path(next_path),
    }


def require_same_origin(request: Request) -> None:
    """对关键 POST 做最小 same-origin 校验。"""

    source = request.headers.get("origin") or request.headers.get("referer")
    if not source:
        raise HTTPException(status_code=403, detail="出于安全考虑，请从系统页面提交表单。")

    parsed_source = urlparse(source)
    source_host = parsed_source.netloc
    request_host = request.headers.get("host", "")
    request_scheme = request.url.scheme
    if not source_host or source_host != request_host or parsed_source.scheme != request_scheme:
        raise HTTPException(status_code=403, detail="安全校验未通过，请从当前系统页面重新提交。")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """应用生命周期：启动时使用 create_all 初始化默认数据库。"""

    # V0.2 初期不用 Alembic，先用 create_all 支撑本地开发和演示。
    create_database_tables(engine)
    yield


app = FastAPI(title="AI Guided SQL Assessment", lifespan=lifespan)
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))
templates.env.filters["basename"] = lambda value: Path(value).name if value else ""


def _lesson_material_title_prefix(lesson: Lesson) -> str:
    """生成资料标题前缀，优先使用课次编码。"""

    return lesson.lesson_code or f"课次{lesson.id}"


def _generate_lesson_material_title(
    db: Session,
    lesson: Lesson,
    material_type: str,
    requested_title: str | None = None,
) -> str:
    """生成不重复的课次资料标题。

    Args:
        db: SQLAlchemy Session。
        lesson: 资料所属课次。
        material_type: 资料类型。
        requested_title: 教师手动填写的标题，可为空。

    Returns:
        当前课次内不重复的资料标题。

    Raises:
        SQLAlchemy 查询异常会继续向外抛出。
    """

    requested_title = (requested_title or "").strip()
    if requested_title:
        base_title = requested_title
    else:
        label = DEFAULT_MATERIAL_TITLE_LABELS.get(material_type, "资料")
        base_title = f"{_lesson_material_title_prefix(lesson)}-{label}"

    existing_titles = set(
        db.scalars(select(LessonMaterial.title).where(LessonMaterial.lesson_id == lesson.id)).all()
    )
    if base_title not in existing_titles:
        return base_title

    index = 2
    while f"{base_title}（{index}）" in existing_titles:
        index += 1
    return f"{base_title}（{index}）"


def _get_latest_knowledge_outline(db: Session, lesson_id: int) -> KnowledgeOutline | None:
    """读取课次最新一条知识主干。"""

    return db.scalar(
        select(KnowledgeOutline)
        .where(KnowledgeOutline.lesson_id == lesson_id)
        .order_by(KnowledgeOutline.id.desc())
    )


def get_or_create_demo_course(session: Session) -> Course:
    """读取或创建一个演示课程。

    Args:
        session: SQLAlchemy Session。

    Returns:
        Course 实例。

    Raises:
        SQLAlchemy 写入异常会继续向外抛出。
    """

    course = session.scalar(select(Course).order_by(Course.id))
    if course is not None:
        return course

    # 当前没有登录和课程管理，先创建一个 demo course 作为上传入口。
    course = Course(title="数据库应用与数据分析", semester="2025-2026-2", status="draft")
    session.add(course)
    session.commit()
    session.refresh(course)
    return course


@app.get("/")
async def read_root() -> RedirectResponse:
    """跳转到课程列表。"""

    return RedirectResponse(url="/courses", status_code=303)


@app.get("/ai/settings", response_class=HTMLResponse)
async def show_ai_settings(request: Request) -> HTMLResponse:
    """显示当前会话 API Key 设置页面。"""

    session_id, created = resolve_session_id(request)
    next_path = sanitize_next_path(request.query_params.get("next"))
    response = templates.TemplateResponse(
        request,
        "ai_settings.html",
        _ai_settings_context(session_id, next_path=next_path),
    )
    if created:
        set_session_cookie(response, session_id)
    return response


@app.post("/ai/settings", response_class=HTMLResponse)
async def save_ai_settings(
    request: Request,
) -> HTMLResponse:
    """保存当前会话临时 API Key，不入库。"""

    require_same_origin(request)
    form = await request.form()
    api_key = str(form.get("api_key", ""))
    next_path = sanitize_next_path(str(form.get("next", "")))
    session_id, created = resolve_session_id(request)
    cleaned_key = api_key.strip()
    if cleaned_key:
        # API Key 只进入内存会话映射，不写数据库、不写日志、不回显。
        set_session_api_key(session_id, cleaned_key)

    if cleaned_key and next_path:
        response = RedirectResponse(url=next_path, status_code=303)
        if created:
            set_session_cookie(response, session_id)
        return response

    message = "当前会话 API Key 已设置。" if cleaned_key else "请输入有效的 DeepSeek API Key。"
    status_code = 200 if cleaned_key else 400
    response = templates.TemplateResponse(
        request,
        "ai_settings.html",
        _ai_settings_context(session_id, message, next_path=next_path),
        status_code=status_code,
    )
    if created:
        set_session_cookie(response, session_id)
    return response


@app.post("/ai/settings/clear")
async def clear_ai_settings(request: Request) -> RedirectResponse:
    """清除当前会话临时 API Key。"""

    require_same_origin(request)
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    clear_session_api_key(session_id)
    response = RedirectResponse(url="/ai/settings", status_code=303)
    delete_session_cookie(response)
    return response


@app.get("/courses", response_class=HTMLResponse)
async def list_courses(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    """显示课程列表；没有课程时创建 demo course。"""

    get_or_create_demo_course(db)
    courses = db.scalars(select(Course).order_by(Course.id)).all()
    return templates.TemplateResponse(
        request,
        "courses.html",
        {"courses": courses},
    )


@app.get("/courses/{course_id}/course-plan/upload", response_class=HTMLResponse)
async def show_course_plan_upload_form(
    course_id: int,
    request: Request,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """显示授课计划上传表单。"""

    course = db.get(Course, course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="课程不存在")

    return templates.TemplateResponse(
        request,
        "course_plan_upload.html",
        {"course": course, "error_message": None},
    )


@app.post("/courses/{course_id}/course-plan/upload", response_class=HTMLResponse)
async def upload_course_plan(
    course_id: int,
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> Response:
    """接收 `.xlsx` 授课计划，保存运行时文件并调用导入 service。"""

    course = db.get(Course, course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="课程不存在")

    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        return templates.TemplateResponse(
            request,
            "course_plan_upload.html",
            {
                "course": course,
                "error_message": "当前仅支持 .xlsx 格式的授课计划，请重新上传。",
            },
            status_code=400,
        )

    COURSE_PLAN_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    safe_filename = Path(file.filename).name
    saved_path = COURSE_PLAN_UPLOAD_DIR / f"{uuid4().hex}-{safe_filename}"

    # 上传文件只保存到运行时目录，目录已由 .gitignore 排除。
    with saved_path.open("wb") as output_file:
        shutil.copyfileobj(file.file, output_file)

    result = import_course_plan(db, course, saved_path, safe_filename)
    upload = result["upload"]
    return RedirectResponse(url=f"/course-plan-uploads/{upload.id}", status_code=303)


@app.get("/course-plan-uploads/{upload_id}", response_class=HTMLResponse)
async def show_course_plan_preview(
    upload_id: int,
    request: Request,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """显示授课计划导入结果和 planned lessons 只读预览。"""

    upload = db.scalar(
        select(CoursePlanUpload)
        .options(selectinload(CoursePlanUpload.course))
        .where(CoursePlanUpload.id == upload_id)
    )
    if upload is None:
        raise HTTPException(status_code=404, detail="授课计划上传记录不存在")

    planned_lessons = db.scalars(
        select(PlannedLesson)
        .where(PlannedLesson.course_plan_upload_id == upload.id)
        .order_by(PlannedLesson.id)
    ).all()

    return templates.TemplateResponse(
        request,
        "course_plan_preview.html",
        {
            "upload": upload,
            "course": upload.course,
            "planned_lessons": planned_lessons,
            "planned_lesson_count": len(planned_lessons),
        },
    )


@app.post("/course-plan-uploads/{upload_id}/confirm")
async def confirm_course_plan_upload(
    upload_id: int,
    request: Request,
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """确认 planned lessons，并批量生成正式课次。"""

    upload = db.scalar(
        select(CoursePlanUpload)
        .options(selectinload(CoursePlanUpload.planned_lessons))
        .where(CoursePlanUpload.id == upload_id)
    )
    if upload is None:
        raise HTTPException(status_code=404, detail="授课计划上传记录不存在")

    form = await request.form()
    selected_ids = {int(value) for value in form.getlist("planned_lesson_ids")}
    planned_lessons = db.scalars(
        select(PlannedLesson)
        .where(PlannedLesson.course_plan_upload_id == upload.id)
        .order_by(PlannedLesson.id)
    ).all()

    # 业务规则：选中的 planned lesson 进入正式课次；未选中的本轮标记为 skipped。
    confirmed_ids: list[int] = []
    for planned_lesson in planned_lessons:
        if planned_lesson.id in selected_ids:
            planned_lesson.status = "confirmed"
            confirmed_ids.append(planned_lesson.id)
        else:
            planned_lesson.status = "skipped"
    db.commit()

    create_lessons_from_confirmed_planned_lessons(db, confirmed_ids)
    return RedirectResponse(url=f"/courses/{upload.course_id}/lessons", status_code=303)


@app.get("/courses/{course_id}/lessons", response_class=HTMLResponse)
async def list_lessons(
    course_id: int,
    request: Request,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """显示课程正式课次列表。"""

    course = db.get(Course, course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="课程不存在")

    lessons = db.scalars(
        select(Lesson)
        .where(Lesson.course_id == course.id)
        .order_by(Lesson.id)
    ).all()

    return templates.TemplateResponse(
        request,
        "lessons.html",
        {"course": course, "lessons": lessons, "lesson_count": len(lessons)},
    )


@app.get("/lessons/{lesson_id}", response_class=HTMLResponse)
async def show_lesson_detail(
    lesson_id: int,
    request: Request,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """显示正式课次详情和已添加教学材料。"""

    lesson = db.scalar(
        select(Lesson)
        .options(selectinload(Lesson.materials))
        .where(Lesson.id == lesson_id)
    )
    if lesson is None:
        raise HTTPException(status_code=404, detail="课次不存在")

    materials = db.scalars(
        select(LessonMaterial)
        .where(LessonMaterial.lesson_id == lesson.id)
        .order_by(LessonMaterial.id.desc())
    ).all()
    knowledge_outline = _get_latest_knowledge_outline(db, lesson.id)

    return templates.TemplateResponse(
        request,
        "lesson_detail.html",
        {
            "lesson": lesson,
            "materials": materials,
            "error_message": None,
            "material_type_labels": MATERIAL_TYPE_LABELS,
            "lesson_status_labels": LESSON_STATUS_LABELS,
            "knowledge_outline": knowledge_outline,
            "knowledge_outline_status_labels": KNOWLEDGE_OUTLINE_STATUS_LABELS,
        },
    )


def _lesson_material_context(db: Session, lesson: Lesson, error_message: str | None = None) -> dict[str, object]:
    """构造课次材料页面上下文。"""

    materials = db.scalars(
        select(LessonMaterial)
        .where(LessonMaterial.lesson_id == lesson.id)
        .order_by(LessonMaterial.id.desc())
    ).all()
    knowledge_outline = _get_latest_knowledge_outline(db, lesson.id)
    return {
        "lesson": lesson,
        "materials": materials,
        "error_message": error_message,
        "material_type_labels": MATERIAL_TYPE_LABELS,
        "lesson_status_labels": LESSON_STATUS_LABELS,
        "knowledge_outline": knowledge_outline,
        "knowledge_outline_status_labels": KNOWLEDGE_OUTLINE_STATUS_LABELS,
    }


@app.post("/lessons/{lesson_id}/materials", response_class=HTMLResponse)
async def add_lesson_material(
    lesson_id: int,
    request: Request,
    title: str = Form(""),
    material_type: str = Form("pasted_text"),
    content: str = Form(""),
    files: list[UploadFile] | None = File(None),
    db: Session = Depends(get_db),
) -> Response:
    """为课次添加教学材料，支持粘贴文本和多文件上传。"""

    lesson = db.get(Lesson, lesson_id)
    if lesson is None:
        raise HTTPException(status_code=404, detail="课次不存在")

    title_text = title.strip()
    uploaded_files = [uploaded_file for uploaded_file in (files or []) if uploaded_file.filename]
    if material_type == "pasted_text":
        material_content = content.strip()
        if not material_content:
            return templates.TemplateResponse(
                request,
                "lesson_detail.html",
                _lesson_material_context(db, lesson, "请选择“粘贴文本”并填写文本内容。"),
                status_code=400,
            )
        material = LessonMaterial(
            lesson_id=lesson.id,
            material_type=material_type,
            title=_generate_lesson_material_title(db, lesson, material_type, title_text),
            content=material_content,
            file_path=None,
        )
        db.add(material)
        db.commit()
        return RedirectResponse(url=f"/lessons/{lesson.id}", status_code=303)

    if not uploaded_files:
        return templates.TemplateResponse(
            request,
            "lesson_detail.html",
            _lesson_material_context(db, lesson, "请选择一个或多个 .txt / .md / .docx / .pptx 文件。"),
            status_code=400,
        )

    LESSON_MATERIAL_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []
    created_count = 0
    multiple_files = len(uploaded_files) > 1
    for uploaded_file in uploaded_files:
        safe_filename = Path(uploaded_file.filename or "lesson-material").name
        suffix = Path(safe_filename).suffix.lower()
        if suffix not in SUPPORTED_MATERIAL_SUFFIXES:
            errors.append(f"{safe_filename}：暂不支持该文件类型。请上传 .txt / .md / .docx / .pptx；不支持 PDF、图片、扫描件和旧版 .doc / .ppt。")
            continue

        saved_path = LESSON_MATERIAL_UPLOAD_DIR / f"{uuid4().hex}-{safe_filename}"
        # 文件材料保存到运行时目录；目录由 .gitignore 排除，不进入公开仓库。
        file_bytes = await uploaded_file.read()
        saved_path.write_bytes(file_bytes)
        try:
            file_content = extract_text_from_lesson_material(saved_path, safe_filename)
        except LessonMaterialExtractionError as exc:
            errors.append(f"{safe_filename}：{exc} 如果提取结果不完整，请复制文字粘贴到文本框中补充。")
            saved_path.unlink(missing_ok=True)
            continue

        requested_title = f"{title_text} - {safe_filename}" if title_text and multiple_files else title_text
        material = LessonMaterial(
            lesson_id=lesson.id,
            material_type=material_type,
            title=_generate_lesson_material_title(db, lesson, material_type, requested_title),
            content=file_content,
            file_path=str(saved_path),
        )
        db.add(material)
        created_count += 1

    db.commit()
    if errors:
        message = "；".join(errors)
        if created_count:
            message = f"已成功添加 {created_count} 份资料。以下文件未能保存：{message}"
        return templates.TemplateResponse(
            request,
            "lesson_detail.html",
            _lesson_material_context(db, lesson, message),
            status_code=400,
        )

    return RedirectResponse(url=f"/lessons/{lesson.id}", status_code=303)


@app.post("/lesson-materials/{material_id}/delete")
async def delete_lesson_material(
    material_id: int,
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """删除课次教学资料，并尽量删除对应上传文件。"""

    material = db.get(LessonMaterial, material_id)
    if material is None:
        raise HTTPException(status_code=404, detail="资料不存在")

    lesson_id = material.lesson_id
    if material.file_path:
        Path(material.file_path).unlink(missing_ok=True)
    db.delete(material)
    db.commit()
    return RedirectResponse(url=f"/lessons/{lesson_id}", status_code=303)


@app.post("/lessons/{lesson_id}/knowledge-outline/generate")
async def generate_lesson_knowledge_outline(
    lesson_id: int,
    request: Request,
    db: Session = Depends(get_db),
) -> Response:
    """使用当前 AI Provider 为课次生成知识主干初稿。"""

    require_same_origin(request)
    lesson = db.get(Lesson, lesson_id)
    if lesson is None:
        raise HTTPException(status_code=404, detail="课次不存在")

    materials = db.scalars(
        select(LessonMaterial)
        .where(LessonMaterial.lesson_id == lesson.id)
        .order_by(LessonMaterial.id)
    ).all()
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    api_key = get_session_api_key(session_id)
    provider_name = ai_provider.get_ai_provider_name()
    if provider_name == "deepseek" and not api_key:
        return templates.TemplateResponse(
            request,
            "knowledge_outline.html",
            {
                "lesson": lesson,
                "outline": _get_latest_knowledge_outline(db, lesson.id),
                "knowledge_outline_status_labels": KNOWLEDGE_OUTLINE_STATUS_LABELS,
                "error_message": "请先设置当前会话 DeepSeek API Key，再生成知识主干。",
                "ai_provider": provider_name,
            },
            status_code=400,
        )
    lesson_for_ai = SimpleNamespace(
        lesson_code=lesson.lesson_code,
        title=lesson.title,
        content_summary=lesson.content_summary,
    )
    materials_for_ai = [SimpleNamespace(content=material.content) for material in materials]
    try:
        generated_outline = await run_in_threadpool(
            ai_provider.generate_knowledge_outline_with_provider,
            lesson_for_ai,
            materials_for_ai,
            api_key,
        )
    except DeepSeekProviderError as exc:
        return templates.TemplateResponse(
            request,
            "knowledge_outline.html",
            {
                "lesson": lesson,
                "outline": _get_latest_knowledge_outline(db, lesson.id),
                "knowledge_outline_status_labels": KNOWLEDGE_OUTLINE_STATUS_LABELS,
                "error_message": exc.user_message,
                "ai_provider": ai_provider.get_ai_provider_name(),
            },
            status_code=400,
        )

    # AI 初稿和教师编辑稿初始一致，后续必须由教师编辑保存。
    outline = KnowledgeOutline(
        lesson_id=lesson.id,
        ai_raw_output=generated_outline.content,
        edited_content=generated_outline.content,
        status="draft",
        generated_by_model=generated_outline.model_name,
    )
    db.add(outline)
    db.commit()
    return RedirectResponse(url=f"/lessons/{lesson.id}/knowledge-outline", status_code=303)


@app.get("/lessons/{lesson_id}/knowledge-outline", response_class=HTMLResponse)
async def show_lesson_knowledge_outline(
    lesson_id: int,
    request: Request,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """显示课次知识主干编辑页面。"""

    lesson = db.get(Lesson, lesson_id)
    if lesson is None:
        raise HTTPException(status_code=404, detail="课次不存在")

    outline = _get_latest_knowledge_outline(db, lesson.id)
    return templates.TemplateResponse(
        request,
        "knowledge_outline.html",
        {
            "lesson": lesson,
            "outline": outline,
            "knowledge_outline_status_labels": KNOWLEDGE_OUTLINE_STATUS_LABELS,
            "error_message": None,
            "ai_provider": ai_provider.get_ai_provider_name(),
        },
    )


@app.post("/knowledge-outlines/{outline_id}/save")
async def save_knowledge_outline(
    outline_id: int,
    edited_content: str = Form(...),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """保存教师编辑后的知识主干。"""

    outline = db.get(KnowledgeOutline, outline_id)
    if outline is None:
        raise HTTPException(status_code=404, detail="知识主干不存在")

    # 保存教师复核后的版本；后续页面使用 edited_content 展示。
    outline.edited_content = edited_content.strip()
    outline.status = "reviewed"
    db.commit()
    return RedirectResponse(url=f"/lessons/{outline.lesson_id}/knowledge-outline", status_code=303)
