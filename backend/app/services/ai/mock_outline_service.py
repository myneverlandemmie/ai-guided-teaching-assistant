"""Mock AI 知识主干生成服务。

本服务只生成可测试的中文初稿，不调用真实 AI API。
"""

from __future__ import annotations

import re

from app.models.lesson import Lesson, LessonMaterial
from app.services.ai.sanitizer import sanitize_lesson_for_outline, sanitize_materials_for_outline, sanitize_text_for_outline

MOCK_OUTLINE_MODEL_NAME = "mock-ai-v0.2"
KEYWORD_PATTERNS = (
    "SELECT",
    "WHERE",
    "JOIN",
    "INNER JOIN",
    "OUTER JOIN",
    "GROUP BY",
    "HAVING",
    "ORDER BY",
    "IN",
    "EXISTS",
    "Python",
    "print",
    "input",
    "if",
    "for",
    "while",
    "def",
)

def sanitize_material_text_for_outline(text: str) -> str:
    """过滤不应进入知识主干的行政信息和个人信息。

    Args:
        text: 原始教学材料文本。

    Returns:
        仅供生成知识主干使用的过滤文本。

    Raises:
        不主动抛出业务异常。
    """

    return sanitize_text_for_outline(text)


def extract_teaching_relevant_text(text: str) -> str:
    """提取生成知识主干所需的教学相关文本。

    Args:
        text: 原始教学材料文本。

    Returns:
        已过滤行政和个人信息的教学文本。

    Raises:
        不主动抛出业务异常。
    """

    return sanitize_material_text_for_outline(text)


def _compact_text(text: str, max_length: int = 500) -> str:
    """压缩材料文本，避免 Mock 输出过长。"""

    compacted = re.sub(r"\s+", " ", text).strip()
    if len(compacted) <= max_length:
        return compacted
    return f"{compacted[:max_length]}..."


def _collect_material_keywords(material_text: str) -> list[str]:
    """从材料中提取少量 SQL / Python 关键词，保留到知识主干中。"""

    found: list[str] = []
    for keyword in KEYWORD_PATTERNS:
        if re.search(rf"(?<![A-Za-z]){re.escape(keyword)}(?![A-Za-z])", material_text, re.IGNORECASE):
            found.append(keyword)
    return found


def generate_mock_knowledge_outline(lesson: Lesson, materials: list[LessonMaterial]) -> str:
    """基于课次和教学材料生成 Mock 知识主干。

    Args:
        lesson: 正式课次对象。
        materials: 当前课次已添加的教学材料列表。

    Returns:
        中文知识主干初稿。

    Raises:
        不主动抛出业务异常；调用方负责保存。
    """

    sanitized_lesson = sanitize_lesson_for_outline(lesson)
    sanitized_materials = sanitize_materials_for_outline(materials)
    sanitized_material_text = "\n".join(material.content for material in sanitized_materials)
    material_keywords = _collect_material_keywords(sanitized_material_text)
    material_excerpt = _compact_text(sanitized_material_text)
    keyword_text = "、".join(material_keywords) if material_keywords else "结合课次标题与教学内容梳理基础概念"
    material_hint = material_excerpt if material_excerpt else "当前课次尚未添加教学材料，本初稿仅根据课次标题和教学内容摘要生成。"

    # Mock 输出必须让教师可编辑，不能伪装成真实大模型最终结论。
    return "\n".join(
        [
            f"# {sanitized_lesson.lesson_code + '-' if sanitized_lesson.lesson_code else ''}{sanitized_lesson.title} 知识主干草稿",
            "",
            "生成说明：本内容由 Mock AI 规则生成，仅用于演示流程，仅供教师参考，需教师审阅、修改与确认。",
            "",
            "## 1. 本节课定位",
            f"本节课围绕“{sanitized_lesson.title}”展开，教学内容摘要为：{sanitized_lesson.content_summary or '暂无摘要'}",
            "建议教师结合课程标准、班级基础和课堂时间确认前后知识衔接。",
            "",
            "## 2. 学习目标",
            "- 理解本课核心概念和基本应用场景。",
            "- 能根据课堂任务完成基础练习。",
            "- 能用规范表达说明自己的解题思路。",
            "",
            "## 3. 核心知识点",
            f"- 课次关键词：{keyword_text}。",
            f"- 材料线索：{material_hint}",
            "",
            "## 4. 知识结构",
            "- 概念引入：从任务场景说明为什么需要本课知识。",
            "- 方法讲解：结合示例拆解基本语法、步骤或操作流程。",
            "- 练习巩固：安排由易到难的课堂任务。",
            "",
            "## 5. 学生易错点",
            "- 容易只记语法形式，忽略适用条件。",
            "- 容易在输入输出、条件组合或关键字位置上出现格式错误。",
            "- 需要教师结合学生提交结果进行二次讲解。",
            "",
            "## 6. 课程思政与职业素养融入点",
            "| 融入点 | 对应知识/任务 | 依据类型 | 教学提示 |",
            "|---|---|---|---|",
            "| 数据安全与隐私保护 | 查询和筛选数据时注意最小授权，避免随意泄露结果 | 基于本节知识点的建议方向 | 结合课堂示例提醒学生不要把真实个人信息写入测试数据 |",
            "| 查询结果核验与质量意识 | 对 WHERE、JOIN、GROUP BY 等结果进行复核 | 基于本节知识点的建议方向 | 提醒学生完成后先核对结果再提交 |",
            "以上课程思政与职业素养融入点为 AI 根据当前材料生成的参考建议，必须由教师结合课程标准、专业规范、学生基础和学校要求进行审阅、修改与确认。",
            "",
            "## 7. 学生易错点",
            "- 容易只记语法形式，忽略适用条件。",
            "- 容易在输入输出、条件组合或关键字位置上出现格式错误。",
            "- 需要教师结合学生提交结果进行二次讲解。",
            "",
            "## 8. 课堂任务建议",
            "- 先做一个跟讲示例，再做一个独立练习。",
            "- 对错误较多的步骤安排即时反馈。",
            "- 将数据安全、操作规范和结果核验作为课堂评价点。",
            "",
            "## 9. 可测知识点与题型蓝图",
            "| 可测知识点 | 对应学习目标 | 推荐题型 | 难度 | 出题依据 | 是否含思政/职业素养 | 教师需确认 |",
            "|---|---|---|---|---|---|---|",
            f"| {keyword_text} | 理解并能在任务中使用本课核心知识 | 概念辨析 / 选择 / 操作步骤排序 | 基础 | 课次标题、教学材料与课堂任务 | 是 | 需教师确认材料依据 |",
            "| 数据安全与查询结果核验 | 形成规范操作和结果复核意识 | 情境判断 / 职业规范辨析 | 提高 | 课程思政与职业素养融入点 | 是 | 需教师确认依据 |",
            "以上题型蓝图仅供教师设计小测时参考，不代表正式测评内容，需由教师结合教学目标、学生基础、课程思政要求和课堂实际进行修改确认。",
            "",
            "## 10. 补充内容建议",
            f"- 建议补充概念说明：可结合“{sanitized_lesson.title}”补充基础概念和应用场景示例。",
            "- 建议补充操作示例：补充 1 个完整课堂演示，示例方向可贴近真实任务流程。",
            "- 建议补充课堂演示：补充错误示例与正确示例对照。",
            "- 建议补充生活化或职业场景案例：示例方向可采用学生熟悉的数据筛选、查询核验或规范操作场景。",
            "- 建议补充学生练习材料：增加 1 组由易到难的基础练习。",
            "- 建议补充易错提醒：明确输入输出、关键字位置和结果核验提醒。",
            "- 建议补充课程思政或职业素养材料依据：需教师确认依据，避免编造政策文件、政策原文、标准编号、真实企业案例或真实数据来源。",
            "以上补充建议为 AI 根据当前材料生成的参考方向，不等同于教学定稿，需由教师人工筛选、修改和确认。",
            "",
            "## 11. 教师使用提示",
            "- 请根据本班学生基础删改目标、易错点和课堂任务。",
            "- 若材料不足，请补充课程标准要求、操作示范和课堂评价方式。",
            "- 请检查课程思政与职业素养内容是否有依据，避免空泛口号化或过度拔高。",
            "- 本初稿不是最终导学案，也不是自动批阅结果。",
            "",
            "## 12. AI 草稿声明",
            "以上内容为 AI 生成的知识主干草稿，供教师备课和教学设计参考。教师应结合课程标准、学生基础、课堂实际、课程思政要求和教学伦理要求进行审阅、修改与确认，不应直接作为未经审核的正式教学材料使用。",
        ]
    )
