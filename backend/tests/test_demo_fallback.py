from types import SimpleNamespace

from app.services.ai.fallback import FALLBACK_REASON_MISSING_API_KEY
from app.services.ai.provider import generate_knowledge_outline_with_provider


def test_deepseek_provider_without_api_key_returns_local_structured_draft() -> None:
    lesson = SimpleNamespace(lesson_code="0406", title="分组查询", content_summary="GROUP BY 分组。")
    material = SimpleNamespace(content="教学目标：理解分组查询。重点：结果核验。")

    result = generate_knowledge_outline_with_provider(
        lesson,
        [material],
        api_key=None,
        selected_model="deepseek-v4-flash",
        provider_name="deepseek",
    )

    assert result.model_name == "local-structured-draft"
    assert result.fallback_reason == FALLBACK_REASON_MISSING_API_KEY
    assert "本地结构化草稿" in result.content
    assert "需教师审阅、修改与确认" in result.content
    assert "mock" not in result.content.lower()
