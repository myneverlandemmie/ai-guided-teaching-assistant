"""知识主干模型。"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class KnowledgeOutline(Base):
    """课次知识主干。

    V0.2 先保存 Mock AI 初稿和教师编辑稿，所有内容都需要教师复核后使用。
    """

    __tablename__ = "knowledge_outlines"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id"), nullable=False, index=True)
    ai_raw_output: Mapped[str] = mapped_column(Text, nullable=False, default="")
    edited_content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft")
    generated_by_model: Mapped[str] = mapped_column(String(100), nullable=False, default="mock-ai-v0.2")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    lesson = relationship("Lesson", back_populates="knowledge_outlines")
    lesson_drafts = relationship("LessonDraft", back_populates="source_outline")
