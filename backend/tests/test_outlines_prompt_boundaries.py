import re

import pytest

from app.models.lesson import Lesson, LessonMaterial
from app.services.ai.deepseek_client import build_knowledge_outline_prompt
from app.services.ai.sanitizer import sanitize_text_for_outline


def test_sanitizer_covers_common_administrative_variants() -> None:
    source = "\n".join(
        [
            "学校名称：示例学校",
            "教师：张老师",
            "任课老师：张老师",
            "班级：23物联网2班",
            "学校 | 示例学校",
            "授课班级 23物联网2班",
            "本课面向23物联网2班开展条件查询练习。",
            "教学目标：掌握 WHERE 条件查询。",
            "实验步骤：编写 SQL 语句。",
            "张老师提醒学生核验结果。",
            "连接 student 表、score 表、学生表、教师表。",
            "API Key: sk-test-secret-123456",
            "Token: bearer abcdefghijklmnop",
            "密码：test-password",
        ]
    )

    sanitized = sanitize_text_for_outline(source)

    assert "示例学校" not in sanitized
    assert "张老师" not in sanitized
    assert "23物联网2班" not in sanitized
    assert "某班级" in sanitized
    assert "sk-test-secret-123456" not in sanitized
    assert "abcdefghijklmnop" not in sanitized
    assert "test-password" not in sanitized
    assert "教学目标" in sanitized
    assert "WHERE" in sanitized
    assert "实验步骤" in sanitized
    assert "student 表" in sanitized
    assert "score 表" in sanitized
    assert "学生表" in sanitized
    assert "教师表" in sanitized


def test_deepseek_prompt_filters_sensitive_material_information() -> None:
    lesson = Lesson(
        course_id=1,
        planned_lesson_id=None,
        week="1",
        lesson_no="1",
        hours="2",
        lesson_code="0402",
        title="WHERE 条件查询",
        content_summary="班级：23物联网2班\n讲解 WHERE 与 IN关键字。",
        status="draft",
    )
    material = LessonMaterial(
        lesson_id=1,
        material_type="pasted_text",
        title="虚构材料",
        content="\n".join(
            [
                "学校：示例学校",
                "学校名称：示例学校",
                "学校 | 示例学校",
                "教师：张老师",
                "任课教师：张老师",
                "任课老师：张老师",
                "班级：23物联网2班",
                "授课班级：23物联网2班",
                "授课班级 23物联网2班",
                "教学目标：掌握 WHERE 条件查询。",
                "重点：WHERE、IN关键字 的使用。",
                "难点：多个条件组合。",
                "API Key: sk-test-secret-123456",
                "Token: bearer abcdefghijklmnop",
                "密码：test-password",
                "连接 student 表、score 表、学生表、教师表。",
            ]
        ),
    )

    prompt = build_knowledge_outline_prompt(lesson, [material])

    assert "示例学校" not in prompt
    assert "张老师" not in prompt
    assert "23物联网2班" not in prompt
    assert "sk-test-secret-123456" not in prompt
    assert "abcdefghijklmnop" not in prompt
    assert "test-password" not in prompt
    assert "教学目标" in prompt
    assert "WHERE" in prompt
    assert "IN关键字" in prompt
    assert "重点" in prompt
    assert "难点" in prompt
    assert "student 表" in prompt
    assert "score 表" in prompt
    assert "学生表" in prompt
    assert "教师表" in prompt


def test_knowledge_outline_prompt_contains_fixed_sections_and_disclaimers() -> None:
    lesson = Lesson(
        course_id=1,
        planned_lesson_id=None,
        week="1",
        lesson_no="1",
        hours="2",
        lesson_code="0402",
        title="WHERE 条件查询",
        content_summary="条件查询。",
        status="draft",
    )
    material = LessonMaterial(
        lesson_id=1,
        material_type="pasted_text",
        title="虚构材料",
        content="\n".join(
            [
                "学校：示例学校",
                "任课教师：张老师",
                "授课班级：23物联网2班",
                "教学目标：掌握 WHERE 条件查询。",
                "重点：理解数据筛选条件。",
            ]
        ),
    )

    prompt = build_knowledge_outline_prompt(lesson, [material])

    for section in [
        "## 1. 本节课定位",
        "## 2. 学习目标",
        "## 3. 核心知识点",
        "## 4. 知识结构",
        "## 5. 重点与难点",
        "## 6. 材料结构分析与教学重心提醒",
        "## 7. 课程思政与职业素养融入点",
        "## 8. 学生易错点",
        "## 9. 课堂任务建议",
        "## 10. 可测知识点与题型蓝图",
        "## 11. 补充内容建议",
        "## 12. 教师使用提示",
        "## 13. AI 草稿声明",
    ]:
        assert section in prompt
    assert "材料是依据，不是质量上限" in prompt
    assert "材料存在，不等于教学中心" in prompt
    assert "基础必达目标" in prompt
    assert "提高目标" in prompt
    assert "拓展目标" in prompt
    assert "6S、机房卫生、课堂纪律" in prompt
    assert "不默认作为中心融入点" in prompt
    assert "技术准确性优先" in prompt
    assert "课程、语言、数据库、开发板、平台、软件版本或工具链" in prompt
    assert "不确定" in prompt
    assert "需教师确认" in prompt
    assert "不得主动引入无关差异" in prompt
    assert "教学类比" in prompt
    assert "真实执行机制" in prompt
    assert "SQL/数据库课程示例" in prompt
    sql_example_match = re.search(r"SQL/数据库课程示例：.+GROUP_CONCAT.+DISTINCT.+GROUP BY.+组合", prompt)
    assert sql_example_match is not None
    assert "GROUP_CONCAT" in prompt
    assert "GROUP_CONCAT(DISTINCT 字段)" in prompt
    assert "按多个字段组成的组合键进行分组" in prompt
    assert "MySQL 课程" in prompt
    assert "学生导学案素材提取" in prompt
    for course_keyword in ["Python", "C", "Arduino", "单片机", "传感器", "物联网项目", "专业英语"]:
        assert course_keyword in prompt
    assert "不得把 SQL 规则迁移到无关课程" in prompt
    assert "客户为先、服务意识、创新精神" in prompt
    assert "不得自动作为本节中心思政" in prompt
    assert "不同课程应优先选择与本节核心任务更贴合的职业素养方向" in prompt
    for professional_quality in ["数据准确性", "代码规范", "接线规范", "术语准确性"]:
        assert professional_quality in prompt
    assert "审阅、修改与确认" in prompt
    assert "严禁编造政策文件、政策原文、标准编号、行业规范条款、真实企业案例、真实数据来源" in prompt
    assert "以上课程思政与职业素养融入点为 AI 根据当前材料生成的参考建议" in prompt
    assert "以上题型蓝图仅供教师设计小测时参考" in prompt
    assert "必须至少包含 1 条与本节相关的课程思政 / 职业素养测试方向" in prompt
    assert "以上补充建议为 AI 根据当前材料生成的参考方向" in prompt
    assert "不得输出学校、教师姓名、真实班级等行政信息" in prompt
    assert "示例学校" not in prompt
    assert "张老师" not in prompt
    assert "23物联网2班" not in prompt


def test_deepseek_prompt_prioritizes_key_material_and_limits_length(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_PROMPT_MATERIAL_MAX_CHARS", "9000")
    lesson = Lesson(
        course_id=1,
        planned_lesson_id=None,
        week="1",
        lesson_no="1",
        hours="2",
        lesson_code="0402",
        title="WHERE 条件查询",
        content_summary="条件查询。",
        status="draft",
    )
    material = LessonMaterial(
        lesson_id=1,
        material_type="pasted_text",
        title="长材料",
        content="\n".join(
            [
                *(f"普通铺垫内容 {index}" for index in range(80)),
                "学校名称：示例学校",
                "教学目标：掌握 WHERE 子句。",
                "实验步骤：编写 SQL 条件查询。",
            ]
        ),
    )

    prompt = build_knowledge_outline_prompt(lesson, [material])

    assert len(prompt) <= 9000
    assert "教学目标" in prompt
    assert "实验步骤" in prompt
    assert "SQL" in prompt
    assert "示例学校" not in prompt
