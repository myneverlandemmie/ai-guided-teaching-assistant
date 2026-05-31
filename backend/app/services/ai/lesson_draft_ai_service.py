"""课前学情测试与学生导学案真实 AI 生成封装。"""

from __future__ import annotations

from dataclasses import replace

import httpx

from app.models.knowledge_outline import KnowledgeOutline
from app.models.lesson import Lesson
from app.services.ai.deepseek_client import DeepSeekProviderError, get_deepseek_config
from app.services.ai.lesson_draft_prompt import LESSON_DRAFT_SYSTEM_MESSAGE, build_lesson_draft_prompt
from app.services.ai.lesson_draft_service import (
    GeneratedLessonDraft,
    generate_basic_lesson_drafts,
    generate_single_lesson_draft,
    generate_tiered_guide_draft,
)
from app.services.ai.sanitizer import (
    API_KEY_PATTERN,
    CLASS_NAME_PATTERN,
    ID_CARD_PATTERN,
    PASSWORD_INLINE_PATTERN,
    PHONE_PATTERN,
    TEACHER_NAME_PATTERN,
    TOKEN_PATTERN,
    sanitize_text_for_outline,
)

LOCAL_STRUCTURED_DRAFT = "local-structured-draft"


def _with_generated_by(draft: GeneratedLessonDraft, generated_by: str) -> GeneratedLessonDraft:
    """复制草稿并替换生成来源。"""

    return replace(draft, generated_by=generated_by)


def _fallback_basic_drafts(lesson: Lesson, outline: KnowledgeOutline) -> list[GeneratedLessonDraft]:
    """生成本地结构化前测和基础版导学案。"""

    return [_with_generated_by(draft, LOCAL_STRUCTURED_DRAFT) for draft in generate_basic_lesson_drafts(lesson, outline)]


def _fallback_tiered_draft(lesson: Lesson, outline: KnowledgeOutline, draft_type: str) -> GeneratedLessonDraft:
    """生成本地结构化提升任务包或拓展挑战包。"""

    return _with_generated_by(generate_tiered_guide_draft(lesson, outline, draft_type), LOCAL_STRUCTURED_DRAFT)


def _fallback_single_draft(lesson: Lesson, outline: KnowledgeOutline, draft_type: str) -> GeneratedLessonDraft:
    """只生成当前目标 draft_type 的本地结构化草稿。"""

    return _with_generated_by(generate_single_lesson_draft(lesson, outline, draft_type), LOCAL_STRUCTURED_DRAFT)


def _is_usable_draft_content(draft_type: str, content: str) -> bool:
    """做轻量格式检查，避免空响应或明显不可用内容覆盖本地草稿。"""

    if not content or len(content.strip()) < 80:
        return False
    if draft_type == "diagnostic_probe":
        return "### 题目" in content and "参考答案" in content and "诊断点" in content
    if draft_type == "guide_mid":
        required_headings = ["提升任务包", "使用建议", "适用对象", "任务 1", "教师调整提示"]
        return all(heading in content for heading in required_headings)
    if draft_type == "guide_high":
        required_headings = ["拓展挑战包", "使用建议", "适用对象", "挑战 1", "教师调整提示"]
        return all(heading in content for heading in required_headings)
    required_headings = ["学习导航", "学习情境", "知识要点", "边学边填", "过程记录", "学习自评"]
    return all(heading in content for heading in required_headings)


def _sanitize_generated_draft_content(draft_type: str, content: str) -> str:
    """清洗 AI 输出，避免课前题目中的通用教学字段被行政信息规则误伤。"""

    if draft_type != "diagnostic_probe":
        return sanitize_text_for_outline(content)

    sanitized_lines: list[str] = []
    for raw_line in (content or "").splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            sanitized_lines.append("")
            continue
        line = API_KEY_PATTERN.sub("[疑似密钥已移除]", line)
        line = TOKEN_PATTERN.sub("[疑似 Token 已移除]", line)
        line = PASSWORD_INLINE_PATTERN.sub("[密码信息已移除]", line)
        line = PHONE_PATTERN.sub("[已过滤手机号]", line)
        line = ID_CARD_PATTERN.sub("[已过滤身份证号]", line)
        line = CLASS_NAME_PATTERN.sub("某班级", line)
        line = TEACHER_NAME_PATTERN.sub("某教师", line)
        line = line.replace("[已过滤行政信息]", "示例字段")
        sanitized_lines.append(line)
    return "\n".join(sanitized_lines).strip()


def _call_deepseek_lesson_draft(
    lesson: Lesson,
    outline: KnowledgeOutline,
    draft_type: str,
    api_key: str,
    selected_model: str | None,
    related_drafts: dict[str, str] | None = None,
) -> tuple[str, str]:
    """调用 DeepSeek 生成单份导学草稿。

    测试中可 monkeypatch 本函数，避免真实网络请求。
    """

    config = get_deepseek_config(selected_model)
    prompt = build_lesson_draft_prompt(lesson, outline, draft_type, related_drafts=related_drafts)
    payload = {
        "model": config.model,
        "messages": [
            {"role": "system", "content": LESSON_DRAFT_SYSTEM_MESSAGE},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    try:
        with httpx.Client(timeout=config.timeout_seconds) as client:
            response = client.post(f"{config.base_url}/chat/completions", json=payload, headers=headers)
    except httpx.TimeoutException:
        raise DeepSeekProviderError("DeepSeek 请求超时，请稍后重试或减少材料长度。") from None
    except httpx.HTTPError:
        raise DeepSeekProviderError("AI 服务请求失败，请稍后重试或检查配置。") from None

    if response.status_code >= 400:
        raise DeepSeekProviderError("AI 服务请求失败，已回退为本地结构化草稿。", response.status_code)
    try:
        data = response.json()
        content = data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError, ValueError):
        raise DeepSeekProviderError("DeepSeek 返回格式异常，已回退为本地结构化草稿。") from None
    if not content:
        raise DeepSeekProviderError("DeepSeek 返回内容为空，已回退为本地结构化草稿。")
    return _sanitize_generated_draft_content(draft_type, content), config.model


def generate_basic_lesson_drafts_with_ai(
    lesson: Lesson,
    outline: KnowledgeOutline,
    api_key: str | None,
    selected_model: str | None,
) -> tuple[list[GeneratedLessonDraft], bool]:
    """生成课前学情测试和基础版导学案，有 Key 时优先调用 DeepSeek。

    Returns:
        (草稿列表, 是否发生 fallback)。
    """

    if not api_key:
        return _fallback_basic_drafts(lesson, outline), True

    local_drafts = _fallback_basic_drafts(lesson, outline)
    generated: list[GeneratedLessonDraft] = []
    try:
        for local_draft in local_drafts:
            content, model_name = _call_deepseek_lesson_draft(
                lesson,
                outline,
                local_draft.draft_type,
                api_key,
                selected_model,
            )
            if not _is_usable_draft_content(local_draft.draft_type, content):
                return local_drafts, True
            generated.append(
                GeneratedLessonDraft(local_draft.draft_type, local_draft.title, content, generated_by=model_name)
            )
    except DeepSeekProviderError:
        return local_drafts, True
    return generated, False


def generate_tiered_guide_draft_with_ai(
    lesson: Lesson,
    outline: KnowledgeOutline,
    draft_type: str,
    api_key: str | None,
    selected_model: str | None,
) -> tuple[GeneratedLessonDraft, bool]:
    """生成提升任务包或拓展挑战包，有 Key 时优先调用 DeepSeek。"""

    local_draft = _fallback_tiered_draft(lesson, outline, draft_type)
    if not api_key:
        return local_draft, True
    try:
        content, model_name = _call_deepseek_lesson_draft(lesson, outline, draft_type, api_key, selected_model)
    except DeepSeekProviderError:
        return local_draft, True
    if not _is_usable_draft_content(draft_type, content):
        return local_draft, True
    return GeneratedLessonDraft(draft_type, local_draft.title, content, generated_by=model_name), False


def generate_single_lesson_draft_with_ai(
    lesson: Lesson,
    outline: KnowledgeOutline,
    draft_type: str,
    api_key: str | None,
    selected_model: str | None,
    related_drafts: dict[str, str] | None = None,
) -> tuple[GeneratedLessonDraft, bool]:
    """只生成指定 draft_type；AI 失败时也只 fallback 当前草稿。"""

    local_draft = _fallback_single_draft(lesson, outline, draft_type)
    if not api_key:
        return local_draft, True
    try:
        if related_drafts:
            content, model_name = _call_deepseek_lesson_draft(
                lesson,
                outline,
                draft_type,
                api_key,
                selected_model,
                related_drafts=related_drafts,
            )
        else:
            content, model_name = _call_deepseek_lesson_draft(lesson, outline, draft_type, api_key, selected_model)
    except DeepSeekProviderError:
        return local_draft, True
    if not _is_usable_draft_content(draft_type, content):
        return local_draft, True
    return GeneratedLessonDraft(draft_type, local_draft.title, content, generated_by=model_name), False
