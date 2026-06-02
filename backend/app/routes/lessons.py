"""正式课次列表与课次入口相关路由。"""

from __future__ import annotations

from collections.abc import Callable, Mapping

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.models.course import Course
from app.models.knowledge_outline import KnowledgeOutline
from app.models.lesson import Lesson, LessonMaterial

GetLatestKnowledgeOutline = Callable[[Session, int], KnowledgeOutline | None]


def create_lessons_router(
    templates: Jinja2Templates,
    get_latest_knowledge_outline: GetLatestKnowledgeOutline,
    material_type_labels: Mapping[str, str],
    lesson_status_labels: Mapping[str, str],
    knowledge_outline_status_labels: Mapping[str, str],
) -> APIRouter:
    """创建正式课次路由，复用 main.py 中已有公共依赖。"""

    router = APIRouter()

    @router.get("/courses/{course_id}/lessons", response_class=HTMLResponse)
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

    @router.get("/lessons/{lesson_id}", response_class=HTMLResponse)
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
        knowledge_outline = get_latest_knowledge_outline(db, lesson.id)

        return templates.TemplateResponse(
            request,
            "lesson_detail.html",
            {
                "lesson": lesson,
                "materials": materials,
                "error_message": None,
                "material_type_labels": material_type_labels,
                "lesson_status_labels": lesson_status_labels,
                "knowledge_outline": knowledge_outline,
                "knowledge_outline_status_labels": knowledge_outline_status_labels,
            },
        )

    return router
