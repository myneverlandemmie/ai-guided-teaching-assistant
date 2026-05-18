"""智学导评 V0.2 后端入口。"""

from __future__ import annotations

import shutil
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.base import create_database_tables
from app.db.session import engine, get_db
from app.models.course import Course
from app.models.course_plan import CoursePlanUpload, PlannedLesson
from app.models.lesson import Lesson, LessonMaterial
from app.services.course_plan.import_service import create_lessons_from_confirmed_planned_lessons, import_course_plan

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
COURSE_PLAN_UPLOAD_DIR = PROJECT_ROOT / "data" / "uploads" / "course-plans"
LESSON_MATERIAL_UPLOAD_DIR = PROJECT_ROOT / "data" / "uploads" / "lesson-materials"


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """应用生命周期：启动时使用 create_all 初始化默认数据库。"""

    # V0.2 初期不用 Alembic，先用 create_all 支撑本地开发和演示。
    create_database_tables(engine)
    yield


app = FastAPI(title="AI Guided SQL Assessment", lifespan=lifespan)
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))


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
        .order_by(LessonMaterial.id)
    ).all()

    return templates.TemplateResponse(
        request,
        "lesson_detail.html",
        {"lesson": lesson, "materials": materials, "error_message": None},
    )


@app.post("/lessons/{lesson_id}/materials", response_class=HTMLResponse)
async def add_lesson_material(
    lesson_id: int,
    request: Request,
    title: str = Form(...),
    material_type: str = Form("text"),
    content: str = Form(""),
    file: UploadFile | None = File(None),
    db: Session = Depends(get_db),
) -> Response:
    """为课次添加教学材料，支持粘贴文本和可选 .txt / .md 文件。"""

    lesson = db.get(Lesson, lesson_id)
    if lesson is None:
        raise HTTPException(status_code=404, detail="课次不存在")

    saved_path: Path | None = None
    file_content = ""
    if file is not None and file.filename:
        suffix = Path(file.filename).suffix.lower()
        if suffix not in {".txt", ".md"}:
            materials = db.scalars(
                select(LessonMaterial)
                .where(LessonMaterial.lesson_id == lesson.id)
                .order_by(LessonMaterial.id)
            ).all()
            return templates.TemplateResponse(
                request,
                "lesson_detail.html",
                {
                    "lesson": lesson,
                    "materials": materials,
                    "error_message": "当前仅支持 .txt 或 .md 教学材料文件。",
                },
                status_code=400,
            )

        LESSON_MATERIAL_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        safe_filename = Path(file.filename).name
        saved_path = LESSON_MATERIAL_UPLOAD_DIR / f"{uuid4().hex}-{safe_filename}"
        # 文件材料保存到运行时目录；目录由 .gitignore 排除，不进入公开仓库。
        file_bytes = await file.read()
        saved_path.write_bytes(file_bytes)
        file_content = file_bytes.decode("utf-8", errors="replace")

    material_content = content.strip() or file_content
    if not material_content:
        materials = db.scalars(
            select(LessonMaterial)
            .where(LessonMaterial.lesson_id == lesson.id)
            .order_by(LessonMaterial.id)
        ).all()
        return templates.TemplateResponse(
            request,
            "lesson_detail.html",
            {
                "lesson": lesson,
                "materials": materials,
                "error_message": "请粘贴文本内容，或上传 .txt / .md 文件。",
            },
            status_code=400,
        )

    # V0.2 只保存朴素文本材料，不做 AI 解析或复杂富文本编辑。
    material = LessonMaterial(
        lesson_id=lesson.id,
        material_type=material_type,
        title=title.strip(),
        content=material_content,
        file_path=str(saved_path) if saved_path is not None else None,
    )
    db.add(material)
    db.commit()

    return RedirectResponse(url=f"/lessons/{lesson.id}", status_code=303)
