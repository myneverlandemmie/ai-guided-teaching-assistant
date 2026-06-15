"""课程管理相关路由。"""

from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.course import Course
from app.models.lesson import Lesson
from app.services.course_management_service import (
    create_course,
    delete_course,
    get_or_create_default_course,
    rename_course,
)

SanitizeNextPath = Callable[[str | None], str | None]
ResolveReturnToPath = Callable[[str | None, str], tuple[str, bool]]


def create_courses_router(
    templates: Jinja2Templates,
    sanitize_next_path: SanitizeNextPath,
    resolve_return_to_path: ResolveReturnToPath,
) -> APIRouter:
    """创建课程管理路由，复用 main.py 中已有公共依赖。"""

    router = APIRouter()

    def get_or_create_demo_course(session: Session) -> Course:
        """读取或创建默认测试课程。"""

        return get_or_create_default_course(session)

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

    def _courses_template_context(
        db: Session,
        courses: list[Course],
        template_name: str,
        error_message: str | None,
        return_to_invalid: bool = False,
    ) -> dict[str, object]:
        """构造课程页上下文。"""

        context: dict[str, object] = {
            "courses": courses,
            "error_message": error_message,
            "return_to_invalid": return_to_invalid,
        }
        if template_name == "courses_v2.html":
            context["lesson_counts"] = _course_lesson_counts(db, courses)
        return context

    @router.get("/")
    async def read_root() -> RedirectResponse:
        """跳转到课程列表。"""

        return RedirectResponse(url="/courses", status_code=303)

    @router.get("/courses", response_class=HTMLResponse)
    async def list_courses(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
        """显示课程列表；没有课程时创建 demo course。"""

        get_or_create_demo_course(db)
        courses = db.scalars(select(Course).order_by(Course.id)).all()
        return templates.TemplateResponse(
            request,
            "courses.html",
            {"courses": courses, "error_message": None},
        )

    @router.get("/ui-v2/courses", response_class=HTMLResponse)
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

    @router.post("/courses/create", response_class=HTMLResponse)
    async def create_course_route(
        request: Request,
        title: str = Form(""),
        return_to: str = Form("/courses"),
        db: Session = Depends(get_db),
    ) -> Response:
        """创建课程并返回课程中心。"""

        redirect_to, return_to_invalid = resolve_return_to_path(return_to, "/courses")
        try:
            create_course(db, title)
        except ValueError as exc:
            courses = db.scalars(select(Course).order_by(Course.id)).all()
            template_name = "courses_v2.html" if redirect_to.split("?", 1)[0] == "/ui-v2/courses" else "courses.html"
            return templates.TemplateResponse(
                request,
                template_name,
                _courses_template_context(db, courses, template_name, str(exc), return_to_invalid),
                status_code=400,
            )
        return RedirectResponse(url=redirect_to, status_code=303)

    @router.post("/courses/{course_id}/rename", response_class=HTMLResponse)
    async def rename_course_route(
        course_id: int,
        request: Request,
        title: str = Form(""),
        return_to: str = Form("/courses"),
        db: Session = Depends(get_db),
    ) -> Response:
        """修改课程名称。"""

        redirect_to, return_to_invalid = resolve_return_to_path(return_to, "/courses")
        course = db.get(Course, course_id)
        if course is None:
            raise HTTPException(status_code=404, detail="课程不存在")

        try:
            rename_course(db, course, title)
        except ValueError as exc:
            courses = db.scalars(select(Course).order_by(Course.id)).all()
            template_name = "courses_v2.html" if redirect_to.split("?", 1)[0] == "/ui-v2/courses" else "courses.html"
            return templates.TemplateResponse(
                request,
                template_name,
                _courses_template_context(db, courses, template_name, str(exc), return_to_invalid),
                status_code=400,
            )
        return RedirectResponse(url=redirect_to, status_code=303)

    @router.post("/courses/{course_id}/delete")
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
        redirect_to, _return_to_invalid = resolve_return_to_path(return_to, "/courses")
        return RedirectResponse(url=redirect_to, status_code=303)

    return router
