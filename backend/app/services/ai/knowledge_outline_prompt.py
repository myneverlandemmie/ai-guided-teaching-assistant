"""知识主干生成 Prompt 模板。"""

from __future__ import annotations

import re

from app.models.lesson import Lesson, LessonMaterial
from app.services.ai.sanitizer import sanitize_lesson_for_outline, sanitize_materials_for_outline, sanitize_text_for_outline

PRIORITY_MATERIAL_KEYWORDS = (
    "教学目标",
    "学习目标",
    "重点",
    "难点",
    "实验步骤",
    "操作步骤",
    "任务",
    "代码",
    "SQL",
    "Python",
    "易错",
    "评价",
)

KNOWLEDGE_OUTLINE_SYSTEM_MESSAGE = """
你是严谨、克制、面向中职课堂的课程教学设计助手。你只生成供教师审阅的知识主干草稿，不生成最终教案，不生成正式学生讲义，不生成正式测评题。

必须遵守：
- 输出中文 Markdown。
- 不得输出学校、教研组、任课教师、授课班级、授课地点、授课日期、学号、姓名、手机号、身份证号等行政或个人信息。
- 不得编造材料中没有依据的具体事实。
- 严禁编造政策文件、政策原文、标准编号、行业规范条款、真实企业案例、真实数据来源。
- 如果材料不足，应标注“需教师补充”。
- 课程思政内容必须准确、稳妥、克制，不能为了凑内容而强行拔高或编造。
- AI 生成内容必须由教师修改确认后使用。
""".strip()


def _split_material_lines(text: str) -> list[str]:
    """把材料拆成适合 prompt 选择的轻量文本行。"""

    lines: list[str] = []
    for raw_line in text.splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        if line:
            lines.append(line)
    return lines


def _is_priority_material_line(line: str) -> bool:
    """判断材料行是否包含应优先保留的教学关键词。"""

    return any(keyword.lower() in line.lower() for keyword in PRIORITY_MATERIAL_KEYWORDS)


def _append_with_limit(target: list[str], seen: set[str], line: str, max_chars: int, current_length: int) -> int:
    """按长度上限追加行，返回新的长度。"""

    if not line or line in seen:
        return current_length
    separator_length = 1 if target else 0
    next_length = current_length + separator_length + len(line)
    if next_length > max_chars:
        remaining = max_chars - current_length - separator_length
        if remaining > 20:
            target.append(line[:remaining])
            seen.add(line)
            return max_chars
        return current_length
    target.append(line)
    seen.add(line)
    return next_length


def build_limited_material_context(material_text: str, max_chars: int) -> str:
    """在脱敏后材料中优先选择关键教学内容，不做 RAG 或复杂摘要。"""

    if max_chars <= 0:
        return ""

    lines = _split_material_lines(sanitize_text_for_outline(material_text))
    priority_lines = [line for line in lines if _is_priority_material_line(line)]
    normal_lines = [line for line in lines if not _is_priority_material_line(line)]

    selected: list[str] = []
    seen: set[str] = set()
    current_length = 0
    for line in [*priority_lines, *normal_lines]:
        current_length = _append_with_limit(selected, seen, line, max_chars, current_length)
        if current_length >= max_chars:
            break
    return "\n".join(selected)


def _render_prompt(lesson_code: str, lesson_title: str, content_summary: str, material_text: str) -> str:
    """渲染固定结构的知识主干 prompt。"""

    return f"""
请基于课次信息和教学材料，为教师生成“知识主干草稿”。

输入边界：
- 输出供教师审阅；AI 生成内容必须由教师修改确认。
- 不得输出学校、教师姓名、真实班级等行政信息。
- 不得编造材料中没有依据的具体事实。
- 严禁编造政策文件、政策原文、标准编号、行业规范条款、真实企业案例、真实数据来源。
- 如果材料不足，应标注“需教师补充”。
- 课程思政内容必须稳妥、准确、有依据，避免空泛口号化。
- 必须至少包含 1 条与本节相关的课程思政 / 职业素养测试方向。

课次编码：{lesson_code}
课次标题：{lesson_title}
教学内容摘要：{content_summary}

教学材料（已做基础过滤和轻量选择）：
{material_text}

请严格使用以下中文 Markdown 结构输出：

# 知识主干草稿

## 1. 本节课定位
说明本节课在课程中的位置、前后知识衔接、适用教学场景。

## 2. 学习目标
用 3—5 条列出学生完成本节课后应掌握的内容。尽量使用“能……”“会……”“理解……”等可观察表述。

## 3. 核心知识点
列出本节课最重要的知识点。每个知识点用 1—3 句话解释。

## 4. 知识结构
用层级列表展示本节课知识之间的关系。可以体现“概念 → 语法/原理 → 操作 → 应用”的递进。

## 5. 重点与难点
分别列出：
- 教学重点；
- 教学难点；
并说明原因。

## 6. 课程思政与职业素养融入点
这是本模板的重点部分之一，必须单独输出，不能省略。

要求：
1. 优先依据课次材料中已经出现的职业场景、操作规范、行业标准、数据安全、质量意识、团队协作、职业伦理等内容提炼；
2. 严禁编造政策文件、政策原文、标准编号、行业规范条款、真实企业案例、真实数据来源；
3. 如果材料中没有明确思政内容，不要强行编造，可以从职业道德、职业规范、数据安全与隐私保护、质量意识、工匠精神、责任意识、协作沟通、遵守行业标准、安全操作意识、服务社会与技术向善等通用职业素养方向提出“建议融入方向”；
4. 每条必须标注依据类型：“来自材料”“基于本节知识点的建议方向”“需教师补充依据”；
5. 如果无法确认依据，必须写“需教师补充依据”，不能当作事实陈述；
6. 语言应稳妥、自然、适合中职课堂，不要空泛口号化。

请输出表格：

| 融入点 | 对应知识/任务 | 依据类型 | 教学提示 |
|---|---|---|---|

本节末尾固定加入一句：
“以上课程思政与职业素养融入点为 AI 根据当前材料生成的参考建议，必须由教师结合课程标准、专业规范、学生基础和学校要求进行审阅、修改与确认。”

## 7. 学生易错点
列出学生可能出现的误解、操作错误或概念混淆。每条尽量给出教师提醒方式。

## 8. 课堂任务建议
给出 2—4 个课堂任务建议。任务应适合中职学生，避免过难。如适合，可以在任务中自然融入职业规范、质量意识、数据安全或协作意识，但不得强行拔高。

## 9. 可测知识点与题型蓝图
这部分不是正式小测题，而是为后续教师设计小测或系统生成小测提供参考蓝图。

请用表格列出：

| 可测知识点 | 对应学习目标 | 推荐题型 | 难度 | 出题依据 | 是否含思政/职业素养 | 教师需确认 |
|---|---|---|---|---|---|---|

要求：
1. 推荐题型可以包括概念辨析、判断、选择、填空、代码/语句补全、操作步骤排序、错误排查、情境判断、职业规范辨析、数据安全案例判断、简答；
2. 难度可分为基础、提高、拓展；
3. 出题依据必须来自课次材料、本节课知识点、课程思政与职业素养融入点；
4. 如果依据不足，请写“需教师补充材料依据”；
5. 不生成正式题目；
6. 不给出学生评分或评价结论；
7. 必须至少包含 1 条与本节相关的课程思政 / 职业素养测试方向；
8. 思政 / 职业素养测试方向不得编造政策条文、标准编号、真实企业案例或学校要求。

本节末尾固定加入一句：
“以上题型蓝图仅供教师设计小测时参考，不代表正式测评内容，需由教师结合教学目标、学生基础、课程思政要求和课堂实际进行修改确认。”

## 10. 补充内容建议
这部分允许 AI 根据材料缺口提出建议，但必须保持建议性质，不能当成事实定稿。

请分条列出：
- 建议补充的概念说明；
- 建议补充的操作示例；
- 建议补充的课堂演示；
- 建议补充的生活化或职业场景案例；
- 建议补充的学生练习材料；
- 建议补充的易错提醒；
- 建议补充的课程思政或职业素养材料依据。

要求：
1. 每条用“建议补充……”开头；
2. 如果材料已经比较充分，可以写“暂无明显必须补充内容”；
3. 不得编造具体学校、教师、班级、学生信息；
4. 不得编造教材页码、政策文件、政策原文、标准编号、真实企业案例、真实数据来源；
5. 可以给出通用示例方向，但必须标注“示例方向”；
6. 不涉及学生评分、学生能力判断或个人评价；
7. 课程思政相关补充建议必须标明“需教师确认依据”。

本节末尾固定加入一句：
“以上补充建议为 AI 根据当前材料生成的参考方向，不等同于教学定稿，需由教师人工筛选、修改和确认。”

## 11. 教师使用提示
提醒教师哪些内容需要结合本班情况调整。如果材料不足，列出需要教师补充的信息。
强调教师应检查：
- 是否符合课程标准；
- 是否符合学生基础；
- 是否符合课堂时间；
- 是否符合本校教学安排；
- 是否需要删减或补充案例；
- 课程思政与职业素养内容是否有充分依据；
- 是否存在 AI 过度拔高、空泛口号化或依据不足的问题。

## 12. AI 草稿声明
固定输出：
“以上内容为 AI 生成的知识主干草稿，供教师备课和教学设计参考。教师应结合课程标准、学生基础、课堂实际、课程思政要求和教学伦理要求进行审阅、修改与确认，不应直接作为未经审核的正式教学材料使用。”
""".strip()


def build_knowledge_outline_prompt(lesson: Lesson, materials: list[LessonMaterial], max_chars: int) -> str:
    """构造知识主干生成 prompt，并在输入阶段过滤行政和个人信息。"""

    sanitized_lesson = sanitize_lesson_for_outline(lesson)
    sanitized_materials = sanitize_materials_for_outline(materials)
    sanitized_material = "\n".join(material.content for material in sanitized_materials if material.content).strip()

    lesson_code = sanitized_lesson.lesson_code or "未设置"
    lesson_title = sanitized_lesson.title or "未设置"
    content_summary = sanitized_lesson.content_summary or "暂无"
    empty_hint = "当前课次未添加教学材料，请仅基于课次标题和教学内容摘要生成基础知识主干；材料不足处请标注“需教师补充”。"

    base_prompt = _render_prompt(lesson_code, lesson_title, content_summary, "")
    material_limit = max(0, max_chars - len(base_prompt) - 16)
    material_text = build_limited_material_context(sanitized_material, material_limit) if sanitized_material else empty_hint
    prompt = _render_prompt(lesson_code, lesson_title, content_summary, material_text)
    if len(prompt) > max_chars:
        overflow = len(prompt) - max_chars
        trim_to = max(0, len(material_text) - overflow - 8)
        prompt = _render_prompt(lesson_code, lesson_title, content_summary, material_text[:trim_to])
    return sanitize_text_for_outline(prompt)
