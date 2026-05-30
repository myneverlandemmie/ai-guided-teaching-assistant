"""DeepSeek OpenAI-compatible 客户端。"""

from __future__ import annotations

import os
from dataclasses import dataclass

import httpx

from app.models.lesson import Lesson, LessonMaterial
from app.services.ai.knowledge_outline_prompt import (
    KNOWLEDGE_OUTLINE_SYSTEM_MESSAGE,
    build_knowledge_outline_prompt as build_prompt_from_template,
)

DEFAULT_DEEPSEEK_BASE_URL = "https://api.deepseek.com"
FALLBACK_DEEPSEEK_MODELS = ("deepseek-v4-flash", "deepseek-v4-pro")
FORBIDDEN_DEEPSEEK_MODELS = {"deepseek-chat", "deepseek-reasoner"}
DEFAULT_TIMEOUT_SECONDS = 180.0
DEFAULT_FLASH_TIMEOUT_SECONDS = 180.0
DEFAULT_PRO_TIMEOUT_SECONDS = 300.0
DEFAULT_PROMPT_MATERIAL_MAX_CHARS = 12_000


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


def normalize_model_name(model_name: str | None) -> str:
    """规范化模型名称。"""

    return (model_name or "").strip()


def get_allowed_deepseek_models() -> list[str]:
    """读取允许教师选择的 DeepSeek 模型列表。"""

    raw_models = os.getenv("DEEPSEEK_ALLOWED_MODELS", ",".join(FALLBACK_DEEPSEEK_MODELS))
    allowed_fallbacks = set(FALLBACK_DEEPSEEK_MODELS)
    models: list[str] = []
    seen: set[str] = set()
    for raw_model in raw_models.split(","):
        model = normalize_model_name(raw_model)
        if not model or model in seen:
            continue
        # V0.2 只允许 DeepSeek V4 模型；废弃模型和未知模型均不进入页面选项。
        if model in FORBIDDEN_DEEPSEEK_MODELS or model not in allowed_fallbacks:
            continue
        models.append(model)
        seen.add(model)
    return models or list(FALLBACK_DEEPSEEK_MODELS)


def is_allowed_deepseek_model(model_name: str | None) -> bool:
    """判断模型是否在当前允许列表中。"""

    return normalize_model_name(model_name) in get_allowed_deepseek_models()


def get_default_deepseek_model() -> str:
    """读取默认 DeepSeek 模型；非法时回退到 allowed models 第一项。"""

    allowed_models = get_allowed_deepseek_models()
    configured_default = normalize_model_name(os.getenv("DEEPSEEK_DEFAULT_MODEL"))
    if configured_default in allowed_models:
        return configured_default
    return allowed_models[0]


def get_deepseek_timeout_seconds(model_name: str | None = None) -> float:
    """按模型读取 DeepSeek 等待时间，避免长材料生成过早超时。"""

    model = normalize_model_name(model_name) or get_default_deepseek_model()
    legacy_timeout = os.getenv("AI_REQUEST_TIMEOUT_SECONDS")
    global_default = _parse_positive_float_env(
        "DEEPSEEK_TIMEOUT_SECONDS",
        _parse_positive_float_env("AI_REQUEST_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS),
    )
    if model == "deepseek-v4-pro":
        return _parse_positive_float_env(
            "DEEPSEEK_PRO_TIMEOUT_SECONDS",
            _parse_positive_float_env("AI_REQUEST_TIMEOUT_SECONDS", DEFAULT_PRO_TIMEOUT_SECONDS)
            if legacy_timeout is not None and os.getenv("DEEPSEEK_TIMEOUT_SECONDS") is None
            else global_default if os.getenv("DEEPSEEK_TIMEOUT_SECONDS") is not None else DEFAULT_PRO_TIMEOUT_SECONDS,
        )
    if model == "deepseek-v4-flash":
        return _parse_positive_float_env(
            "DEEPSEEK_FLASH_TIMEOUT_SECONDS",
            _parse_positive_float_env("AI_REQUEST_TIMEOUT_SECONDS", DEFAULT_FLASH_TIMEOUT_SECONDS)
            if legacy_timeout is not None and os.getenv("DEEPSEEK_TIMEOUT_SECONDS") is None
            else global_default if os.getenv("DEEPSEEK_TIMEOUT_SECONDS") is not None else DEFAULT_FLASH_TIMEOUT_SECONDS,
        )
    return global_default


def get_deepseek_config(model_name: str | None = None) -> DeepSeekConfig:
    """从环境变量读取 DeepSeek 配置。"""

    model = normalize_model_name(model_name) or get_default_deepseek_model()
    if not is_allowed_deepseek_model(model):
        raise DeepSeekProviderError("DeepSeek 模型配置无效，请使用当前允许列表中的 V4 模型。")
    return DeepSeekConfig(
        base_url=os.getenv("DEEPSEEK_BASE_URL", DEFAULT_DEEPSEEK_BASE_URL).rstrip("/"),
        model=model,
        timeout_seconds=get_deepseek_timeout_seconds(model),
        prompt_material_max_chars=_parse_positive_int_env(
            "AI_PROMPT_MATERIAL_MAX_CHARS",
            DEFAULT_PROMPT_MATERIAL_MAX_CHARS,
        ),
    )


def build_knowledge_outline_prompt(lesson: Lesson, materials: list[LessonMaterial], config: DeepSeekConfig | None = None) -> str:
    """兼容入口：构造知识主干生成 prompt。"""
    active_config = config or get_deepseek_config()
    return build_prompt_from_template(lesson, materials, active_config.prompt_material_max_chars)


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
    model_name: str | None = None,
    config: DeepSeekConfig | None = None,
) -> tuple[str, str]:
    """调用 DeepSeek 生成知识主干。"""

    active_config = config or get_deepseek_config(model_name)
    prompt = build_knowledge_outline_prompt(lesson, materials, active_config)
    payload = {
        "model": active_config.model,
        "messages": [
            {"role": "system", "content": KNOWLEDGE_OUTLINE_SYSTEM_MESSAGE},
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
