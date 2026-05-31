from pathlib import Path

from app.models.knowledge_outline import KnowledgeOutline
from app.models.lesson import Lesson
from app.services.ai.lesson_draft_prompt import LESSON_DRAFT_SYSTEM_MESSAGE, build_lesson_draft_prompt
from app.services.ai.lesson_draft_service import DRAFT_TYPE_LABELS, generate_basic_lesson_drafts, generate_tiered_guide_draft


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


def test_public_draft_labels_are_task_pack_or_basic_document() -> None:
    assert DRAFT_TYPE_LABELS["guide_low"] == "全班通用导学案 / 基础版导学案"
    assert DRAFT_TYPE_LABELS["guide_mid"] == "巩固提升任务包"
    assert DRAFT_TYPE_LABELS["guide_high"] == "拓展探究任务包"
    for forbidden in ["低阶", "中阶", "高阶"]:
        assert all(forbidden not in label for label in DRAFT_TYPE_LABELS.values())


def test_local_structured_guides_use_learning_context_and_task_packs() -> None:
    lesson = _lesson()
    outline = _outline()
    low = next(draft for draft in generate_basic_lesson_drafts(lesson, outline) if draft.draft_type == "guide_low")
    mid = generate_tiered_guide_draft(lesson, outline, "guide_mid")
    high = generate_tiered_guide_draft(lesson, outline, "guide_high")

    assert "基础版导学案" in low.content
    assert "学习情境" in low.content
    assert "任务导入" not in low.content
    assert "提升任务包" in mid.content
    assert "拓展挑战包" in high.content
    assert "不是完整导学案" in mid.content
    assert "不是完整导学案" in high.content
    assert "学习导航" not in mid.content
    assert "学习导航" not in high.content
    for content in [low.content, mid.content, high.content]:
        assert "低阶" not in content
        assert "中阶" not in content
        assert "高阶" not in content


def test_lesson_draft_prompts_prevent_dialogue_opening_and_split_task_packs() -> None:
    lesson = _lesson()
    outline = _outline()
    system_and_low = f"{LESSON_DRAFT_SYSTEM_MESSAGE}\n{build_lesson_draft_prompt(lesson, outline, 'guide_low')}"
    mid_prompt = build_lesson_draft_prompt(lesson, outline, "guide_mid")
    high_prompt = build_lesson_draft_prompt(lesson, outline, "guide_high")

    for forbidden_opening in ["当然可以", "以下是", "好的", "我将为你"]:
        assert forbidden_opening in system_and_low
    assert "直接输出正文" in system_and_low
    assert "学习情境" in system_and_low
    assert "任务导入" not in system_and_low
    assert "提升任务包" in mid_prompt
    assert "只生成 3—5 个提升任务" in mid_prompt
    assert "不要重复完整导学案结构" in mid_prompt
    assert "拓展挑战包" in high_prompt
    assert "只生成 2—3 个挑战任务" in high_prompt
    assert "不要重复完整导学案结构" in high_prompt


def test_lesson_drafts_template_contains_generation_guard() -> None:
    template = Path("app/templates/lesson_drafts.html").read_text(encoding="utf-8")

    assert "AI 正在生成，请稍候" in template
    assert "请勿重复点击" in template
    assert "data-draft-generation-form" in template
    assert "data-ai-generation-form" in template
    assert "data-draft-generation-button" in template
    assert "handleLessonDraftGenerationSubmit" in template
    script = Path("app/static/js/app.js").read_text(encoding="utf-8")
    assert "button.disabled = true" in script
    assert "event.submitter" in script
    assert "button.textContent = 'AI 正在生成，请稍候...'" not in script
    assert "clickedButton.textContent = form.getAttribute('data-loading-label')" in script
