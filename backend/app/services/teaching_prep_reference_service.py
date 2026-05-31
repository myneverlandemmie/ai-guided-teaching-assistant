"""备课参考建议生成服务。"""

from __future__ import annotations

from pathlib import Path

import httpx

from app.models.knowledge_outline import KnowledgeOutline
from app.models.lesson import Lesson, LessonMaterial
from app.services.ai.deepseek_client import DeepSeekProviderError, get_deepseek_config
from app.services.ai.lesson_draft_service import GeneratedLessonDraft
from app.services.ai.sanitizer import sanitize_text_for_outline

TEACHING_PREP_REFERENCE_DRAFT_TYPE = "teaching_prep_reference"
LOCAL_STRUCTURED_DRAFT = "local-structured-draft"
PROMPT_PATH = Path(__file__).resolve().parents[3] / "docs" / "prompts" / "teaching-prep-reference-suggestions-v0.1.md"
SYSTEM_MESSAGE = """
你是面向中职教师的备课参考建议助理。只提供温和、可选、可审阅的参考建议。
不得输出完整教案、比赛教案成稿、教师能力评价或一键备课结果。
所有建议必须由教师结合班级学情、教学条件、课程标准和课堂实际审阅、修改与取舍。
""".strip()


def load_teaching_prep_reference_prompt() -> str:
    """读取 Markdown Prompt 资产；缺失时返回最小安全边界文本。"""

    if PROMPT_PATH.exists():
        return PROMPT_PATH.read_text(encoding="utf-8")
    return """
# Teaching Prep Reference Suggestions v0.1 / 备课参考建议 Prompt v0.1

仅供教师备课参考，不替代教师判断；不输出完整教案；不评价教师能力。
输出结构：材料概况、已有亮点、可能遗漏、教学环节参考、导学案生成提示、课前学情测试提示、评价参考、教师确认声明。
""".strip()


def _lesson_name(lesson: Lesson) -> str:
    return f"{lesson.lesson_code}-{lesson.title}" if lesson.lesson_code else lesson.title


def _outline_text(outline: KnowledgeOutline | None, max_chars: int = 2400) -> str:
    if outline is None:
        return "暂无知识主干。"
    text = sanitize_text_for_outline((outline.edited_content or outline.ai_raw_output or "").strip())
    return text[:max_chars] if len(text) > max_chars else text


def _materials_text(materials: list[LessonMaterial], max_chars: int = 4200) -> str:
    parts: list[str] = []
    remaining = max_chars
    for material in materials:
        content = sanitize_text_for_outline((material.content or "").strip())
        if not content:
            continue
        header = f"## {material.title or '课次资料'}\n"
        budget = max(0, remaining - len(header))
        if budget <= 0:
            break
        clipped = content[:budget]
        parts.append(f"{header}{clipped}")
        remaining -= len(header) + len(clipped)
        if remaining <= 0:
            break
    if not parts:
        return "暂无课次资料，以下内容仅能基于课次基本信息和已有知识主干判断。"
    suffix = "\n\n提示：课次资料可能经过长度控制，教师需结合原始材料确认。" if remaining <= 0 else ""
    return "\n\n".join(parts) + suffix


def build_teaching_prep_reference_prompt(
    lesson: Lesson,
    materials: list[LessonMaterial],
    outline: KnowledgeOutline | None,
) -> str:
    """构造备课参考建议 prompt。"""

    prompt_asset = load_teaching_prep_reference_prompt()
    lesson_name = sanitize_text_for_outline(_lesson_name(lesson))
    summary = sanitize_text_for_outline(lesson.content_summary or "暂无")
    return f"""
{prompt_asset}

请基于以下课次信息、课次资料和知识主干，生成“备课参考建议”。

课次：{lesson_name}
教学内容摘要：{summary}

知识主干：
{_outline_text(outline)}

课次资料：
{_materials_text(materials)}

输出要求：
- 直接输出正文，不要使用“当然可以”“以下是”等对话式开头；
- 必须使用：一、材料概况；二、已有亮点；三、可能遗漏；四、教学环节参考；五、导学案生成提示；六、课前学情测试提示；七、评价参考；八、教师确认声明；
- 如果材料不足，写明“仅基于现有材料判断”；
- 语气必须温和、专业、可选择，可使用“可考虑”“如本课条件允许”“建议教师结合实际判断”“若已有安排，可忽略本建议”；
- 不输出完整教案，不替教师重写教学流程，不评价教师能力。
""".strip()


def generate_local_teaching_prep_reference(
    lesson: Lesson,
    materials: list[LessonMaterial],
    outline: KnowledgeOutline | None,
) -> GeneratedLessonDraft:
    """无 Key 或 AI 失败时生成本地结构化备课参考建议。"""

    lesson_name = _lesson_name(lesson)
    has_materials = bool(materials)
    outline_excerpt = _outline_text(outline, 520)
    first_material = sanitize_text_for_outline(materials[0].content[:260]) if materials else "暂无课次资料。"
    content = f"""# {lesson_name}｜备课参考建议

> 以下为基于现有材料的本地结构化参考建议，仅供教师审阅、修改与取舍，不替代教师教学判断。

## 一、材料概况

- 课次：{lesson_name}
- 教学内容摘要：{lesson.content_summary or '暂无'}
- 资料情况：{'已添加课次资料' if has_materials else '暂未添加课次资料'}。
- 知识主干摘要：{outline_excerpt or '暂无知识主干摘要。'}
- 说明：以下判断仅基于现有材料。

## 二、已有亮点

- 可看到本课已经围绕课次主题组织材料，具备形成学生导学案和课前学情测试的基础。
- 可考虑继续保留材料中的任务、步骤、练习、安全规范或职业素养提示。
- 当前资料摘录：{first_material}

## 三、可能遗漏

- 可考虑补充更明确的学生起点信息，例如学生已掌握哪些前置概念或基础操作。
- 如本课条件允许，可进一步明确课前、课中、课后任务之间的衔接关系。
- 若材料中已有评价安排，可忽略本项；否则可考虑补充知识、技能、素养三个维度的观察点。

## 四、教学环节参考

- 课前：可考虑用 5—8 道基础题判断学习起点，不作为正式考试成绩。
- 课中：建议教师结合实际判断是否需要增加学生记录区、操作步骤记录或错误排查记录。
- 课后：可考虑安排 1—3 个小练习，帮助学生复盘关键概念、技能步骤和易错点。

## 五、导学案生成提示

- 可进入学生导学案的内容：关键概念、技能步骤、易错提醒、安全规范、职业素养、学习记录、课后小练。
- 建议保留学生填写空间，例如“我学会了”“我还不明白”“我遇到的问题”。
- 若已有学习单或任务单，可优先转化为学生可填写、可记录、可复盘的结构。

## 六、课前学情测试提示

- 可测诊断点：基础概念、前置知识、任务背景理解、操作步骤、易错判断、安全规范、职业素养。
- 建议题型：单选题、判断题、填空题或简答题。
- 前测定位：用于判断学习起点，不作为正式考试成绩。

## 七、评价参考

- 可考虑是否已有学生自评、小组互评、教师评价或过程表现记录。
- 评价参考只能作为可选提醒，不作为教师能力评价。
- 若已有安排，可忽略或调整本建议。

## 八、教师确认声明

本建议仅作为备课参考，不替代教师判断。教师应结合班级学情、教学条件、课程标准和实际课堂安排进行取舍。若材料中已有相应安排，可忽略或调整本建议。
"""
    return GeneratedLessonDraft(
        TEACHING_PREP_REFERENCE_DRAFT_TYPE,
        f"{lesson_name}｜备课参考建议",
        content,
        generated_by=LOCAL_STRUCTURED_DRAFT,
    )


def _is_usable_reference_content(content: str) -> bool:
    required = ["材料概况", "已有亮点", "可能遗漏", "教学环节参考", "导学案生成提示", "课前学情测试提示", "评价参考", "教师确认声明"]
    return bool(content and len(content.strip()) >= 120 and all(section in content for section in required))


def _call_deepseek_teaching_prep_reference(
    lesson: Lesson,
    materials: list[LessonMaterial],
    outline: KnowledgeOutline | None,
    api_key: str,
    selected_model: str | None,
) -> tuple[str, str]:
    """调用 DeepSeek 生成备课参考建议；测试中可 monkeypatch 避免真实网络。"""

    config = get_deepseek_config(selected_model)
    payload = {
        "model": config.model,
        "messages": [
            {"role": "system", "content": SYSTEM_MESSAGE},
            {"role": "user", "content": build_teaching_prep_reference_prompt(lesson, materials, outline)},
        ],
        "temperature": 0.25,
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    try:
        with httpx.Client(timeout=config.timeout_seconds) as client:
            response = client.post(f"{config.base_url}/chat/completions", json=payload, headers=headers)
    except httpx.TimeoutException:
        raise DeepSeekProviderError("DeepSeek 响应较慢，已回退为本地结构化草稿。") from None
    except httpx.HTTPError:
        raise DeepSeekProviderError("AI 服务请求失败，已回退为本地结构化草稿。") from None
    if response.status_code >= 400:
        raise DeepSeekProviderError("AI 服务请求失败，已回退为本地结构化草稿。", response.status_code)
    try:
        data = response.json()
        content = data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError, ValueError):
        raise DeepSeekProviderError("AI 返回格式异常，已回退为本地结构化草稿。") from None
    if not content:
        raise DeepSeekProviderError("AI 返回内容为空，已回退为本地结构化草稿。")
    return sanitize_text_for_outline(content), config.model


def generate_teaching_prep_reference(
    lesson: Lesson,
    materials: list[LessonMaterial],
    outline: KnowledgeOutline | None,
    api_key: str | None,
    selected_model: str | None,
) -> tuple[GeneratedLessonDraft, bool]:
    """生成备课参考建议；无 Key 或失败时回退本地结构化草稿。"""

    local_draft = generate_local_teaching_prep_reference(lesson, materials, outline)
    if not api_key:
        return local_draft, True
    try:
        content, model_name = _call_deepseek_teaching_prep_reference(lesson, materials, outline, api_key, selected_model)
    except DeepSeekProviderError:
        return local_draft, True
    if not _is_usable_reference_content(content):
        return local_draft, True
    return GeneratedLessonDraft(
        TEACHING_PREP_REFERENCE_DRAFT_TYPE,
        local_draft.title,
        content,
        generated_by=model_name,
    ), False
