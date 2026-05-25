"""AI Provider 抽象层。"""

from __future__ import annotations

import os
from dataclasses import dataclass

from app.models.lesson import Lesson, LessonMaterial
from app.services.ai.deepseek_client import DeepSeekProviderError, generate_deepseek_knowledge_outline, get_deepseek_config
from app.services.ai.mock_outline_service import MOCK_OUTLINE_MODEL_NAME, generate_mock_knowledge_outline

DEFAULT_AI_PROVIDER = "deepseek"


@dataclass(frozen=True)
class GeneratedOutline:
    """AI 生成结果。"""

    content: str
    model_name: str


def get_ai_provider_name() -> str:
    """读取当前 AI Provider 名称。"""

    return os.getenv("AI_PROVIDER", DEFAULT_AI_PROVIDER).strip().lower() or DEFAULT_AI_PROVIDER


def generate_knowledge_outline_with_provider(
    lesson: Lesson,
    materials: list[LessonMaterial],
    api_key: str | None,
    provider_name: str | None = None,
) -> GeneratedOutline:
    """根据配置调用 Mock 或 DeepSeek 生成知识主干。

    Args:
        lesson: 当前课次。
        materials: 当前课次材料。
        api_key: DeepSeek 模式下必需的当前会话 API Key。
        provider_name: 可选 provider 名称，测试可显式传入。

    Returns:
        GeneratedOutline。

    Raises:
        DeepSeekProviderError: DeepSeek 调用失败、缺少 API Key 或 Provider 配置无效。
    """

    active_provider = (provider_name or get_ai_provider_name()).strip().lower()
    if active_provider == "mock":
        return GeneratedOutline(generate_mock_knowledge_outline(lesson, materials), MOCK_OUTLINE_MODEL_NAME)

    if active_provider == "deepseek":
        if not api_key:
            raise DeepSeekProviderError("请先设置当前会话 DeepSeek API Key，再生成知识主干。")
        content, model_name = generate_deepseek_knowledge_outline(lesson, materials, api_key, get_deepseek_config())
        return GeneratedOutline(content, model_name)

    raise DeepSeekProviderError("AI Provider 配置无效，请使用 deepseek 或 mock。")
