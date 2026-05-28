"""正式课次模型。"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.course_plan import PlannedLesson


class Lesson(Base):
    """教师确认后的正式课次。"""

    __tablename__ = "lessons"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), nullable=False, index=True)
    planned_lesson_id: Mapped[int | None] = mapped_column(ForeignKey("planned_lessons.id"), nullable=True, unique=True)
    week: Mapped[str] = mapped_column(String(50), nullable=False)
    lesson_no: Mapped[str] = mapped_column(String(50), nullable=False)
    hours: Mapped[str] = mapped_column(String(50), nullable=False)
    lesson_code: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    homework_hint: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    course = relationship("Course", back_populates="lessons")
    planned_lesson = relationship("PlannedLesson", back_populates="lesson")
    materials = relationship("LessonMaterial", back_populates="lesson", cascade="all, delete-orphan")
    knowledge_outlines = relationship("KnowledgeOutline", back_populates="lesson", cascade="all, delete-orphan")
    drafts = relationship("LessonDraft", back_populates="lesson", cascade="all, delete-orphan")


class LessonMaterial(Base):
    """课次教学材料。"""

    __tablename__ = "lesson_materials"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id"), nullable=False, index=True)
    material_type: Mapped[str] = mapped_column(String(50), nullable=False, default="text")
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))

    lesson = relationship("Lesson", back_populates="materials")


def create_lesson_from_planned_lesson(planned_lesson: PlannedLesson) -> Lesson | None:
    """将已确认的 planned lesson 转换为正式 Lesson。

    Args:
        planned_lesson: 授课计划解析得到的预览课次。

    Returns:
        confirmed 状态返回 Lesson；skipped 或其他状态返回 None。

    Raises:
        不主动抛出业务异常。
    """

    # 业务规则：教师确认的计划课次才进入正式课次；跳过的课次不能生成 Lesson。
    if planned_lesson.status != "confirmed":
        return None

    return Lesson(
        course_id=planned_lesson.course_id,
        planned_lesson_id=planned_lesson.id,
        week=planned_lesson.week,
        lesson_no=planned_lesson.lesson_no,
        hours=planned_lesson.hours,
        lesson_code=planned_lesson.lesson_code,
        title=planned_lesson.lesson_title,
        content_summary=planned_lesson.content_raw,
        homework_hint=planned_lesson.homework,
        status="draft",
    )
