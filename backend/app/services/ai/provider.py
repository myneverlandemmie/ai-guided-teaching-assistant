"""AI Provider 抽象层。"""

from __future__ import annotations

import os
from dataclasses import dataclass

from app.models.lesson import Lesson, LessonMaterial
from app.services.ai.deepseek_client import DeepSeekProviderError, generate_deepseek_knowledge_outline, get_deepseek_config
from app.services.ai.fallback import FALLBACK_REASON_MISSING_API_KEY, FALLBACK_REASON_PROVIDER_ERROR
from app.services.ai.mock_outline_service import MOCK_OUTLINE_MODEL_NAME, generate_mock_knowledge_outline

DEFAULT_AI_PROVIDER = "deepseek"
LOCAL_STRUCTURED_DRAFT = "local-structured-draft"


@dataclass(frozen=True)
class GeneratedOutline:
    """AI 生成结果。"""

    content: str
    model_name: str
    fallback_reason: str | None = None


def get_ai_provider_name() -> str:
    """读取当前 AI Provider 名称。"""

    return os.getenv("AI_PROVIDER", DEFAULT_AI_PROVIDER).strip().lower() or DEFAULT_AI_PROVIDER


def generate_local_knowledge_outline(
    lesson: Lesson,
    materials: list[LessonMaterial],
    fallback_reason: str,
) -> GeneratedOutline:
    """生成知识主干本地结构化草稿，并标记 fallback reason。"""

    return GeneratedOutline(
        generate_mock_knowledge_outline(lesson, materials),
        LOCAL_STRUCTURED_DRAFT,
        fallback_reason,
    )


def generate_knowledge_outline_with_provider(
    lesson: Lesson,
    materials: list[LessonMaterial],
    api_key: str | None,
    selected_model: str | None = None,
    provider_name: str | None = None,
) -> GeneratedOutline:
    """根据配置调用本地结构化草稿或 DeepSeek 生成知识主干。

    Args:
        lesson: 当前课次。
        materials: 当前课次材料。
        api_key: DeepSeek 模式下使用的当前会话 API Key；为空时使用本地结构化草稿。
        selected_model: 教师当前会话选择的 DeepSeek 模型。
        provider_name: 可选 provider 名称，测试可显式传入。

    Returns:
        GeneratedOutline。

    Raises:
        DeepSeekProviderError: DeepSeek 调用失败或 Provider 配置无效。
    """

    active_provider = (provider_name or get_ai_provider_name()).strip().lower()
    if active_provider == "mock":
        return GeneratedOutline(generate_mock_knowledge_outline(lesson, materials), MOCK_OUTLINE_MODEL_NAME)

    if active_provider == "deepseek":
        if not api_key:
            return generate_local_knowledge_outline(lesson, materials, FALLBACK_REASON_MISSING_API_KEY)
        try:
            content, model_name = generate_deepseek_knowledge_outline(
                lesson,
                materials,
                api_key,
                selected_model,
                get_deepseek_config(selected_model),
            )
        except DeepSeekProviderError:
            return generate_local_knowledge_outline(lesson, materials, FALLBACK_REASON_PROVIDER_ERROR)
        return GeneratedOutline(content, model_name)

    raise DeepSeekProviderError("AI Provider 配置无效，请使用 deepseek 或 mock。")
