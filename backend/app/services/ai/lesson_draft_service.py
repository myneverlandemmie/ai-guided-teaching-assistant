"""导学案前测与三阶导学案草稿生成服务。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from openpyxl import Workbook

from app.models.knowledge_outline import KnowledgeOutline
from app.models.lesson import Lesson
from app.models.lesson_draft import LessonDraft

DRAFT_TYPE_LABELS = {
    "diagnostic_probe": "导学案前测",
    "guide_low": "低阶导学案",
    "guide_mid": "中阶导学案",
    "guide_high": "高阶导学案",
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
    """导学案前测题目结构。"""

    question_type: str
    prompt: str
    answer: str
    explanation: str
    diagnosis_point: str
    difficulty: str
    options: list[str]


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
    content = f"""# {lesson_name}｜导学案前测草稿

> 本前测用于判断学习起点，不作为正式考试成绩。教师可复制到学习通或其他平台后自行筛选、修改和发布。

## 前测依据

- 来源知识主干：{outline.id}
- 核心材料摘要：{excerpt or "暂无知识主干摘要，需教师补充。"}

## 前测题目

### 题目 1
- 题型：单选题
- 题干：本节课最核心的学习任务更接近以下哪一项？
- 选项：A. 记住全部材料原文；B. 识别核心概念并完成基础任务；C. 跳过基础直接做拓展；D. 只关注课堂纪律
- 参考答案：B
- 简短解析：前测关注学习起点，应先判断学生是否理解核心概念和基础任务。
- 诊断点：核心任务识别
- 难度：基础

### 题目 2
- 题型：判断题
- 题干：如果学生对本节课的关键术语还不熟悉，导学案应提供更细步骤和更多示例。
- 参考答案：正确
- 简短解析：基础薄弱学生需要低阶导学案支持。
- 诊断点：学习支持需求
- 难度：基础

### 题目 3
- 题型：填空题
- 题干：本节课学习后，学生至少应能完成一个与核心知识相关的______任务。
- 参考答案：基础练习 / 基础操作 / 基础应用
- 简短解析：前测用于判断学生是否具备进入课堂任务的准备。
- 诊断点：基础应用意识
- 难度：基础

### 题目 4
- 题型：单选题
- 题干：遇到不确定的技术细节时，更合适的处理方式是？
- 选项：A. 直接猜测；B. 写成确定结论；C. 标注需教师确认；D. 忽略不处理
- 参考答案：C
- 简短解析：教师复核是 AI 草稿进入课堂前的必要环节。
- 诊断点：技术准确性意识
- 难度：中等

### 题目 5
- 题型：判断题
- 题干：导学案前测的结果可以帮助教师决定低 / 中 / 高阶导学案的使用复杂度。
- 参考答案：正确
- 简短解析：前测用于学习起点诊断，不是正式成绩记录。
- 诊断点：分层导学理解
- 难度：基础

## 导学案复杂度建议

- 低复杂度：多数学生对核心术语、基本步骤或任务目标不熟悉。
- 中复杂度：多数学生能理解基本概念，但需要关键提示完成任务。
- 高复杂度：多数学生能独立完成基础任务，可增加迁移、排错和反思。

## 教师提示

- 本前测不是正式考试，不做成绩记录。
- 教师应结合本班学生基础删改题目、答案和解析。
- 本系统不发布题目、不统计学生结果、不对接学习通 API。
"""
    return GeneratedLessonDraft("diagnostic_probe", f"{lesson_name}｜导学案前测", content)


def _build_guide(lesson: Lesson, outline: KnowledgeOutline, draft_type: str) -> GeneratedLessonDraft:
    lesson_name = _lesson_name(lesson)
    excerpt = _outline_excerpt(outline)
    guide_settings = {
        "guide_low": (
            "低阶导学案",
            "默认基础版本，步骤更细、示例更多、提示更充分，适合基础薄弱学生。",
            "先按示例完成一个基础任务，再仿照完成一个同类小任务。",
            "1. 先读示例；2. 再补全步骤；3. 最后检查结果。",
        ),
        "guide_mid": (
            "中阶导学案",
            "可选分层版本，适合基础一般、有一定独立完成能力的学生。",
            "先完成基础任务，再根据提示调整条件、步骤或表达方式。",
            "保留关键节点提示，其余过程由学生独立补全。",
        ),
        "guide_high": (
            "高阶导学案",
            "可选分层版本，适合掌握较快、可进行迁移和排错的学生。",
            "完成迁移任务、错误排查和方法说明。",
            "仅保留任务目标，鼓励学生比较方案、解释原因并复盘错误。",
        ),
    }
    label, audience, task_style, hint_style = guide_settings[draft_type]
    content = f"""# {lesson_name}｜{label}草稿

> 这是一份面向学生使用的导学案 / 学习单草稿，可用于填写、整理笔记和课堂练习。教师需审阅、修改与确认后再发给学生。

## 学习导航

- 本课主题：{lesson_name}
- 使用建议：{audience}
- 本课要学会什么：理解本节课核心知识，能说出关键概念或操作步骤。
- 本课要完成什么任务：完成一个与本课内容一致的基础练习，并能检查自己的结果。

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

## AI 草稿声明

以上内容为导学案草稿，仅供教师审阅、修改、复制，不会自动发布给学生。教师应结合课程标准、学生基础和课堂实际确认后使用。
"""
    return GeneratedLessonDraft(draft_type, f"{lesson_name}｜{label}", content)


def generate_lesson_drafts(lesson: Lesson, outline: KnowledgeOutline) -> list[GeneratedLessonDraft]:
    """基于最新知识主干生成四类教师草稿，不调用真实 AI。"""

    return [
        _build_diagnostic_probe(lesson, outline),
        _build_guide(lesson, outline, "guide_low"),
        _build_guide(lesson, outline, "guide_mid"),
        _build_guide(lesson, outline, "guide_high"),
    ]


def generate_basic_lesson_drafts(lesson: Lesson, outline: KnowledgeOutline) -> list[GeneratedLessonDraft]:
    """默认生成前测和低阶导学案，符合先诊断再分层的教学流程。"""

    return [_build_diagnostic_probe(lesson, outline), _build_guide(lesson, outline, "guide_low")]


def generate_tiered_guide_draft(lesson: Lesson, outline: KnowledgeOutline, draft_type: str) -> GeneratedLessonDraft:
    """按需生成中阶或高阶导学案草稿。"""

    if draft_type not in {"guide_mid", "guide_high"}:
        raise ValueError("仅支持生成中阶或高阶导学案")
    return _build_guide(lesson, outline, draft_type)


def parse_diagnostic_probe_questions(content: str) -> list[DiagnosticQuestion]:
    """从导学案前测 Markdown 中解析题目，供学习通模板导出使用。"""

    questions: list[DiagnosticQuestion] = []
    blocks = re.split(r"(?m)^###\s*题目\s*\d+\s*$", content)
    for block in blocks[1:]:
        data: dict[str, str] = {}
        for line in block.splitlines():
            matched = re.match(r"^-\s*([^：:]+)[：:]\s*(.*)$", line.strip())
            if matched:
                data[matched.group(1).strip()] = matched.group(2).strip()
        question_type = data.get("题型", "")
        prompt = data.get("题干", "")
        answer = data.get("参考答案", "")
        if not question_type or not prompt:
            continue
        options = _parse_options(data.get("选项", ""))
        questions.append(
            DiagnosticQuestion(
                question_type=question_type,
                prompt=prompt,
                answer=answer,
                explanation=data.get("简短解析", ""),
                diagnosis_point=data.get("诊断点", ""),
                difficulty=data.get("难度", ""),
                options=options,
            )
        )
    return questions


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
