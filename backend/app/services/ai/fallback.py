"""AI fallback reason and teacher-facing messages."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Generic, TypeVar

FALLBACK_REASON_MISSING_API_KEY = "missing_api_key"
FALLBACK_REASON_PROVIDER_ERROR = "provider_error"
FALLBACK_REASON_QUERY_PARAM = "ai_fallback_reason"

MISSING_API_KEY_FALLBACK_MESSAGE = "当前未设置 DeepSeek API Key，已生成本地结构化草稿。"
PROVIDER_ERROR_FALLBACK_MESSAGE = "AI 服务暂时不可用，系统已提供本地草稿，可稍后重试。"

FALLBACK_MESSAGES = {
    FALLBACK_REASON_MISSING_API_KEY: MISSING_API_KEY_FALLBACK_MESSAGE,
    FALLBACK_REASON_PROVIDER_ERROR: PROVIDER_ERROR_FALLBACK_MESSAGE,
}

T = TypeVar("T")


@dataclass(frozen=True)
class FallbackGenerationResult(Generic[T]):
    """Generation result that stays compatible with old two-item unpacking."""

    value: T
    used_fallback: bool
    fallback_reason: str | None = None

    def __iter__(self) -> Iterator[object]:
        yield self.value
        yield self.used_fallback


def fallback_message_for_reason(reason: str | None) -> str | None:
    """Return the teacher-facing fallback message for a short safe reason."""

    return FALLBACK_MESSAGES.get(reason or "")
