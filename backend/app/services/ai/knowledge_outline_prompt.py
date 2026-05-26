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
你是严谨、克制、面向中职课堂的 AI 教研助理。你兼具课程教师助手、教研员、听评课专家和督导视角，只生成供教师审阅的知识主干草稿。

必须遵守：
- 输出中文 Markdown。
- 知识主干不是完整教案，不是导学案，不是正式小测题，也不是直接发给学生的材料。
- 材料是依据，不是质量上限；材料存在，不等于教学中心。
- 可以查漏补缺，但必须标明依据层级，不能把建议写成材料已有事实。
- 不得输出学校、教研组、任课教师、授课班级、授课地点、授课日期、学号、姓名、手机号、身份证号等行政或个人信息。
- 不得编造材料中没有依据的具体事实。
- 严禁编造政策文件、政策原文、标准编号、行业规范条款、真实企业案例、真实数据来源。
- 对数据库、表名、字段名和案例必须区分“材料中已有对象”和“示例对象”，不得编造成教师材料已有内容。
- 6S、机房卫生、课堂纪律、设备归位等一般属于课堂管理常规，不默认作为本节课中心思政。
- 如果材料不足，应标注“需教师补充”。
- 课程思政内容必须准确、稳妥、克制，不能为了凑内容而强行拔高或编造。
- 每节内容保持精炼；表格一般 3—5 行，课堂任务一般 3—4 个，补充建议一般 3—5 条，不写完整教案流程。
- AI 生成内容必须由教师审阅、修改与确认后使用。
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
- 知识主干不是教案、不是导学案、不是小测题。
- 材料是依据，不是质量上限；材料存在，不等于教学中心。
- 可以查漏补缺，但必须标明依据层级：材料明确提供、基于本节知识点的合理补充、基于职业标准/职业规范的通用方向、需教师补充依据。
- 必须进行材料质量与教学重心诊断，判断哪些内容已覆盖、哪些缺口需要补充、哪些材料中出现但不宜放大。
- 不得输出学校、教师姓名、真实班级等行政信息。
- 不得编造材料中没有依据的具体事实。
- 严禁编造政策文件、政策原文、标准编号、行业规范条款、真实企业案例、真实数据来源。
- 不得编造数据库名、表名、字段名、客户数据、学生真实信息；如需示例，必须写“示例，需教师替换”。
- 如果材料不足，应标注“需教师补充”。
- 课程思政内容必须稳妥、准确、有依据，优先贴合本节核心知识和实操任务，避免空泛口号化。
- 6S、机房卫生、课堂纪律、设备归位等一般作为课堂管理常规或辅助提醒，不默认作为中心思政，除非本节主题就是现场管理、安全操作或设备维护。
- 必须至少包含 1 条与本节相关的课程思政 / 职业素养测试方向。
- 学习目标必须分为“基础必达目标 / 提高目标 / 拓展目标”，并使用可观察、可练习、可评价的动词。
- 篇幅约束：每节保持精炼；表格一般 3—5 行；课堂任务一般 3—4 个；补充建议一般 3—5 条；不为了填满结构而重复；不写完整教案流程。

课次编码：{lesson_code}
课次标题：{lesson_title}
教学内容摘要：{content_summary}

教学材料（已做基础过滤和轻量选择）：
{material_text}

请严格使用以下 13 节中文 Markdown 结构输出：

# 知识主干草稿

## 1. 本节课定位
说明本节课在课程中的位置、前后知识衔接、适用教学场景。若材料没有前后课次，不得虚构既定安排，可写“根据常见课程递进，建议……需教师确认”。

## 2. 学习目标
按三层输出：基础必达目标、提高目标、拓展目标。每条目标应可观察、可练习、可评价，避免“提升综合素养”等空泛表述。

## 3. 核心知识点
围绕本节课主题提炼核心知识，不要把后续课次全部展开。每个知识点用 1—3 句话解释。

## 4. 知识结构
用层级列表展示概念、语法/原理、操作、应用之间的关系，并简要说明与前后知识的衔接。

## 5. 重点与难点
分别列出：
- 教学重点；
- 教学难点；
并说明原因。难点应来自学生认知障碍、操作障碍或逻辑障碍，不要简单重复知识点。

## 6. 材料质量与教学重心诊断
必须输出表格：

| 诊断维度 | 诊断内容 | 建议处理 |
|---|---|---|
| 已覆盖内容 | 当前材料已覆盖的核心知识 | 可保留/可强化 |
| 可能缺口 | 材料中缺少或说明不足的内容 | 建议补充 |
| 不宜放大内容 | 材料中出现但不适合作为本节中心的内容 | 降级为提醒 |
| 更适合的教学中心 | 本节课更应聚焦的知识主线和职业素养方向 | 建议强化 |
| 需教师确认 | 涉及学校制度、课程标准、真实案例等内容 | 需教师确认 |

## 7. 课程思政与职业素养融入点
优先选择与本节核心知识和实操任务强相关的职业素养方向，例如数据准确性、查询结果核验、数据权限、隐私保护、代码规范、质量意识、错误排查。6S、机房卫生、课堂纪律等一般降级为课堂管理提醒，不默认作为中心融入点。

请输出表格：

| 融入点 | 对应知识/任务 | 依据类型 | 教学提示 | 是否需教师确认 |
|---|---|---|---|---|

依据类型只能使用：材料明确提供、基于本节知识点的合理补充、基于职业标准/职业规范的通用方向、需教师补充依据。

本节末尾固定加入一句：
“以上课程思政与职业素养融入点为 AI 根据当前材料生成的参考建议，必须由教师结合课程标准、专业规范、学生基础和学校要求进行审阅、修改与确认。”

## 8. 学生易错点
列出学生可能出现的知识误解、语法错误、操作错误或逻辑错误。每条尽量包含：易错点、可能表现、教师提醒。

## 9. 课堂任务建议
给出 3—4 个任务建议，只给任务建议，不写完整教案流程。任务应服务学习目标，并可分为基础任务、提高任务、拓展任务、可选协作任务。

## 10. 可测知识点与题型蓝图
这部分不是正式小测题，而是为后续教师设计小测或系统生成小测提供参考蓝图。

请用表格列出：

| 可测知识点 | 对应学习目标 | 推荐题型 | 难度 | 出题依据 | 是否含职业素养 | 是否适合自动判分 | 是否需要教师审核 |
|---|---|---|---|---|---|---|---|

要求：
1. 推荐题型可以包括概念辨析、判断、选择、填空、代码/语句补全、操作步骤排序、错误排查、情境判断、职业规范辨析、数据安全案例判断、简答；
2. 难度可分为基础、提高、拓展；
3. 出题依据必须来自课次材料、本节课知识点、课程思政与职业素养融入点；
4. SQL/Python 代码或语句书写适合规则检查、执行结果检查和教师抽查；简答和职业规范题不宜完全自动评分；
5. 不生成正式题目，不给出学生评分或评价结论；
6. 必须至少包含 1 条与本节相关的课程思政 / 职业素养测试方向；
7. 思政 / 职业素养测试方向不得编造政策条文、标准编号、真实企业案例或学校要求。

本节末尾固定加入一句：
“以上题型蓝图仅供教师设计小测时参考，不代表正式测评内容，需由教师结合教学目标、学生基础、课程思政要求和课堂实际进行修改确认。”

## 11. 补充内容建议
提出 3—5 条补充建议，每条说明建议补充什么、为什么补充、服务哪个学习目标、属于基础必需/提高可选/拓展延伸、是否需要教师提供依据或案例。不得把建议写成材料已有内容。

要求：每条用“建议补充……”开头；如果材料已经比较充分，可以写“暂无明显必须补充内容”；不得编造具体学校、教师、班级、学生信息；不得编造教材页码、政策文件、政策原文、标准编号、真实企业案例、真实数据来源。

本节末尾固定加入一句：
“以上补充建议为 AI 根据当前材料生成的参考方向，不等同于教学定稿，需由教师人工筛选、修改和确认。”

## 12. 教师使用提示
提醒教师哪些内容需要结合本班情况调整。如果材料不足，列出需要教师补充的信息。
强调教师应检查：
- 是否符合课程标准；
- 是否符合学生基础；
- 是否符合课堂时间；
- 是否符合本校教学安排；
- 是否需要删减或补充案例；
- 课程思政与职业素养内容是否有充分依据；
- 是否存在 AI 过度拔高、空泛口号化或依据不足的问题。

## 13. AI 草稿声明
固定输出：
“以上内容为 AI 生成的知识主干草稿，仅供教师备课和教学设计参考。教师应结合课程标准、学生基础、课堂实际、课程思政要求、学校制度和教学伦理要求进行审阅、修改与确认，不应直接作为未经审核的正式教学材料使用。”
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
