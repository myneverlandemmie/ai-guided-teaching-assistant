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
            f"# {sanitized_lesson.lesson_code + '-' if sanitized_lesson.lesson_code else ''}{sanitized_lesson.title} 知识主干初稿",
            "",
            "生成说明：本内容由 Mock AI 规则生成，仅用于演示流程，必须由教师编辑确认后使用。",
            "",
            "## 1. 本节课定位",
            f"本节课围绕“{sanitized_lesson.title}”展开，教学内容摘要为：{sanitized_lesson.content_summary or '暂无摘要'}",
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
            "## 6. 课堂任务建议",
            "- 先做一个跟讲示例，再做一个独立练习。",
            "- 对错误较多的步骤安排即时反馈。",
            "",
            "## 7. 后续小测题方向",
            "- 围绕本课关键词设计 1 到 2 道基础题。",
            "- 题目应聚焦本节课主干知识，不扩展到复杂综合项目。",
            "",
            "## 8. 教师使用提示",
            "- 请根据本班学生基础删改目标、易错点和课堂任务。",
            "- 本初稿不是最终导学案，也不是自动批阅结果。",
        ]
    )
