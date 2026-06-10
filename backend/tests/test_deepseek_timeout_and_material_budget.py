import pytest

from app.models.knowledge_outline import KnowledgeOutline
from app.models.lesson import Lesson
from app.services.ai.deepseek_client import DeepSeekProviderError, get_deepseek_config, get_deepseek_timeout_seconds
from app.services.ai.fallback import FALLBACK_REASON_PROVIDER_ERROR
from app.services.ai.lesson_draft_ai_service import generate_single_lesson_draft_with_ai
from app.services.ai.lesson_draft_prompt import build_lesson_draft_prompt, trim_text_to_budget


def _lesson(title: str = "三极管放大电路") -> Lesson:
    return Lesson(
        id=1,
        course_id=1,
        week="1",
        lesson_no="1",
        hours="2",
        lesson_code="0201",
        title=title,
        content_summary="认识三极管放大电路的静态工作点、输入信号和输出信号。",
        status="draft",
    )


def _outline(content: str) -> KnowledgeOutline:
    return KnowledgeOutline(
        id=1,
        lesson_id=1,
        ai_raw_output=content,
        edited_content=content,
        status="reviewed",
        generated_by_model="test-model",
    )


def test_deepseek_timeout_defaults_and_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in [
        "AI_REQUEST_TIMEOUT_SECONDS",
        "DEEPSEEK_TIMEOUT_SECONDS",
        "DEEPSEEK_FLASH_TIMEOUT_SECONDS",
        "DEEPSEEK_PRO_TIMEOUT_SECONDS",
    ]:
        monkeypatch.delenv(name, raising=False)

    assert get_deepseek_timeout_seconds("deepseek-v4-flash") == 180.0
    assert get_deepseek_timeout_seconds("deepseek-v4-pro") == 300.0
    assert get_deepseek_timeout_seconds("unknown-model") == 180.0
    assert get_deepseek_config("deepseek-v4-flash").timeout_seconds == 180.0
    assert get_deepseek_config("deepseek-v4-pro").timeout_seconds == 300.0

    monkeypatch.setenv("DEEPSEEK_FLASH_TIMEOUT_SECONDS", "210")
    monkeypatch.setenv("DEEPSEEK_PRO_TIMEOUT_SECONDS", "360")
    assert get_deepseek_config("deepseek-v4-flash").timeout_seconds == 210.0
    assert get_deepseek_config("deepseek-v4-pro").timeout_seconds == 360.0

    monkeypatch.setenv("DEEPSEEK_FLASH_TIMEOUT_SECONDS", "bad")
    assert get_deepseek_config("deepseek-v4-flash").timeout_seconds == 180.0


def test_timeout_fallback_only_returns_current_draft_type(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_timeout(*args, **kwargs):
        raise DeepSeekProviderError("DeepSeek 请求超时，请稍后重试或减少材料长度。")

    monkeypatch.setattr("app.services.ai.lesson_draft_ai_service._call_deepseek_lesson_draft", fake_timeout)

    result = generate_single_lesson_draft_with_ai(
        _lesson(),
        _outline("知识主干：静态工作点、放大倍数、实验步骤和安全注意事项。"),
        "guide_mid",
        "sk-test-not-real",
        "deepseek-v4-pro",
    )
    draft, used_fallback = result

    assert used_fallback is True
    assert result.fallback_reason == FALLBACK_REASON_PROVIDER_ERROR
    assert draft.draft_type == "guide_mid"
    assert draft.generated_by == "local-structured-draft"
    assert draft.content
    assert "提升任务包" in draft.content


def test_material_budget_trims_long_general_text(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_LESSON_DRAFT_PER_FILE_MAX_CHARS", "500")
    content = "教学目标：理解基础概念。\n\n" + "普通教学材料段落。" * 300

    prompt = build_lesson_draft_prompt(_lesson("通用课程"), _outline(content), "diagnostic_probe")

    assert "材料可能经过长度控制" in prompt
    assert "教师需结合原始资料确认" in prompt
    assert "普通教学材料段落。" in prompt
    assert len(prompt) < 7000


def test_non_sql_material_keeps_circuit_keywords_and_generic_boundaries(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_LESSON_DRAFT_PER_FILE_MAX_CHARS", "2000")
    circuit_material = """
教学目标：理解三极管放大电路的基本作用。
知识点：三极管、静态工作点、输入信号、输出信号、放大倍数。
实验步骤：连接电源，检查极性，输入小信号，观察输出波形。
安全注意事项：断电后再调整接线，避免短路。
"""

    prompt = build_lesson_draft_prompt(_lesson(), _outline(circuit_material), "guide_low")

    for keyword in ["三极管", "静态工作点", "输入信号", "输出信号", "放大倍数", "安全注意事项"]:
        assert keyword in prompt
    assert "本系统面向通用教学材料" in prompt
    assert "不限于 SQL" in prompt
    assert "CREATE TABLE" not in prompt
    assert "INSERT INTO" not in prompt
    assert "公式、图示" in prompt


def test_code_or_script_text_trimming_keeps_notice() -> None:
    code = "# 文件说明：Arduino 传感器读取示例\n\n```c\n" + "void loop() { readSensor(); }\n" * 200 + "```"

    trimmed = trim_text_to_budget(code, 500, material_kind="code")

    assert trimmed
    assert "文件说明" in trimmed
    assert "代码或脚本材料已按长度预算截取" in trimmed
    assert len(trimmed) <= 500


def test_lesson_draft_prompt_is_not_specialized_for_one_programming_or_sql_course() -> None:
    prompt = build_lesson_draft_prompt(
        _lesson("专业英语术语阅读"),
        _outline("教学目标：识别专业术语，理解设备说明中的安全提示。"),
        "guide_low",
    )

    assert "基于可见材料生成" in prompt
    assert "不得编造" in prompt
    assert "教师审核、修改、确认" in prompt or "教师审核、修改与确认" in prompt
    assert "SQL 专用" not in prompt
    assert "Python 专用" not in prompt
    assert "C 语言专用" not in prompt
    assert "编程专用" not in prompt
