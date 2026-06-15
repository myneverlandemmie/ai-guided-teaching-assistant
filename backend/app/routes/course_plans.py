"""授课计划上传与确认相关路由。"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from urllib.parse import quote
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.models.course import Course
from app.models.course_plan import CoursePlanUpload, PlannedLesson
from app.services.course_plan.import_service import create_lessons_from_confirmed_planned_lessons, import_course_plan

SanitizeNextPath = Callable[[str | None], str | None]
ResolveReturnToPath = Callable[[str | None, str], tuple[str, bool]]
GetUploadDir = Callable[[], Path]

MAX_COURSE_PLAN_UPLOAD_BYTES = 50 * 1024 * 1024
COURSE_PLAN_UPLOAD_TOO_LARGE_MESSAGE = "文件过大，请拆分资料后上传。"
COURSE_PLAN_UPLOAD_CHUNK_BYTES = 1024 * 1024


class CoursePlanUploadTooLargeError(ValueError):
    """授课计划上传文件超过大小限制。"""


async def _save_course_plan_upload_with_size_limit(uploaded_file: UploadFile, destination: Path) -> None:
    """分块保存授课计划上传文件，超限时删除已写入内容。"""

    total_size = 0
    try:
        await uploaded_file.seek(0)
        with destination.open("wb") as output_file:
            while True:
                chunk = await uploaded_file.read(COURSE_PLAN_UPLOAD_CHUNK_BYTES)
                if not chunk:
                    break
                total_size += len(chunk)
                if total_size > MAX_COURSE_PLAN_UPLOAD_BYTES:
                    raise CoursePlanUploadTooLargeError
                output_file.write(chunk)
    except CoursePlanUploadTooLargeError:
        destination.unlink(missing_ok=True)
        raise
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    finally:
        await uploaded_file.seek(0)


def create_course_plans_router(
    templates: Jinja2Templates,
    sanitize_next_path: SanitizeNextPath,
    resolve_return_to_path: ResolveReturnToPath,
    get_course_plan_upload_dir: GetUploadDir,
) -> APIRouter:
    """创建授课计划上传路由，复用 main.py 中已有公共依赖。"""

    router = APIRouter()

    @router.get("/courses/{course_id}/course-plan/upload", response_class=HTMLResponse)
    async def show_course_plan_upload_form(
        course_id: int,
        request: Request,
        db: Session = Depends(get_db),
    ) -> Response:
        """显示授课计划上传表单。"""

        course = db.get(Course, course_id)
        if course is None:
            raise HTTPException(status_code=404, detail="课程不存在")

        return_to, return_to_invalid = resolve_return_to_path(request.query_params.get("return_to"), "/courses")
        if return_to_invalid:
            return RedirectResponse(url=return_to, status_code=303)
        return templates.TemplateResponse(
            request,
            "course_plan_upload.html",
            {"course": course, "error_message": None, "return_to": return_to},
        )

    @router.post("/courses/{course_id}/course-plan/upload", response_class=HTMLResponse)
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

        safe_return_to, return_to_invalid = resolve_return_to_path(return_to, "/courses")
        if not file.filename or not file.filename.lower().endswith(".xlsx"):
            if return_to_invalid:
                return RedirectResponse(url=safe_return_to, status_code=303)
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

        course_plan_upload_dir = get_course_plan_upload_dir()
        course_plan_upload_dir.mkdir(parents=True, exist_ok=True)
        safe_filename = Path(file.filename).name
        saved_path = course_plan_upload_dir / f"{uuid4().hex}-{safe_filename}"

        # 上传文件只保存到运行时目录，目录已由 .gitignore 排除。
        try:
            await _save_course_plan_upload_with_size_limit(file, saved_path)
        except CoursePlanUploadTooLargeError:
            if return_to_invalid:
                return RedirectResponse(url=safe_return_to, status_code=303)
            return templates.TemplateResponse(
                request,
                "course_plan_upload.html",
                {
                    "course": course,
                    "error_message": COURSE_PLAN_UPLOAD_TOO_LARGE_MESSAGE,
                    "return_to": safe_return_to,
                },
                status_code=400,
            )

        result = import_course_plan(db, course, saved_path, safe_filename)
        upload = result["upload"]
        if return_to_invalid:
            return RedirectResponse(url=safe_return_to, status_code=303)
        preview_url = f"/course-plan-uploads/{upload.id}"
        if safe_return_to != "/courses":
            preview_url = f"{preview_url}?return_to={quote(safe_return_to, safe='')}"
        return RedirectResponse(url=preview_url, status_code=303)

    @router.get("/course-plan-uploads/{upload_id}", response_class=HTMLResponse)
    async def show_course_plan_preview(
        upload_id: int,
        request: Request,
        db: Session = Depends(get_db),
    ) -> Response:
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
        return_to, return_to_invalid = resolve_return_to_path(request.query_params.get("return_to"), "/courses")
        if return_to_invalid:
            return RedirectResponse(url=return_to, status_code=303)

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

    @router.post("/course-plan-uploads/{upload_id}/confirm")
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

    return router
