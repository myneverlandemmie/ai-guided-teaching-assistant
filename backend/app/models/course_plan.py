"""授课计划上传与计划课次模型。"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class CoursePlanUpload(Base):
    """授课计划上传记录。"""

    __tablename__ = "course_plan_uploads"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), nullable=False, index=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    parsed_status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))

    course = relationship("Course", back_populates="course_plan_uploads")
    planned_lessons = relationship("PlannedLesson", back_populates="course_plan_upload", cascade="all, delete-orphan")


class PlannedLesson(Base):
    """从授课计划解析出的课次预览数据。"""

    __tablename__ = "planned_lessons"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    course_plan_upload_id: Mapped[int] = mapped_column(ForeignKey("course_plan_uploads.id"), nullable=False, index=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), nullable=False, index=True)
    week: Mapped[str] = mapped_column(String(50), nullable=False)
    lesson_no: Mapped[str] = mapped_column(String(50), nullable=False)
    hours: Mapped[str] = mapped_column(String(50), nullable=False)
    lesson_code: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    lesson_title: Mapped[str] = mapped_column(String(255), nullable=False)
    content_raw: Mapped[str] = mapped_column(Text, nullable=False)
    tools: Mapped[str] = mapped_column(Text, nullable=False, default="")
    homework: Mapped[str] = mapped_column(Text, nullable=False, default="")
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    course_plan_upload = relationship("CoursePlanUpload", back_populates="planned_lessons")
    course = relationship("Course", back_populates="planned_lessons")
    lesson = relationship("Lesson", back_populates="planned_lesson", uselist=False)
