"""课次导学草稿模型。"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


LESSON_DRAFT_TYPES = {
    "diagnostic_probe",
    "guide_low",
    "guide_mid",
    "guide_high",
    "teaching_prep_reference",
}
LESSON_DRAFT_STATUSES = {"draft", "reviewed"}


class LessonDraft(Base):
    """基于知识主干生成的教师草稿。

    V0.2 先保存导学案前测、学生导学案任务包和备课参考建议草稿，不做学生端发布。
    """

    __tablename__ = "lesson_drafts"
    __table_args__ = (
        UniqueConstraint("lesson_id", "draft_type", name="uq_lesson_drafts_lesson_type"),
        CheckConstraint(
            "draft_type in ('diagnostic_probe', 'guide_low', 'guide_mid', 'guide_high', 'teaching_prep_reference')",
            name="ck_lesson_drafts_draft_type",
        ),
        CheckConstraint("status in ('draft', 'reviewed')", name="ck_lesson_drafts_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id"), nullable=False, index=True)
    source_outline_id: Mapped[int | None] = mapped_column(ForeignKey("knowledge_outlines.id"), nullable=True)
    draft_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft")
    generated_by: Mapped[str] = mapped_column(String(100), nullable=False, default="rule_based")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    lesson = relationship("Lesson", back_populates="drafts")
    source_outline = relationship("KnowledgeOutline", back_populates="lesson_drafts")
