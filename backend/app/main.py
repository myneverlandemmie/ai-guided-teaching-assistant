"""智学导评 V0.2 后端入口。"""

from __future__ import annotations

import shutil
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import quote, urlparse
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload
from starlette.concurrency import run_in_threadpool

from app.db.base import create_database_tables
from app.db.session import engine, get_db
from app.models.course import Course
from app.models.course_plan import CoursePlanUpload, PlannedLesson
from app.models.knowledge_outline import KnowledgeOutline
from app.models.lesson import Lesson, LessonMaterial
from app.models.lesson_draft import LESSON_DRAFT_TYPES, LessonDraft
from app.services.course_plan.import_service import create_lessons_from_confirmed_planned_lessons, import_course_plan
from app.services.course_management_service import (
    create_course,
    delete_course,
    get_or_create_default_course,
    rename_course,
)
from app.services.ai import provider as ai_provider
from app.services.ai.deepseek_client import DeepSeekProviderError
from app.services.ai.deepseek_client import (
    get_allowed_deepseek_models,
    get_default_deepseek_model,
    is_allowed_deepseek_model,
    normalize_model_name,
)
from app.services.ai.sanitizer import sanitize_text_for_outline
from app.services.ai.lesson_draft_ai_service import (
    generate_single_lesson_draft_with_ai,
)
from app.services.ai.lesson_draft_service import (
    DRAFT_TYPE_LABELS,
    DiagnosticQuestionBlock,
    parse_diagnostic_probe_question_blocks,
    write_chaoxing_template_xlsx,
)
from app.services.ai.session_key_store import (
    SESSION_COOKIE_NAME,
    clear_session_api_key,
    delete_session_cookie,
    get_session_api_key,
    get_session_selected_model,
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
from app.services.teaching_prep_reference_service import (
    TEACHING_PREP_REFERENCE_DRAFT_TYPE,
    generate_teaching_prep_reference,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
STATIC_DIR = Path(__file__).resolve().parent / "static"
COURSE_PLAN_UPLOAD_DIR = PROJECT_ROOT / "data" / "uploads" / "course-plans"
LESSON_MATERIAL_UPLOAD_DIR = PROJECT_ROOT / "data" / "uploads" / "lesson-materials"
CHAOXING_EXPORT_DIR = PROJECT_ROOT / "data" / "exports" / "chaoxing"
GUIDE_EXPORT_DIR = PROJECT_ROOT / "data" / "exports" / "guides"
MATERIAL_TYPE_LABELS = {
    "pasted_text": "粘贴文本",
    "lesson_plan": "教案",
    "course_ppt": "PPT课件",
    "training_guide": "实训指导书",
    "task_sheet": "任务书 / 学习单",
    "evaluation_sheet": "评价表 / 记录表",
    "supplementary": "补充材料",
    "text": "粘贴文本",
    "ppt_text": "PPT课件",
    "other": "其他",
}
LESSON_STATUS_LABELS = {"draft": "草稿", "published": "已发布", "archived": "已归档"}
KNOWLEDGE_OUTLINE_STATUS_LABELS = {"draft": "草稿", "reviewed": "已复核", "published": "已发布"}
LESSON_DRAFT_STATUS_LABELS = {"draft": "草稿", "reviewed": "已复核"}
LESSON_DRAFT_DOWNLOAD_NAME_PARTS = {
    "guide_low": "core_learning_guide",
    "guide_mid": "enhancement_task_pack",
    "guide_high": "extension_challenge_pack",
    TEACHING_PREP_REFERENCE_DRAFT_TYPE: "teaching_prep_reference_suggestions",
}
DEFAULT_MATERIAL_TITLE_LABELS = {
    "pasted_text": "粘贴文本",
    "lesson_plan": "教案",
    "course_ppt": "PPT课件",
    "training_guide": "实训指导书",
    "task_sheet": "任务书",
    "evaluation_sheet": "评价表",
    "supplementary": "补充材料",
    "other": "其他资料",
}
MATERIAL_CATEGORY_OPTIONS = [
    ("lesson_plan", "教案"),
    ("course_ppt", "PPT / 课件"),
    ("training_guide", "实训指导书"),
    ("task_sheet", "任务书 / 学习单"),
    ("evaluation_sheet", "评价表 / 记录表"),
    ("supplementary", "补充材料"),
    ("other", "其他"),
]


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
    allowed_models = get_allowed_deepseek_models()
    selected_model = get_session_selected_model(session_id) or get_default_deepseek_model()
    return {
        "is_api_key_set": bool(api_key),
        "masked_api_key": mask_api_key(api_key),
        "message": message,
        "ai_provider": ai_provider.get_ai_provider_name(),
        "next_path": sanitize_next_path(next_path),
        "allowed_models": allowed_models,
        "selected_model": selected_model,
        "default_model": get_default_deepseek_model(),
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
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))
templates.env.filters["basename"] = lambda value: Path(value).name if value else ""
templates.env.filters["splitext"] = lambda value: Path(value).suffix.lstrip(".") if value else ""


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


def _lesson_material_category_label(material: LessonMaterial) -> str:
    """返回教师可见的资料类别。"""

    return MATERIAL_TYPE_LABELS.get(material.material_type, MATERIAL_TYPE_LABELS.get("other", "其他"))


def _get_latest_knowledge_outline(db: Session, lesson_id: int) -> KnowledgeOutline | None:
    """读取课次最新一条知识主干。"""

    return db.scalar(
        select(KnowledgeOutline)
        .where(KnowledgeOutline.lesson_id == lesson_id)
        .order_by(KnowledgeOutline.id.desc())
    )


def _get_lesson_drafts(db: Session, lesson_id: int) -> list[LessonDraft]:
    """读取当前课次全部导学草稿。"""

    return db.scalars(
        select(LessonDraft)
        .where(LessonDraft.lesson_id == lesson_id)
        .order_by(LessonDraft.id)
    ).all()


def _get_lesson_draft_by_type(db: Session, lesson_id: int, draft_type: str) -> LessonDraft | None:
    """读取某课次指定类型草稿。"""

    return db.scalar(
        select(LessonDraft)
        .where(LessonDraft.lesson_id == lesson_id, LessonDraft.draft_type == draft_type)
        .order_by(LessonDraft.id.desc())
    )


def _learning_guide_dependency_message(draft_type: str, has_low: bool, has_mid: bool) -> str | None:
    """返回学生导学案任务包的依赖提示。"""

    if draft_type == "guide_mid" and not has_low:
        return "请先生成全班通用导学案，再生成巩固提升任务包。"
    if draft_type == "guide_high" and not has_mid:
        return "请先生成巩固提升任务包，再生成拓展探究任务包。"
    return None


def _upsert_lesson_drafts(
    db: Session,
    lesson: Lesson,
    outline: KnowledgeOutline | None,
    generated_drafts: list[object],
) -> None:
    """按 lesson_id + draft_type 更新当前草稿，不保留历史版本。"""

    existing_drafts = {
        draft.draft_type: draft
        for draft in db.scalars(select(LessonDraft).where(LessonDraft.lesson_id == lesson.id)).all()
    }
    for generated in generated_drafts:
        if generated.draft_type not in LESSON_DRAFT_TYPES:
            continue
        draft = existing_drafts.get(generated.draft_type)
        if draft is None:
            draft = LessonDraft(
                lesson_id=lesson.id,
                source_outline_id=outline.id if outline else None,
                draft_type=generated.draft_type,
                title=generated.title,
                content=generated.content,
                status="draft",
                generated_by=generated.generated_by,
            )
            db.add(draft)
        else:
            draft.source_outline_id = outline.id if outline else None
            draft.title = generated.title
            draft.content = generated.content
            draft.status = "draft"
            draft.generated_by = generated.generated_by


def _safe_export_part(value: str | None, fallback: str) -> str:
    """生成安全的导出文件名片段。"""

    cleaned = "".join(char for char in (value or "") if char.isalnum() or char in {"-", "_"})
    return cleaned or fallback


def _safe_export_filename(filename: str | None, suffix: str) -> str | None:
    """只允许下载固定导出目录下的简单文件名。"""

    if not filename:
        return None
    basename = Path(filename).name
    if basename != filename or "\\" in filename or not basename.endswith(suffix):
        return None
    return basename


def _append_query_param(path: str, key: str, value: str) -> str:
    """向站内路径追加简单查询参数。"""

    separator = "&" if "?" in path else "?"
    return f"{path}{separator}{key}={quote(value, safe='')}"


def _distribution(items: list[str]) -> list[dict[str, object]]:
    """生成页面使用的轻量分布数据。"""

    counts: dict[str, int] = {}
    for item in items:
        label = item.strip() or "不详"
        if label in {"基础"}:
            label = "易 / 基础"
        elif label in {"中等"}:
            label = "中 / 中等"
        elif label in {"提高"}:
            label = "难 / 提高"
        counts[label] = counts.get(label, 0) + 1
    total = sum(counts.values()) or 1
    return [
        {
            "label": label,
            "count": count,
            "percent": round(count / total * 100),
            "percent_display": f"{count / total * 100:.1f}%",
        }
        for label, count in counts.items()
    ]


def _diagnostic_probe_view_context(draft: LessonDraft | None) -> dict[str, object]:
    """构造课前学情测试 V2 的题卡与结构概览。"""

    question_blocks: list[DiagnosticQuestionBlock] = []
    if draft is not None:
        question_blocks = parse_diagnostic_probe_question_blocks(draft.content)
    return {
        "question_blocks": question_blocks,
        "question_type_distribution": _distribution([block.question.question_type for block in question_blocks]),
        "difficulty_distribution": _distribution([block.question.difficulty for block in question_blocks]),
    }


def get_or_create_demo_course(session: Session) -> Course:
    """读取或创建默认测试课程。

    Args:
        session: SQLAlchemy Session。

    Returns:
        Course 实例。

    Raises:
        SQLAlchemy 写入异常会继续向外抛出。
    """

    return get_or_create_default_course(session)


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
    selected_model = normalize_model_name(str(form.get("selected_model", ""))) or get_default_deepseek_model()
    next_path = sanitize_next_path(str(form.get("next", "")))
    session_id, created = resolve_session_id(request)
    cleaned_key = api_key.strip()
    if not is_allowed_deepseek_model(selected_model):
        response = templates.TemplateResponse(
            request,
            "ai_settings.html",
            _ai_settings_context(session_id, "模型配置无效，请选择当前允许列表中的 DeepSeek V4 模型。", next_path=next_path),
            status_code=400,
        )
        if created:
            set_session_cookie(response, session_id)
        return response

    if cleaned_key:
        # API Key 只进入内存会话映射，不写数据库、不写日志、不回显。
        set_session_api_key(session_id, cleaned_key, selected_model)

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
        {"courses": courses, "error_message": None},
    )


def _course_lesson_counts(db: Session, courses: list[Course]) -> dict[int, int]:
    """统计课程下正式课次数量。"""

    if not courses:
        return {}
    course_ids = [course.id for course in courses]
    rows = db.execute(
        select(Lesson.course_id, func.count(Lesson.id))
        .where(Lesson.course_id.in_(course_ids))
        .group_by(Lesson.course_id)
    ).all()
    return {course_id: count for course_id, count in rows}


@app.get("/ui-v2/courses", response_class=HTMLResponse)
async def list_courses_v2(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    """课程中心 V2 preview。"""

    get_or_create_demo_course(db)
    courses = db.scalars(select(Course).order_by(Course.id)).all()
    return templates.TemplateResponse(
        request,
        "courses_v2.html",
        {
            "courses": courses,
            "lesson_counts": _course_lesson_counts(db, courses),
            "error_message": None,
        },
    )


@app.post("/courses/create", response_class=HTMLResponse)
async def create_course_route(
    request: Request,
    title: str = Form(""),
    return_to: str = Form("/courses"),
    db: Session = Depends(get_db),
) -> Response:
    """创建课程并返回课程中心。"""

    redirect_to = sanitize_next_path(return_to) or "/courses"
    try:
        create_course(db, title)
    except ValueError as exc:
        courses = db.scalars(select(Course).order_by(Course.id)).all()
        template_name = "courses_v2.html" if redirect_to == "/ui-v2/courses" else "courses.html"
        context: dict[str, object] = {"courses": courses, "error_message": str(exc)}
        if template_name == "courses_v2.html":
            context["lesson_counts"] = _course_lesson_counts(db, courses)
        return templates.TemplateResponse(
            request,
            template_name,
            context,
            status_code=400,
        )
    return RedirectResponse(url=redirect_to, status_code=303)


@app.post("/courses/{course_id}/rename", response_class=HTMLResponse)
async def rename_course_route(
    course_id: int,
    request: Request,
    title: str = Form(""),
    return_to: str = Form("/courses"),
    db: Session = Depends(get_db),
) -> Response:
    """修改课程名称。"""

    redirect_to = sanitize_next_path(return_to) or "/courses"
    course = db.get(Course, course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="课程不存在")

    try:
        rename_course(db, course, title)
    except ValueError as exc:
        courses = db.scalars(select(Course).order_by(Course.id)).all()
        template_name = "courses_v2.html" if redirect_to == "/ui-v2/courses" else "courses.html"
        context = {"courses": courses, "error_message": str(exc)}
        if template_name == "courses_v2.html":
            context["lesson_counts"] = _course_lesson_counts(db, courses)
        return templates.TemplateResponse(
            request,
            template_name,
            context,
            status_code=400,
        )
    return RedirectResponse(url=redirect_to, status_code=303)


@app.post("/courses/{course_id}/delete")
async def delete_course_route(
    course_id: int,
    return_to: str = Form("/courses"),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """删除课程及其关联课次数据。"""

    course = db.get(Course, course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="课程不存在")

    delete_course(db, course)
    return RedirectResponse(url=sanitize_next_path(return_to) or "/courses", status_code=303)


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

    return_to = sanitize_next_path(request.query_params.get("return_to")) or "/courses"
    return templates.TemplateResponse(
        request,
        "course_plan_upload.html",
        {"course": course, "error_message": None, "return_to": return_to},
    )


@app.post("/courses/{course_id}/course-plan/upload", response_class=HTMLResponse)
async def upload_course_plan(
    course_id: int,
    request: Request,
    file: UploadFile = File(...),
    return_to: str = Form(""),
    db: Session = Depends(get_db),
) -> Response:
    """接收 `.xlsx` 授课计划，保存运行时文件并调用导入 service。"""

    course = db.get(Course, course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="课程不存在")

    safe_return_to = sanitize_next_path(return_to) or "/courses"
    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        return templates.TemplateResponse(
            request,
            "course_plan_upload.html",
            {
                "course": course,
                "error_message": "当前仅支持 .xlsx 格式的授课计划，请重新上传。",
                "return_to": safe_return_to,
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
    preview_url = f"/course-plan-uploads/{upload.id}"
    if safe_return_to != "/courses":
        preview_url = f"{preview_url}?return_to={quote(safe_return_to, safe='')}"
    return RedirectResponse(url=preview_url, status_code=303)


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
    return_to = sanitize_next_path(request.query_params.get("return_to")) or "/courses"

    return templates.TemplateResponse(
        request,
        "course_plan_preview.html",
        {
            "upload": upload,
            "course": upload.course,
            "planned_lessons": planned_lessons,
            "planned_lesson_count": len(planned_lessons),
            "return_to": return_to,
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
    return_to = sanitize_next_path(str(form.get("return_to", ""))) or ""
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
        .options(selectinload(Lesson.planned_lesson))
        .where(Lesson.course_id == course.id)
        .order_by(Lesson.id)
    ).all()
    show_notes_column = any((lesson.planned_lesson and lesson.planned_lesson.notes.strip()) for lesson in lessons)

    return templates.TemplateResponse(
        request,
        "lessons.html",
        {
            "course": course,
            "lessons": lessons,
            "lesson_count": len(lessons),
            "show_notes_column": show_notes_column,
        },
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


@app.get("/ui-v2/lessons/{lesson_id}/materials-outline", response_class=HTMLResponse)
async def show_lesson_materials_outline_v2(
    lesson_id: int,
    request: Request,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """课次资料与知识主干 V2 preview。"""

    lesson = db.scalar(
        select(Lesson)
        .options(selectinload(Lesson.course))
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
    teaching_prep_reference = _get_lesson_draft_by_type(db, lesson.id, TEACHING_PREP_REFERENCE_DRAFT_TYPE)
    return templates.TemplateResponse(
        request,
        "lesson_materials_outline_v2.html",
        {
            "lesson": lesson,
            "materials": materials,
            "knowledge_outline": knowledge_outline,
            "material_type_labels": MATERIAL_TYPE_LABELS,
            "material_category_options": MATERIAL_CATEGORY_OPTIONS,
            "material_category_label": _lesson_material_category_label,
            "knowledge_outline_status_labels": KNOWLEDGE_OUTLINE_STATUS_LABELS,
            "teaching_prep_reference": teaching_prep_reference,
            "draft_status_labels": LESSON_DRAFT_STATUS_LABELS,
        },
    )


@app.get("/ui-v2/lessons/{lesson_id}/diagnostic-probe", response_class=HTMLResponse)
async def show_diagnostic_probe_v2(
    lesson_id: int,
    request: Request,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """课前学情测试 V2 preview。"""

    lesson = db.scalar(
        select(Lesson)
        .options(selectinload(Lesson.course))
        .where(Lesson.id == lesson_id)
    )
    if lesson is None:
        raise HTTPException(status_code=404, detail="课次不存在")

    draft = _get_lesson_draft_by_type(db, lesson.id, "diagnostic_probe")
    chaoxing_filename = _safe_export_filename(request.query_params.get("chaoxing_file"), ".xlsx")
    fallback_message = (
        "DeepSeek 响应较慢、调用失败或当前未设置 API Key，已回退为本地结构化草稿。你可以稍后重试，或减少材料后再生成。"
        if request.query_params.get("draft_fallback") == "1"
        else None
    )
    return templates.TemplateResponse(
        request,
        "diagnostic_probe_v2.html",
        {
            "lesson": lesson,
            "outline": _get_latest_knowledge_outline(db, lesson.id),
            "draft": draft,
            "draft_status_labels": LESSON_DRAFT_STATUS_LABELS,
            "chaoxing_export_url": f"/exports/chaoxing/{chaoxing_filename}" if chaoxing_filename else None,
            "fallback_message": fallback_message,
            **_diagnostic_probe_view_context(draft),
        },
    )


@app.get("/ui-v2/lessons/{lesson_id}/learning-guides", response_class=HTMLResponse)
async def show_learning_guides_v2(
    lesson_id: int,
    request: Request,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """学生导学案 V2 preview。"""

    lesson = db.scalar(
        select(Lesson)
        .options(selectinload(Lesson.course))
        .where(Lesson.id == lesson_id)
    )
    if lesson is None:
        raise HTTPException(status_code=404, detail="课次不存在")

    guide_drafts = {
        draft.draft_type: draft
        for draft in _get_lesson_drafts(db, lesson.id)
        if draft.draft_type in {"guide_low", "guide_mid", "guide_high"}
    }
    fallback_message = (
        "DeepSeek 响应较慢、调用失败或当前未设置 API Key，已回退为本地结构化草稿。你可以稍后重试，或减少材料后再生成。"
        if request.query_params.get("draft_fallback") == "1"
        else None
    )
    return templates.TemplateResponse(
        request,
        "learning_guides_v2.html",
        {
            "lesson": lesson,
            "outline": _get_latest_knowledge_outline(db, lesson.id),
            "guide_low": guide_drafts.get("guide_low"),
            "guide_mid": guide_drafts.get("guide_mid"),
            "guide_high": guide_drafts.get("guide_high"),
            "draft_status_labels": LESSON_DRAFT_STATUS_LABELS,
            "fallback_message": fallback_message,
            "dependency_message": request.query_params.get("dependency_message") or None,
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
        "material_category_options": MATERIAL_CATEGORY_OPTIONS,
        "material_category_label": _lesson_material_category_label,
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
    input_mode: str = Form(""),
    material_category: str = Form(""),
    content: str = Form(""),
    return_to: str = Form(""),
    files: list[UploadFile] | None = File(None),
    db: Session = Depends(get_db),
) -> Response:
    """为课次添加教学材料，支持粘贴文本和多文件上传。"""

    redirect_to = sanitize_next_path(return_to) or f"/lessons/{lesson_id}"
    lesson = db.get(Lesson, lesson_id)
    if lesson is None:
        raise HTTPException(status_code=404, detail="课次不存在")

    title_text = title.strip()
    effective_material_type = material_category.strip() or material_type
    if effective_material_type not in MATERIAL_TYPE_LABELS:
        effective_material_type = "supplementary"
    uploaded_files = [uploaded_file for uploaded_file in (files or []) if uploaded_file.filename]
    is_pasted_text = input_mode == "pasted_text" or (not input_mode and material_type == "pasted_text")
    if is_pasted_text:
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
            material_type=effective_material_type,
            title=_generate_lesson_material_title(db, lesson, effective_material_type, title_text),
            content=material_content,
            file_path=None,
        )
        db.add(material)
        db.commit()
        return RedirectResponse(url=redirect_to, status_code=303)

    if not uploaded_files:
        return templates.TemplateResponse(
            request,
            "lesson_detail.html",
            _lesson_material_context(db, lesson, "请选择一个或多个 .txt / .md / .docx / .pptx / .xlsx 文件；暂不支持 .xls。"),
            status_code=400,
        )

    LESSON_MATERIAL_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []
    created_count = 0
    multiple_files = len(uploaded_files) > 1
    for uploaded_file in uploaded_files:
        safe_filename = Path(uploaded_file.filename or "lesson-material").name
        suffix = Path(safe_filename).suffix.lower()
        if suffix == ".xls":
            errors.append(f"{safe_filename}：暂不支持旧版 .xls 表格文件。请另存为 .xlsx 后上传，或复制表格内容粘贴到文本框。")
            continue
        if suffix not in SUPPORTED_MATERIAL_SUFFIXES:
            errors.append(f"{safe_filename}：暂不支持该文件类型。请上传 .txt / .md / .docx / .pptx / .xlsx；不支持 .xls、PDF、图片、扫描件和旧版 .doc / .ppt。")
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
            material_type=effective_material_type,
            title=_generate_lesson_material_title(db, lesson, effective_material_type, requested_title),
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

    return RedirectResponse(url=redirect_to, status_code=303)


@app.post("/lesson-materials/{material_id}/delete")
async def delete_lesson_material(
    material_id: int,
    return_to: str = Form(""),
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
    return RedirectResponse(url=sanitize_next_path(return_to) or f"/lessons/{lesson_id}", status_code=303)


@app.post("/lessons/{lesson_id}/knowledge-outline/generate")
async def generate_lesson_knowledge_outline(
    lesson_id: int,
    request: Request,
    return_to: str = Form(""),
    db: Session = Depends(get_db),
) -> Response:
    """使用当前 AI Provider 为课次生成知识主干初稿。"""

    require_same_origin(request)
    redirect_to = sanitize_next_path(return_to) or f"/lessons/{lesson_id}/knowledge-outline"
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
    selected_model = get_session_selected_model(session_id) or get_default_deepseek_model()
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
            selected_model,
        )
    except DeepSeekProviderError as exc:
        if redirect_to.startswith("/ui-v2/"):
            materials = db.scalars(
                select(LessonMaterial)
                .where(LessonMaterial.lesson_id == lesson.id)
                .order_by(LessonMaterial.id.desc())
            ).all()
            return templates.TemplateResponse(
                request,
                "lesson_materials_outline_v2.html",
                {
                    "lesson": lesson,
                    "materials": materials,
                    "knowledge_outline": _get_latest_knowledge_outline(db, lesson.id),
                    "material_type_labels": MATERIAL_TYPE_LABELS,
                    "material_category_options": MATERIAL_CATEGORY_OPTIONS,
                    "material_category_label": _lesson_material_category_label,
                    "knowledge_outline_status_labels": KNOWLEDGE_OUTLINE_STATUS_LABELS,
                    "teaching_prep_reference": _get_lesson_draft_by_type(
                        db,
                        lesson.id,
                        TEACHING_PREP_REFERENCE_DRAFT_TYPE,
                    ),
                    "draft_status_labels": LESSON_DRAFT_STATUS_LABELS,
                    "error_message": exc.user_message,
                },
                status_code=400,
            )
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

    sanitized_generated_content = sanitize_text_for_outline(generated_outline.content)
    # AI 初稿和教师编辑稿初始一致，后续必须由教师编辑保存。
    outline = KnowledgeOutline(
        lesson_id=lesson.id,
        ai_raw_output=sanitized_generated_content,
        edited_content=sanitized_generated_content,
        status="draft",
        generated_by_model=generated_outline.model_name,
    )
    db.add(outline)
    db.commit()
    return RedirectResponse(url=redirect_to, status_code=303)


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


@app.get("/lessons/{lesson_id}/drafts", response_class=HTMLResponse)
async def show_lesson_drafts(
    lesson_id: int,
    request: Request,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """显示导学案前测与三阶导学案草稿。"""

    lesson = db.get(Lesson, lesson_id)
    if lesson is None:
        raise HTTPException(status_code=404, detail="课次不存在")

    outline = _get_latest_knowledge_outline(db, lesson.id)
    drafts = _get_lesson_drafts(db, lesson.id)
    chaoxing_filename = _safe_export_filename(request.query_params.get("chaoxing_file"), ".xlsx")
    fallback_message = (
        "DeepSeek 响应较慢、调用失败或当前未设置 API Key，已回退为本地结构化草稿。你可以稍后重试，或减少材料后再生成。"
        if request.query_params.get("draft_fallback") == "1"
        else None
    )
    return templates.TemplateResponse(
        request,
        "lesson_drafts.html",
        {
            "lesson": lesson,
            "outline": outline,
            "drafts": drafts,
            "draft_type_labels": DRAFT_TYPE_LABELS,
            "draft_status_labels": LESSON_DRAFT_STATUS_LABELS,
            "has_low_guide": any(draft.draft_type == "guide_low" for draft in drafts),
            "chaoxing_export_url": f"/exports/chaoxing/{chaoxing_filename}" if chaoxing_filename else None,
            "error_message": None if outline else "请先生成并保存知识主干，再生成课前学情测试与学生导学案草稿。",
            "fallback_message": fallback_message,
        },
    )


@app.post("/lessons/{lesson_id}/drafts/generate")
async def generate_lesson_drafts_route(
    lesson_id: int,
    request: Request,
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """兼容旧入口：只生成或更新课前学情测试，不连带生成导学案。"""

    lesson = db.get(Lesson, lesson_id)
    if lesson is None:
        raise HTTPException(status_code=404, detail="课次不存在")

    outline = _get_latest_knowledge_outline(db, lesson.id)
    if outline is None:
        return RedirectResponse(url=f"/lessons/{lesson.id}/drafts", status_code=303)

    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    draft, used_fallback = await run_in_threadpool(
        generate_single_lesson_draft_with_ai,
        lesson,
        outline,
        "diagnostic_probe",
        get_session_api_key(session_id),
        get_session_selected_model(session_id) or get_default_deepseek_model(),
    )
    _upsert_lesson_drafts(db, lesson, outline, [draft])
    db.commit()
    suffix = "?draft_fallback=1" if used_fallback else ""
    return RedirectResponse(url=f"/lessons/{lesson.id}/drafts{suffix}", status_code=303)


@app.post("/lessons/{lesson_id}/drafts/generate/teaching_prep_reference")
async def generate_teaching_prep_reference_route(
    lesson_id: int,
    request: Request,
    return_to: str = Form(""),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """生成或更新备课参考建议草稿。"""

    lesson = db.scalar(
        select(Lesson)
        .options(selectinload(Lesson.materials), selectinload(Lesson.course))
        .where(Lesson.id == lesson_id)
    )
    if lesson is None:
        raise HTTPException(status_code=404, detail="课次不存在")

    materials = db.scalars(
        select(LessonMaterial)
        .where(LessonMaterial.lesson_id == lesson.id)
        .order_by(LessonMaterial.id)
    ).all()
    outline = _get_latest_knowledge_outline(db, lesson.id)
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    draft, _used_fallback = await run_in_threadpool(
        generate_teaching_prep_reference,
        lesson,
        materials,
        outline,
        get_session_api_key(session_id),
        get_session_selected_model(session_id) or get_default_deepseek_model(),
    )
    _upsert_lesson_drafts(db, lesson, outline, [draft])
    db.commit()
    redirect_to = sanitize_next_path(return_to) or f"/lessons/{lesson.id}/drafts"
    return RedirectResponse(url=redirect_to, status_code=303)


@app.post("/lessons/{lesson_id}/drafts/generate/{draft_type}")
async def generate_tiered_lesson_draft_route(
    lesson_id: int,
    draft_type: str,
    request: Request,
    return_to: str = Form(""),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """按需生成或更新单个导学草稿。"""

    if draft_type not in LESSON_DRAFT_TYPES:
        raise HTTPException(status_code=404, detail="导学草稿类型不存在")

    lesson = db.get(Lesson, lesson_id)
    if lesson is None:
        raise HTTPException(status_code=404, detail="课次不存在")

    outline = _get_latest_knowledge_outline(db, lesson.id)
    if outline is None:
        return RedirectResponse(
            url=sanitize_next_path(return_to) or f"/lessons/{lesson.id}/drafts",
            status_code=303,
        )

    low_guide = _get_lesson_draft_by_type(db, lesson.id, "guide_low")
    mid_guide = _get_lesson_draft_by_type(db, lesson.id, "guide_mid")
    dependency_message = _learning_guide_dependency_message(draft_type, low_guide is not None, mid_guide is not None)
    if dependency_message:
        redirect_to = sanitize_next_path(return_to) or f"/lessons/{lesson.id}/drafts"
        return RedirectResponse(
            url=_append_query_param(redirect_to, "dependency_message", dependency_message),
            status_code=303,
        )

    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    related_drafts = {
        related_type: draft.content
        for related_type, draft in {"guide_low": low_guide, "guide_mid": mid_guide}.items()
        if draft is not None
    }
    api_key = get_session_api_key(session_id)
    selected_model = get_session_selected_model(session_id) or get_default_deepseek_model()
    if api_key:
        draft, used_fallback = await run_in_threadpool(
            generate_single_lesson_draft_with_ai,
            lesson,
            outline,
            draft_type,
            api_key,
            selected_model,
            related_drafts,
        )
    else:
        draft, used_fallback = generate_single_lesson_draft_with_ai(
            lesson,
            outline,
            draft_type,
            None,
            selected_model,
            related_drafts,
        )
    _upsert_lesson_drafts(db, lesson, outline, [draft])
    db.commit()
    redirect_to = sanitize_next_path(return_to) or f"/lessons/{lesson.id}/drafts"
    if used_fallback:
        redirect_to = _append_query_param(redirect_to, "draft_fallback", "1")
    return RedirectResponse(url=redirect_to, status_code=303)


@app.post("/lessons/{lesson_id}/drafts/{draft_id}/save")
async def save_lesson_draft(
    lesson_id: int,
    draft_id: int,
    title: str = Form(...),
    content: str = Form(...),
    return_to: str = Form(""),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """保存教师编辑后的导学草稿。"""

    draft = db.get(LessonDraft, draft_id)
    if draft is None or draft.lesson_id != lesson_id:
        raise HTTPException(status_code=404, detail="导学草稿不存在")

    draft.title = title.strip() or draft.title
    draft.content = content.strip()
    draft.status = "reviewed"
    db.commit()
    return RedirectResponse(url=sanitize_next_path(return_to) or f"/lessons/{lesson_id}/drafts", status_code=303)


@app.post("/lessons/{lesson_id}/drafts/{draft_id}/export-chaoxing")
async def export_diagnostic_probe_to_chaoxing(
    lesson_id: int,
    draft_id: int,
    return_to: str = Form(""),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """将导学案前测导出为学习通题库导入 xlsx。"""

    lesson = db.get(Lesson, lesson_id)
    draft = db.get(LessonDraft, draft_id)
    if lesson is None or draft is None or draft.lesson_id != lesson_id:
        raise HTTPException(status_code=404, detail="导学草稿不存在")
    if draft.draft_type != "diagnostic_probe":
        raise HTTPException(status_code=400, detail="只有导学案前测可以导出学习通题库模板")

    CHAOXING_EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    lesson_part = _safe_export_part(lesson.lesson_code, str(lesson.id))
    filename = f"lesson_{lesson.id}_{lesson_part}_diagnostic_probe.xlsx"
    output_path = CHAOXING_EXPORT_DIR / filename
    write_chaoxing_template_xlsx(lesson, draft, output_path)
    redirect_to = sanitize_next_path(return_to) or f"/lessons/{lesson.id}/drafts"
    return RedirectResponse(url=_append_query_param(redirect_to, "chaoxing_file", filename), status_code=303)


@app.get("/exports/chaoxing/{filename}")
async def download_chaoxing_export(filename: str) -> Response:
    """下载已生成的学习通题库导入文件。"""

    safe_filename = _safe_export_filename(filename, ".xlsx")
    if safe_filename is None:
        raise HTTPException(status_code=404, detail="导出文件不存在")
    file_path = CHAOXING_EXPORT_DIR / safe_filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="导出文件不存在")
    return Response(
        content=file_path.read_bytes(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{safe_filename}"'},
    )


@app.get("/lessons/{lesson_id}/drafts/{draft_id}/download-md")
async def download_lesson_draft_markdown(
    lesson_id: int,
    draft_id: int,
    db: Session = Depends(get_db),
) -> Response:
    """将当前导学案或备课参考建议草稿下载为 Markdown。"""

    lesson = db.get(Lesson, lesson_id)
    draft = db.get(LessonDraft, draft_id)
    if lesson is None or draft is None or draft.lesson_id != lesson_id:
        raise HTTPException(status_code=404, detail="导学草稿不存在")
    downloadable_types = {"guide_low", "guide_mid", "guide_high", TEACHING_PREP_REFERENCE_DRAFT_TYPE}
    if draft.draft_type not in downloadable_types:
        raise HTTPException(status_code=400, detail="只有导学案或备课参考建议草稿可以下载 Markdown")

    GUIDE_EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    filename_part = LESSON_DRAFT_DOWNLOAD_NAME_PARTS.get(draft.draft_type, "learning_draft")
    filename = f"lesson_{lesson.id}_{filename_part}.md"
    output_path = GUIDE_EXPORT_DIR / filename
    output_path.write_text(draft.content, encoding="utf-8")
    return Response(
        content=draft.content,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/knowledge-outlines/{outline_id}/save")
async def save_knowledge_outline(
    outline_id: int,
    edited_content: str = Form(...),
    return_to: str = Form(""),
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
    return RedirectResponse(
        url=sanitize_next_path(return_to) or f"/lessons/{outline.lesson_id}/knowledge-outline",
        status_code=303,
    )
