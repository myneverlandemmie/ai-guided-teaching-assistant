from app.models.knowledge_outline import KnowledgeOutline
from app.models.lesson import Lesson
from app.services.ai.deepseek_client import DeepSeekProviderError
from app.services.ai.fallback import FALLBACK_REASON_MISSING_API_KEY, FALLBACK_REASON_PROVIDER_ERROR
from app.services.ai.lesson_draft_ai_service import (
    generate_basic_lesson_drafts_with_ai,
    generate_tiered_guide_draft_with_ai,
)
from app.services.ai.lesson_draft_prompt import LESSON_DRAFT_SYSTEM_MESSAGE, build_lesson_draft_prompt


def _lesson() -> Lesson:
    return Lesson(
        id=1,
        course_id=1,
        week="1",
        lesson_no="1",
        hours="2",
        lesson_code="0406",
        title="分组查询",
        content_summary="GROUP BY 分组查询。",
        status="draft",
    )


def _outline() -> KnowledgeOutline:
    return KnowledgeOutline(
        id=1,
        lesson_id=1,
        ai_raw_output="知识主干：分组查询、结果核验、过程记录和职业规范。",
        edited_content="知识主干：分组查询、结果核验、过程记录和职业规范。",
        status="reviewed",
        generated_by_model="test-model",
    )


def _ai_probe_content() -> str:
    return """# 分组查询｜课前学情测试草稿

### 题目 1
- 题型：单选题
- 题干：分组查询前应先确认什么？
- 选项：A. 分组字段；B. 字体颜色；C. 座位；D. 无关内容
- 参考答案：A
- 简短解析：分组字段决定统计口径。
- 诊断点：基础概念
- 难度：基础

## 导学案复杂度建议
- 基础版建议：补足概念。
- 提升版建议：增加解释。
- 拓展版建议：增加迁移。
"""


def _ai_guide_content(label: str = "基础版导学案") -> str:
    return f"""# 0406-分组查询｜{label}草稿

## 学习导航
- 本课学习目标：理解分组查询。

## 学习情境
- 本课要解决统计口径问题。

## 知识要点
- GROUP BY 用于分组统计。

## 边学边填
- 分组字段是：______。

## 例题引路
- 教师可调整示例。

## 仿做练习
- 完成一个同类练习，不做自动评分。

## 过程记录
- 记录操作步骤、运行结果、错误信息和排查过程。

## 重点速记
- 先确认分组字段。

## 带回小练
- 完成一个课后小练。

## 学习记录
- 我的问题：______。

## 学习自评
- [ ] 我能说出本课关键概念。

## AI 草稿声明
以上内容为草稿，需教师审核。
"""


def test_lesson_drafts_without_api_key_use_local_structured_drafts() -> None:
    result = generate_basic_lesson_drafts_with_ai(_lesson(), _outline(), None, "deepseek-v4-flash")
    drafts, used_fallback = result

    assert used_fallback is True
    assert result.fallback_reason == FALLBACK_REASON_MISSING_API_KEY
    assert {draft.draft_type for draft in drafts} == {"diagnostic_probe", "guide_low"}
    assert {draft.generated_by for draft in drafts} == {"local-structured-draft"}


def test_lesson_drafts_use_deepseek_content_when_api_succeeds(monkeypatch) -> None:
    calls: list[str] = []

    def fake_call(lesson, outline, draft_type, api_key, selected_model):
        calls.append(draft_type)
        if draft_type == "diagnostic_probe":
            return _ai_probe_content(), "deepseek-v4-flash"
        return _ai_guide_content(), "deepseek-v4-flash"

    monkeypatch.setattr("app.services.ai.lesson_draft_ai_service._call_deepseek_lesson_draft", fake_call)

    result = generate_basic_lesson_drafts_with_ai(
        _lesson(),
        _outline(),
        "sk-test-not-real",
        "deepseek-v4-flash",
    )
    drafts, used_fallback = result

    assert used_fallback is False
    assert result.fallback_reason is None
    assert calls == ["diagnostic_probe", "guide_low"]
    assert {draft.generated_by for draft in drafts} == {"deepseek-v4-flash"}
    assert any("分组查询前应先确认什么" in draft.content for draft in drafts)


def test_lesson_drafts_fallback_when_api_raises(monkeypatch) -> None:
    def fake_call(*args, **kwargs):
        raise DeepSeekProviderError("测试异常")

    monkeypatch.setattr("app.services.ai.lesson_draft_ai_service._call_deepseek_lesson_draft", fake_call)

    result = generate_basic_lesson_drafts_with_ai(
        _lesson(),
        _outline(),
        "sk-test-not-real",
        "deepseek-v4-flash",
    )
    drafts, used_fallback = result

    assert used_fallback is True
    assert result.fallback_reason == FALLBACK_REASON_PROVIDER_ERROR
    assert {draft.generated_by for draft in drafts} == {"local-structured-draft"}


def test_tiered_guide_uses_ai_model_or_fallback(monkeypatch) -> None:
    def fake_call(lesson, outline, draft_type, api_key, selected_model):
        return """# 0406-分组查询｜提升任务包草稿

## 使用建议
- 基础版导学案之后按需使用。

## 适用对象
- 已完成基础任务的学生。

## 任务 1：变式练习
- 学生要做什么：调整统计条件。

## 教师调整提示
- 需教师审核。
""", "deepseek-v4-pro"

    monkeypatch.setattr("app.services.ai.lesson_draft_ai_service._call_deepseek_lesson_draft", fake_call)

    result = generate_tiered_guide_draft_with_ai(
        _lesson(),
        _outline(),
        "guide_mid",
        "sk-test-not-real",
        "deepseek-v4-pro",
    )
    draft, used_fallback = result

    assert used_fallback is False
    assert result.fallback_reason is None
    assert draft.generated_by == "deepseek-v4-pro"
    assert "提升任务包" in draft.content


def test_lesson_draft_prompt_keeps_boundaries_and_versions() -> None:
    prompt = build_lesson_draft_prompt(_lesson(), _outline(), "guide_high")
    full_prompt = f"{LESSON_DRAFT_SYSTEM_MESSAGE}\n{prompt}"

    assert "不生成完整教案" in full_prompt
    assert "不替教师决定教学目标" in full_prompt
    assert "拓展挑战包" in prompt
    assert "不是完整导学案" in prompt
    assert "挑战 1" in prompt
    assert "不做自动评分" in prompt
    assert "低阶" not in prompt
    assert "中阶" not in prompt
    assert "高阶" not in prompt


def test_lesson_draft_prompt_direct_output_and_task_pack_boundaries() -> None:
    low_prompt = build_lesson_draft_prompt(_lesson(), _outline(), "guide_low")
    mid_prompt = build_lesson_draft_prompt(_lesson(), _outline(), "guide_mid")

    assert "学习情境" in low_prompt
    assert "任务导入" not in low_prompt
    assert "直接输出正文" in low_prompt
    assert "当然可以" in low_prompt
    assert "以下是" in low_prompt
    assert "提升任务包" in mid_prompt
    assert "只生成 3—5 个提升任务" in mid_prompt
    assert "不要重复完整导学案结构" in mid_prompt
