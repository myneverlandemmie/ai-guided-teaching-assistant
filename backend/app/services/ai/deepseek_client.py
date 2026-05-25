"""DeepSeek OpenAI-compatible 客户端。"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

import httpx

from app.models.lesson import Lesson, LessonMaterial
from app.services.ai.sanitizer import sanitize_lesson_for_outline, sanitize_materials_for_outline, sanitize_text_for_outline

DEFAULT_DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEFAULT_DEEPSEEK_MODEL = "deepseek-v4-pro"
DEFAULT_TIMEOUT_SECONDS = 60.0
DEFAULT_PROMPT_MATERIAL_MAX_CHARS = 12_000
ALLOWED_DEEPSEEK_MODELS = {"deepseek-v4-pro", "deepseek-v4-flash"}
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


class DeepSeekProviderError(RuntimeError):
    """DeepSeek 调用失败时返回给页面的安全错误。"""

    def __init__(self, user_message: str, status_code: int | None = None) -> None:
        super().__init__(user_message)
        self.user_message = user_message
        self.status_code = status_code


@dataclass(frozen=True)
class DeepSeekConfig:
    """DeepSeek 调用配置。"""

    base_url: str
    model: str
    timeout_seconds: float
    prompt_material_max_chars: int


def _parse_positive_float_env(name: str, default: float) -> float:
    """安全解析正浮点数环境变量，非法值回退默认值。"""

    try:
        value = float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


def _parse_positive_int_env(name: str, default: int) -> int:
    """安全解析正整数环境变量，非法值回退默认值。"""

    try:
        value = int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


def get_deepseek_config() -> DeepSeekConfig:
    """从环境变量读取 DeepSeek 配置。"""

    model = os.getenv("DEEPSEEK_MODEL", DEFAULT_DEEPSEEK_MODEL).strip() or DEFAULT_DEEPSEEK_MODEL
    if model not in ALLOWED_DEEPSEEK_MODELS:
        raise DeepSeekProviderError("DeepSeek 模型配置无效，请使用 deepseek-v4-pro 或 deepseek-v4-flash。")

    return DeepSeekConfig(
        base_url=os.getenv("DEEPSEEK_BASE_URL", DEFAULT_DEEPSEEK_BASE_URL).rstrip("/"),
        model=model,
        timeout_seconds=_parse_positive_float_env("AI_REQUEST_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS),
        prompt_material_max_chars=_parse_positive_int_env(
            "AI_PROMPT_MATERIAL_MAX_CHARS",
            DEFAULT_PROMPT_MATERIAL_MAX_CHARS,
        ),
    )


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
    """渲染知识主干 prompt。"""

    return f"""
你是一名中职数据库 / 程序设计课程的教学助手。请基于下面课次信息和教学材料，为教师生成“知识主干初稿”。

重要约束：
- 输出中文，面向教师可读。
- 不要输出学校、教研组、任课教师、授课班级、授课地点、授课日期、学号、姓名、手机号、身份证号等行政或个人信息。
- 内容聚焦教学目标、重点难点、核心知识点、学生易错点、课堂任务和小测方向。
- AI 内容仅为初稿，必须由教师复核、编辑后使用。
- 如果材料包含 SQL / Python 关键词，请保留与本课次教学相关的关键词和示例方向。

课次编码：{lesson_code}
课次标题：{lesson_title}
教学内容摘要：{content_summary}

教学材料（已做基础过滤）：
{material_text}

请按以下结构输出：
1. 本节课定位
2. 学习目标
3. 核心知识点
4. 知识结构
5. 学生易错点
6. 课堂任务建议
7. 小测题方向
8. 教师使用提示
""".strip()


def build_knowledge_outline_prompt(lesson: Lesson, materials: list[LessonMaterial], config: DeepSeekConfig | None = None) -> str:
    """构造知识主干生成 prompt，并在输入阶段过滤行政和个人信息。"""

    active_config = config or get_deepseek_config()
    sanitized_lesson = sanitize_lesson_for_outline(lesson)
    sanitized_materials = sanitize_materials_for_outline(materials)
    sanitized_material = "\n".join(material.content for material in sanitized_materials if material.content).strip()

    lesson_code = sanitized_lesson.lesson_code or "未设置"
    lesson_title = sanitized_lesson.title or "未设置"
    content_summary = sanitized_lesson.content_summary or "暂无"
    empty_hint = "当前课次未添加教学材料，请仅基于课次标题和教学内容摘要生成基础知识主干。"

    # 先计算无材料时的固定开销，再把材料控制在剩余空间内，确保最终 prompt 有明确上限。
    base_prompt = _render_prompt(lesson_code, lesson_title, content_summary, "")
    material_limit = max(0, active_config.prompt_material_max_chars - len(base_prompt) - 16)
    material_text = build_limited_material_context(sanitized_material, material_limit) if sanitized_material else empty_hint
    prompt = _render_prompt(lesson_code, lesson_title, content_summary, material_text)
    if len(prompt) > active_config.prompt_material_max_chars:
        overflow = len(prompt) - active_config.prompt_material_max_chars
        trim_to = max(0, len(material_text) - overflow - 8)
        prompt = _render_prompt(lesson_code, lesson_title, content_summary, material_text[:trim_to])
    return sanitize_text_for_outline(prompt)


def _safe_error_message(status_code: int) -> str:
    """将 DeepSeek HTTP 状态转换为教师可理解提示。"""

    if status_code == 401:
        return "DeepSeek API Key 无效或认证失败，请检查 Key。"
    if status_code == 402:
        return "DeepSeek 账户余额不足，请检查 DeepSeek 账户余额。"
    if status_code == 429:
        return "DeepSeek 请求过快或触发限流，请稍后重试。"
    if 500 <= status_code <= 599:
        return "DeepSeek 服务繁忙，请稍后重试。"
    return "AI 服务请求失败，请稍后重试或检查配置。"


def generate_deepseek_knowledge_outline(
    lesson: Lesson,
    materials: list[LessonMaterial],
    api_key: str,
    config: DeepSeekConfig | None = None,
) -> tuple[str, str]:
    """调用 DeepSeek 生成知识主干。"""

    active_config = config or get_deepseek_config()
    prompt = build_knowledge_outline_prompt(lesson, materials, active_config)
    payload = {
        "model": active_config.model,
        "messages": [
            {"role": "system", "content": "你是严谨的中职课程教学设计助手。"},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    try:
        with httpx.Client(timeout=active_config.timeout_seconds) as client:
            response = client.post(f"{active_config.base_url}/chat/completions", json=payload, headers=headers)
    except httpx.TimeoutException:
        raise DeepSeekProviderError("DeepSeek 请求超时，请稍后重试或减少材料长度。") from None
    except httpx.HTTPError:
        raise DeepSeekProviderError("AI 服务请求失败，请稍后重试或检查配置。") from None

    if response.status_code >= 400:
        raise DeepSeekProviderError(_safe_error_message(response.status_code), response.status_code)

    try:
        data = response.json()
        content = data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError, ValueError):
        raise DeepSeekProviderError("DeepSeek 返回格式异常，请稍后重试。") from None

    if not content:
        raise DeepSeekProviderError("DeepSeek 返回内容为空，请稍后重试。")
    return content, active_config.model
