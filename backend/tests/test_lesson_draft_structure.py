from app.models.knowledge_outline import KnowledgeOutline
from app.models.lesson import Lesson
from app.services.ai.lesson_draft_service import generate_basic_lesson_drafts


def test_student_learning_guide_contains_process_record_and_self_assessment() -> None:
    lesson = Lesson(
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
    outline = KnowledgeOutline(
        id=1,
        lesson_id=1,
        ai_raw_output="知识主干：分组查询、结果核验、易错点和职业规范。",
        edited_content="知识主干：分组查询、结果核验、易错点和职业规范。",
        status="reviewed",
        generated_by_model="test-model",
    )

    drafts = generate_basic_lesson_drafts(lesson, outline)
    low_guide = next(draft for draft in drafts if draft.draft_type == "guide_low")

    for heading in ["学习导航", "任务导入", "知识要点", "边学边填", "过程记录", "学习自评"]:
        assert heading in low_guide.content
    assert "观察现象" in low_guide.content
    assert "错误信息" in low_guide.content
    assert "我能遵守安全 / 规范要求" in low_guide.content
    assert "rule-based" not in low_guide.content
    assert "mock" not in low_guide.content


def test_diagnostic_probe_covers_learning_start_dimensions() -> None:
    lesson = Lesson(
        id=1,
        course_id=1,
        week="1",
        lesson_no="1",
        hours="2",
        lesson_code="0302",
        title="条件语句",
        content_summary="Python if 判断。",
        status="draft",
    )
    outline = KnowledgeOutline(
        id=1,
        lesson_id=1,
        ai_raw_output="知识主干：条件语句、前置概念、操作步骤、易错判断。",
        edited_content="知识主干：条件语句、前置概念、操作步骤、易错判断。",
        status="reviewed",
        generated_by_model="test-model",
    )

    drafts = generate_basic_lesson_drafts(lesson, outline)
    probe = next(draft for draft in drafts if draft.draft_type == "diagnostic_probe")

    for text in ["基础概念", "前置知识", "任务背景理解", "操作步骤", "易错判断", "安全规范", "职业素养"]:
        assert text in probe.content
    assert "不作为正式考试成绩" in probe.content
