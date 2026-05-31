"""课前学情测试与三阶导学案草稿生成服务。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from openpyxl import Workbook

from app.models.knowledge_outline import KnowledgeOutline
from app.models.lesson import Lesson
from app.models.lesson_draft import LessonDraft

DRAFT_TYPE_LABELS = {
    "diagnostic_probe": "课前学情测试",
    "guide_low": "全班通用导学案 / 基础版导学案",
    "guide_mid": "巩固提升任务包",
    "guide_high": "拓展探究任务包",
    "teaching_prep_reference": "备课参考建议",
}
CHAOXING_HEADERS = [
    "目录",
    "题目类型",
    "大题题干",
    "小题题型",
    "小题题干",
    "正确答案",
    "答案解析",
    "难易度",
    "知识点",
    "标签",
    "选项数",
    "选项A",
    "选项B",
    "选项C",
    "选项D",
    "选项E",
    "选项F",
    "选项G",
    "选项H",
]


@dataclass(frozen=True)
class GeneratedLessonDraft:
    """本地结构化草稿生成结果。"""

    draft_type: str
    title: str
    content: str
    generated_by: str = "rule_based"


@dataclass(frozen=True)
class DiagnosticQuestion:
    """课前学情测试题目结构。"""

    question_type: str
    prompt: str
    answer: str
    explanation: str
    diagnosis_point: str
    difficulty: str
    options: list[str]


@dataclass(frozen=True)
class DiagnosticQuestionBlock:
    """带原始 Markdown 块的课前学情测试题目。"""

    index: int
    question: DiagnosticQuestion
    raw_markdown: str


def _lesson_name(lesson: Lesson) -> str:
    """生成适合页面展示的课次名称。"""

    return f"{lesson.lesson_code}-{lesson.title}" if lesson.lesson_code else lesson.title


def _outline_excerpt(outline: KnowledgeOutline, max_length: int = 500) -> str:
    """取知识主干摘要，避免本地结构化草稿过长。"""

    source = (outline.edited_content or outline.ai_raw_output or "").strip()
    if len(source) <= max_length:
        return source
    return f"{source[:max_length]}..."


def _build_diagnostic_probe(lesson: Lesson, outline: KnowledgeOutline) -> GeneratedLessonDraft:
    lesson_name = _lesson_name(lesson)
    excerpt = _outline_excerpt(outline, 420)
    content = f"""# {lesson_name}｜课前学情测试草稿

> 本前测用于判断学习起点，不作为正式考试成绩。教师可复制到学习通或其他平台后自行筛选、修改和发布。

## 前测依据

- 来源知识主干：{outline.id}
- 核心材料摘要：{excerpt or "暂无知识主干摘要，需教师补充。"}
- 诊断范围：基础概念、前置知识、任务背景理解、操作步骤、易错判断、安全规范、职业素养和进入本课任务所需的准备知识。

## 前测题目

### 题目 1
- 题型：单选题
- 题干：本节课开始前，学生最需要先弄清楚的是哪一项？
- 选项：A. 记住全部材料原文；B. 识别核心概念并完成基础任务；C. 跳过基础直接做拓展；D. 只关注课堂纪律
- 参考答案：B
- 简短解析：前测关注学习起点，应先判断学生是否理解核心概念和基础任务。
- 诊断点：核心任务识别
- 难度：基础

### 题目 2
- 题型：判断题
- 题干：如果学生对本节课的关键术语还不熟悉，导学案应提供更细步骤和更多示例。
- 参考答案：正确
- 简短解析：需要更多支撑的学生可以先使用基础版导学案。
- 诊断点：学习支持需求
- 难度：基础

### 题目 3
- 题型：填空题
- 题干：进入本课任务前，学生至少应知道一个与本课相关的前置概念或______步骤。
- 参考答案：基础练习 / 基础操作 / 基础应用
- 简短解析：前测用于判断学生是否具备进入课堂任务的准备。
- 诊断点：前置知识与基础操作准备
- 难度：基础

### 题目 4
- 题型：单选题
- 题干：完成课堂任务时，遇到结果、现象或步骤不确定，更合适的处理方式是？
- 选项：A. 直接猜测；B. 写成确定结论；C. 记录问题并请教师确认；D. 忽略不处理
- 参考答案：C
- 简短解析：记录和核验能帮助学生形成规范的学习与操作习惯。
- 诊断点：易错判断与过程记录意识
- 难度：中等

### 题目 5
- 题型：判断题
- 题干：课前学情测试的结果可以帮助教师决定是否在基础版主文档之外补充提升任务包或拓展挑战包。
- 参考答案：正确
- 简短解析：前测用于学习起点诊断，不是正式成绩记录。
- 诊断点：分层导学理解
- 难度：基础

### 题目 6
- 题型：判断题
- 题干：如果本课涉及实训、编程、数据处理或设备操作，学生应在学习单中记录关键步骤、观察结果、错误信息或安全规范。
- 参考答案：正确
- 简短解析：过程记录有助于教师判断学生是否具备进入课堂任务的准备。
- 诊断点：安全规范、职业素养与过程记录
- 难度：基础

## 导学案复杂度建议

- 基础版主文档建议：面向全班优先使用，尤其适合多数学生对核心术语、基本步骤或任务目标还不熟悉时。
- 提升任务包建议：少数学生已完成基础任务后，可补充变式练习、错因分析或比较解释。
- 拓展挑战包建议：学有余力学生可尝试迁移应用、开放问题或综合设计。

## 教师提示

- 本前测不是正式考试，不做成绩记录。
- 教师应结合本班学生基础删改题目、答案和解析。
- 本系统不发布题目、不统计学生结果、不对接学习通 API。
"""
    return GeneratedLessonDraft("diagnostic_probe", f"{lesson_name}｜课前学情测试", content)


def _build_guide(lesson: Lesson, outline: KnowledgeOutline, draft_type: str) -> GeneratedLessonDraft:
    lesson_name = _lesson_name(lesson)
    excerpt = _outline_excerpt(outline)
    guide_settings = {
        "guide_low": (
            "基础版导学案",
            "全班主文档，步骤更细、示例更多、提示更充分，建议优先生成并用于课堂。",
            "先按示例完成一个基础任务，再仿照完成一个同类小任务。",
            "1. 先读示例；2. 再补全步骤；3. 最后检查结果。",
        ),
        "guide_mid": (
            "提升任务包",
            "可选任务包，适合已完成基础任务、具备一定独立完成能力的学生。",
            "先完成基础任务，再根据提示调整条件、步骤或表达方式。",
            "保留关键节点提示，其余过程由学生独立补全。",
        ),
        "guide_high": (
            "拓展挑战包",
            "可选挑战包，适合兴趣小组、竞赛苗子或学有余力学生。",
            "完成迁移任务、错误排查和方法说明。",
            "仅保留任务目标，鼓励学生比较方案、解释原因并复盘错误。",
        ),
    }
    label, audience, task_style, hint_style = guide_settings[draft_type]
    if draft_type == "guide_mid":
        return _build_improvement_task_pack(lesson, outline, label, audience, task_style, hint_style)
    if draft_type == "guide_high":
        return _build_extension_challenge_pack(lesson, outline, label, audience, task_style, hint_style)

    content = f"""# {lesson_name}｜{label}草稿

> 这是一份面向学生使用的导学案 / 学习单草稿，可用于填写、整理笔记和课堂练习。教师需审阅、修改与确认后再发给学生。

## 学习导航

- 本课主题：{lesson_name}
- 使用建议：{audience}
- 本课学习目标：理解本节课核心知识，能说出关键概念或操作步骤。
- 本课完成后能做什么：完成一个与本课内容一致的基础练习，并能检查自己的结果。
- 教师确认提示：请教师根据本班学情删改目标和任务要求。

## 学习情境

- 本课要解决什么问题：围绕“{lesson_name}”完成一个与课堂材料一致的学习任务。
- 为什么要学：本课知识可帮助我更规范地理解概念、完成操作、核验结果或记录过程。
- 最后要完成什么任务：{task_style}

## 知识要点

- 先读懂本节课的核心任务，再整理相关概念、步骤或规则。
- 从知识主干、PPT、实训指导书和补充材料中提取关键内容。
- 知识主干摘要：{excerpt or "暂无知识主干摘要，需教师补充。"}
- 我的补充笔记：______________________________

## 边学边填

1. 本节课的核心关键词是：__________、__________、__________。
2. 完成任务前，我需要先确认：任务要求、操作步骤和__________。
3. 容易出错的地方是：__________，我准备这样检查：__________。
4. 本节课需要注意的职业素养 / 安全规范 / 课程思政点是：__________。

## 例题引路

- 示例任务：根据教师提供的示例，完成一个最基础的同类任务。
- 思考：示例中第一步做了什么？为什么要这样做？
- 关键提示：如果材料中已有例题，请优先替换为教师确认后的例题。
- 标注：AI 草稿，教师需审核。

## 仿做练习

1. 仿照例题，轻微改变条件或任务要求，完成一个同类练习。
2. 任务要求：{task_style}
3. 完成后写下我的检查方法：______________________________

## 过程记录

- 我的操作步骤 / 解题步骤：______________________________
- 我的观察现象 / 运行结果 / 查询结果：______________________________
- 我遇到的错误信息或异常现象：______________________________
- 我的排查过程：______________________________
- 我遵守的安全规范 / 职业规范：______________________________
- 适用提示：本区可用于 Python、SQL、C、传感器、单片机、物联网项目、专业英语等课程的过程记录。

## 重点速记

- 最重要的 3 句话：
  1. 先看清任务，再选择方法。
  2. 操作或表达要有依据，不能凭感觉。
  3. 完成后必须检查结果或过程。
- 最容易错的 2 件事：
  1. 只记结论，不说明步骤。
  2. 忽略条件、边界或规范要求。
- 必须遵守的 1 条规范：按教师要求记录过程，遇到不确定内容及时标注并提问。

## 带回小练

1. 整理本节课 3 个关键词。
2. 完成 1 个同类小任务。
3. 写下 1 个仍需教师讲解的问题。
4. 标注：AI 草稿，教师需审核。

## 学习记录

- 今天我学会了：______________________________
- 我还不太明白：______________________________
- 我操作中遇到的问题：______________________________
- 我想问老师的问题：______________________________

## 学习自评

- [ ] 我能说出本课关键概念。
- [ ] 我能完成基础任务。
- [ ] 我能指出一个易错点。
- [ ] 我能遵守安全 / 规范要求。
- 我还需要老师帮助的是：______________________________
- 我的学习心得或问题反馈：______________________________

## AI 草稿声明

以上内容为导学案草稿，仅供教师审阅、修改、复制，不会自动发布给学生。教师应结合课程标准、学生基础和课堂实际确认后使用。
"""
    return GeneratedLessonDraft(draft_type, f"{lesson_name}｜{label}", content)


def _build_improvement_task_pack(
    lesson: Lesson,
    outline: KnowledgeOutline,
    label: str,
    audience: str,
    task_style: str,
    hint_style: str,
) -> GeneratedLessonDraft:
    """生成提升任务包：不是完整导学案，只作为基础版之后的可选任务。"""

    lesson_name = _lesson_name(lesson)
    excerpt = _outline_excerpt(outline, 360)
    content = f"""# {lesson_name}｜{label}草稿

> 本任务包不是完整导学案，建议在基础版导学案完成并经教师复核后按需使用。教师需审阅、修改与确认后再发给学生。

## 使用建议

- 定位：基础版主文档之后的可选补充任务。
- 适用对象：{audience}
- 使用方式：不建议每节课默认生成或全部使用，可结合课前学情测试和课堂表现选择 1—3 个任务。
- 层级关系：巩固提升任务包应建立在全班通用导学案基础上，围绕主导学案中的知识点、技能步骤、易错点和课堂任务进行适度提升，不直接设计成最高难度拓展挑战。
- 依据摘要：{excerpt or "暂无知识主干摘要，需教师补充。"}

## 适用对象

- 已完成基础任务的学生；
- 能说出本课关键概念，但需要进一步解释、比较或排错的学生；
- 适合小组讨论、课堂加练或教师点拨后的巩固。

## 任务 1：变式练习

- 学生要做什么：在基础任务上轻微改变条件、材料或步骤，完成一个同类任务。
- 思考提示：哪些条件变了？哪些步骤保持不变？
- 教师可调整点：可替换为本课材料中的真实任务或课堂练习。

## 任务 2：错因分析

- 学生要做什么：阅读一个可能出错的过程或结果，指出错误原因并写出修正方法。
- 思考提示：先找条件、步骤、结果核验或规范记录中的问题。
- 教师可调整点：建议使用本班学生常见错误，不写学生姓名。

## 任务 3：比较解释

- 学生要做什么：比较两种做法、表达或操作结果，说明哪一种更符合本课要求。
- 思考提示：从准确性、规范性、可检查性三个角度说明理由。
- 教师可调整点：根据课程类型替换为代码、查询、接线、实验记录或术语表达。

## 任务 4：小组讨论或排错

- 学生要做什么：小组讨论一个不确定结果，记录排查过程和最终判断。
- 思考提示：{hint_style}
- 教师可调整点：如课堂时间有限，可只保留口头讨论或记录关键步骤。

## 教师调整提示

- 本任务包仅作可选补充，不替代基础版导学案。
- 教师应结合学生基础、课堂时间和设备条件选择使用。
- 以上内容为本地结构化或 AI 草稿，需教师审核、修改与确认。
"""
    return GeneratedLessonDraft("guide_mid", f"{lesson_name}｜{label}", content)


def _build_extension_challenge_pack(
    lesson: Lesson,
    outline: KnowledgeOutline,
    label: str,
    audience: str,
    task_style: str,
    hint_style: str,
) -> GeneratedLessonDraft:
    """生成拓展挑战包：只提供少量挑战任务，不重复完整导学案。"""

    lesson_name = _lesson_name(lesson)
    excerpt = _outline_excerpt(outline, 360)
    content = f"""# {lesson_name}｜{label}草稿

> 本挑战包不是完整导学案，适合作为兴趣小组、竞赛苗子或学有余力学生的可选拓展。教师需审阅、修改与确认后再发给学生。

## 使用建议

- 定位：基础版主文档和必要提升任务之后的可选挑战。
- 适用对象：{audience}
- 使用方式：建议只选择 1—2 个挑战，不鼓励每节课默认使用，避免增加不必要负担。
- 层级关系：拓展探究任务包应建立在全班通用导学案和巩固提升任务包基础上，避免重复基础训练，难度应高于巩固提升任务包。
- 依据摘要：{excerpt or "暂无知识主干摘要，需教师补充。"}

## 适用对象

- 已较快完成基础任务的学生；
- 愿意尝试迁移、排错、方案设计或综合表达的学生；
- 可用于小组探究、课堂展示或课后自选挑战。

## 挑战 1：迁移应用

- 问题情境：把本课核心方法迁移到一个相近但条件略有变化的任务中。
- 完成要求：说明迁移前后哪些条件相同、哪些条件变化，以及如何检查结果。
- 可选提示：先写出基础任务的关键步骤，再逐项修改。
- 教师可调整点：可替换为本课程真实项目、设备、数据或语料。

## 挑战 2：开放问题

- 问题情境：围绕“{lesson_name}”提出一个需要解释、比较或选择方案的问题。
- 完成要求：给出自己的方案，并说明依据、风险或需要教师确认的地方。
- 可选提示：不确定的技术细节应标注“需教师确认”。
- 教师可调整点：根据课堂时间决定是否要求书面提交。

## 挑战 3：综合设计或竞赛启发

- 问题情境：设计一个小任务，把本课知识与过程记录、规范意识或结果核验结合起来。
- 完成要求：写出任务目标、关键步骤、检查方法和可能错误。
- 可选提示：{task_style}
- 教师可调整点：如本节课不适合综合设计，可改为排错或复盘任务。

## 教师调整提示

- 本挑战包只作可选拓展，不作为全班统一要求。
- 教师应避免让拓展任务替代基础任务。
- 以上内容为本地结构化或 AI 草稿，需教师审核、修改与确认。
"""
    return GeneratedLessonDraft("guide_high", f"{lesson_name}｜{label}", content)


def generate_lesson_drafts(lesson: Lesson, outline: KnowledgeOutline) -> list[GeneratedLessonDraft]:
    """基于最新知识主干生成四类教师草稿，不调用真实 AI。"""

    return [
        _build_diagnostic_probe(lesson, outline),
        _build_guide(lesson, outline, "guide_low"),
        _build_guide(lesson, outline, "guide_mid"),
        _build_guide(lesson, outline, "guide_high"),
    ]


def generate_basic_lesson_drafts(lesson: Lesson, outline: KnowledgeOutline) -> list[GeneratedLessonDraft]:
    """默认生成前测和基础版导学案，符合先诊断再分层的教学流程。"""

    return [_build_diagnostic_probe(lesson, outline), _build_guide(lesson, outline, "guide_low")]


def generate_single_lesson_draft(lesson: Lesson, outline: KnowledgeOutline, draft_type: str) -> GeneratedLessonDraft:
    """只生成指定 draft_type 的本地结构化草稿，不连带补齐其他草稿。"""

    if draft_type == "diagnostic_probe":
        return _build_diagnostic_probe(lesson, outline)
    if draft_type in {"guide_low", "guide_mid", "guide_high"}:
        return _build_guide(lesson, outline, draft_type)
    raise ValueError("不支持的导学草稿类型")


def generate_tiered_guide_draft(lesson: Lesson, outline: KnowledgeOutline, draft_type: str) -> GeneratedLessonDraft:
    """按需生成提升任务包或拓展挑战包草稿。"""

    if draft_type not in {"guide_mid", "guide_high"}:
        raise ValueError("仅支持生成提升任务包或拓展挑战包")
    return _build_guide(lesson, outline, draft_type)


def parse_diagnostic_probe_questions(content: str) -> list[DiagnosticQuestion]:
    """从课前学情测试 Markdown 中解析题目，供学习通模板导出使用。"""

    return [block.question for block in parse_diagnostic_probe_question_blocks(content)]


def parse_diagnostic_probe_question_blocks(content: str) -> list[DiagnosticQuestionBlock]:
    """解析课前学情测试题块，保留每题 Markdown 原文供 V2 页面轻量编辑。"""

    question_blocks: list[DiagnosticQuestionBlock] = []
    for heading, block, raw_markdown in _split_diagnostic_probe_blocks(content):
        question = _parse_diagnostic_question(heading, block)
        if question is None:
            continue
        question_blocks.append(
            DiagnosticQuestionBlock(
                index=len(question_blocks) + 1,
                question=question,
                raw_markdown=raw_markdown.strip(),
            )
        )
    return question_blocks


def _split_diagnostic_probe_blocks(content: str) -> list[tuple[str, str, str]]:
    """按题目标题切分前测 Markdown。"""

    question_pattern = re.compile(
        r"(?m)^[ \t]*(?:#{2,4}[ \t]*)?(?:\*\*)?[ \t]*(?:题目|第)[ \t]*(\d+)[ \t]*(?:题)?(?:[：:.\、-].*)?[ \t]*(?:\*\*)?[ \t]*$"
    )
    matches = list(question_pattern.finditer(content))
    blocks: list[tuple[str, str, str]] = []
    for index, matched in enumerate(matches):
        start = matched.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(content)
        raw_markdown = content[matched.start():end]
        blocks.append((matched.group(0), content[start:end], raw_markdown))

    # 兼容旧的严格格式，避免历史草稿无法导出。
    if not blocks:
        strict_pattern = re.compile(r"(?m)^###\s*题目\s*\d+\s*$")
        strict_matches = list(strict_pattern.finditer(content))
        for index, matched in enumerate(strict_matches):
            start = matched.end()
            end = strict_matches[index + 1].start() if index + 1 < len(strict_matches) else len(content)
            raw_markdown = content[matched.start():end]
            blocks.append((matched.group(0), content[start:end], raw_markdown))
    return blocks


def _parse_diagnostic_question(heading: str, block: str) -> DiagnosticQuestion | None:
    """从单题 Markdown 块中解析题型、题干、答案等字段。"""

    data: dict[str, str] = {}
    option_lines: list[str] = []
    for line in block.splitlines():
        stripped = line.strip().strip("*")
        matched = re.match(r"^(?:[-*]\s*)?([^：:]{1,12})[：:]\s*(.*)$", stripped)
        if matched:
            key = _normalize_question_field(matched.group(1).strip())
            data[key] = matched.group(2).strip()
            continue
        if re.match(r"^[A-H][.．、]\s*.+", stripped):
            option_lines.append(stripped)

    question_type = data.get("题型", "")
    prompt = data.get("题干", "") or _prompt_from_question_heading(heading)
    answer = data.get("参考答案", "")
    if not question_type or not prompt:
        return None
    options = _parse_options(data.get("选项", "") or "；".join(option_lines))
    return DiagnosticQuestion(
        question_type=question_type,
        prompt=prompt,
        answer=answer,
        explanation=data.get("简短解析", ""),
        diagnosis_point=data.get("诊断点", ""),
        difficulty=data.get("难度", ""),
        options=options,
    )


def _normalize_question_field(field_name: str) -> str:
    """归一化 AI 常见字段名，提升学习通导出兼容性。"""

    mapping = {
        "类型": "题型",
        "题目类型": "题型",
        "题干": "题干",
        "题目": "题干",
        "问题": "题干",
        "选项": "选项",
        "答案": "参考答案",
        "正确答案": "参考答案",
        "参考答案": "参考答案",
        "解析": "简短解析",
        "答案解析": "简短解析",
        "简短解析": "简短解析",
        "诊断点": "诊断点",
        "知识点": "诊断点",
        "能力点": "诊断点",
        "对应知识点": "诊断点",
        "难度": "难度",
    }
    return mapping.get(field_name, field_name)


def _prompt_from_question_heading(heading: str) -> str:
    """当 AI 把题干写在标题行时，从标题中提取题干。"""

    text = re.sub(r"^\s*#{2,4}\s*", "", heading).strip().strip("*")
    text = re.sub(r"^(?:题目|第)\s*\d+\s*(?:题)?\s*[：:.\、\s-]*", "", text).strip()
    return text


def _parse_options(options_text: str) -> list[str]:
    """解析 A-H 选项文本。"""

    if not options_text:
        return []
    parsed = re.findall(r"(?:^|[；;]\s*)([A-H])[.．、]\s*([^；;]+)", options_text)
    if parsed:
        return [text.strip() for _, text in parsed]
    return [option.strip() for option in re.split(r"[；;]", options_text) if option.strip()]


def _difficulty_label(difficulty: str) -> str:
    mapping = {"基础": "易", "中等": "中", "提高": "难"}
    return mapping.get(difficulty.strip(), difficulty.strip() or "易")


def _correct_answer(question: DiagnosticQuestion) -> str:
    if question.question_type == "判断题":
        return "A" if question.answer in {"正确", "对", "是", "A"} else "B"
    return question.answer


def _catalog_segment(value: str | None) -> str:
    """清理学习通题库目录片段，避免目录分隔符和换行破坏结构。"""

    text = re.sub(r"\s+", " ", (value or "").strip())
    text = text.replace("/", "-").replace("\\", "-")
    return text.strip(" -")


def _lesson_catalog_part(lesson: Lesson) -> str:
    """生成课次目录片段，优先使用课次编码和标题。"""

    code = _catalog_segment(lesson.lesson_code)
    title = _catalog_segment(lesson.title or lesson.content_summary)
    if code and title:
        return f"{code}-{title}"
    if code:
        return code
    if title:
        return title
    return f"lesson-{lesson.id}"


def build_chaoxing_catalog(lesson: Lesson) -> str:
    """生成学习通课程题库目录，不使用系统工具名作为一级目录。"""

    lesson_part = _lesson_catalog_part(lesson)
    course_title = _catalog_segment(lesson.course.title if lesson.course is not None else "")
    if course_title:
        return f"/{course_title}/{lesson_part}"
    return f"/{lesson_part}"


def build_chaoxing_rows(lesson: Lesson, draft: LessonDraft) -> list[list[str | int]]:
    """将 diagnostic_probe 草稿转换为学习通题库模板行。"""

    questions = parse_diagnostic_probe_questions(draft.content)
    catalog = build_chaoxing_catalog(lesson)
    tag_name = _lesson_catalog_part(lesson)
    tag = f"导学前测；学习起点诊断；{tag_name}"
    rows: list[list[str | int]] = []
    for question in questions:
        options = question.options
        if question.question_type == "判断题":
            options = ["正确", "错误"]
        elif question.question_type == "填空题" and not options:
            options = [answer.strip() for answer in re.split(r"[/；;、，,]", question.answer) if answer.strip()]
        answer = _correct_answer(question)
        row: list[str | int] = [
            catalog,
            question.question_type,
            question.prompt,
            "",
            "",
            answer,
            question.explanation,
            _difficulty_label(question.difficulty),
            question.diagnosis_point,
            tag,
            len(options),
        ]
        row.extend(options[:8])
        row.extend([""] * (8 - len(options[:8])))
        rows.append(row)
    return rows


def write_chaoxing_template_xlsx(lesson: Lesson, draft: LessonDraft, output_path: Path) -> None:
    """写出学习通题库导入模板 xlsx，不读取真实 .xls 模板样式。"""

    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "课程题库"
    worksheet.append(CHAOXING_HEADERS)
    for row in build_chaoxing_rows(lesson, draft):
        worksheet.append(row)
    workbook.save(output_path)
