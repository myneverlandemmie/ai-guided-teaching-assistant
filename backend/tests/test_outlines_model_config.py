import httpx
import pytest

from app.models.lesson import Lesson
from app.services.ai.deepseek_client import (
    DeepSeekProviderError,
    generate_deepseek_knowledge_outline,
    get_allowed_deepseek_models,
    get_deepseek_config,
    get_default_deepseek_model,
    is_allowed_deepseek_model,
)


def test_deepseek_model_config_parses_allowed_models(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "DEEPSEEK_ALLOWED_MODELS",
        " deepseek-v4-flash,deepseek-v4-pro,,deepseek-v4-flash,deepseek-chat,deepseek-reasoner,unknown-model ",
    )
    monkeypatch.setenv("DEEPSEEK_DEFAULT_MODEL", "deepseek-v4-pro")

    assert get_allowed_deepseek_models() == ["deepseek-v4-flash", "deepseek-v4-pro"]
    assert get_default_deepseek_model() == "deepseek-v4-pro"
    assert is_allowed_deepseek_model("deepseek-v4-flash") is True
    assert is_allowed_deepseek_model("deepseek-v4-pro") is True
    assert is_allowed_deepseek_model("deepseek-chat") is False
    assert is_allowed_deepseek_model("deepseek-reasoner") is False
    assert is_allowed_deepseek_model("unknown-model") is False


def test_deepseek_model_config_falls_back_when_env_is_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEEPSEEK_ALLOWED_MODELS", "deepseek-chat,unknown-model,,")
    monkeypatch.setenv("DEEPSEEK_DEFAULT_MODEL", "unknown-model")

    assert get_allowed_deepseek_models() == ["deepseek-v4-flash", "deepseek-v4-pro"]
    assert get_default_deepseek_model() == "deepseek-v4-flash"
    assert get_deepseek_config().model == "deepseek-v4-flash"
    with pytest.raises(DeepSeekProviderError):
        get_deepseek_config("deepseek-chat")


def test_deepseek_config_accepts_v4_models_and_invalid_timeout_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_REQUEST_TIMEOUT_SECONDS", "bad")
    expected_timeouts = {"deepseek-v4-pro": 300.0, "deepseek-v4-flash": 180.0}
    for model_name, expected_timeout in expected_timeouts.items():
        config = get_deepseek_config(model_name)
        assert config.model == model_name
        assert config.timeout_seconds == expected_timeout

    monkeypatch.setenv("AI_PROMPT_MATERIAL_MAX_CHARS", "bad")
    config = get_deepseek_config()
    assert config.prompt_material_max_chars == 12000


def test_deepseek_http_errors_do_not_keep_exception_chain_or_key(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_key = "sk-" + "h" * 16 + "5555"
    lesson = Lesson(
        course_id=1,
        planned_lesson_id=None,
        week="1",
        lesson_no="1",
        hours="2",
        lesson_code="0402",
        title="WHERE 条件查询",
        content_summary="条件查询。",
        status="draft",
    )

    class TimeoutClient:
        def __init__(self, timeout: float) -> None:
            self.timeout = timeout

        def __enter__(self) -> "TimeoutClient":
            return self

        def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
            return None

        def post(self, *args: object, **kwargs: object) -> httpx.Response:
            request = httpx.Request("POST", "https://api.example.test", headers={"Authorization": f"Bearer {fake_key}"})
            raise httpx.TimeoutException("timeout", request=request)

    monkeypatch.setattr("app.services.ai.deepseek_client.httpx.Client", TimeoutClient)
    with pytest.raises(DeepSeekProviderError) as timeout_error:
        generate_deepseek_knowledge_outline(lesson, [], fake_key)
    assert timeout_error.value.__cause__ is None
    assert fake_key not in str(timeout_error.value)

    class HttpErrorClient(TimeoutClient):
        def post(self, *args: object, **kwargs: object) -> httpx.Response:
            request = httpx.Request("POST", "https://api.example.test", headers={"Authorization": f"Bearer {fake_key}"})
            raise httpx.RequestError("network", request=request)

    monkeypatch.setattr("app.services.ai.deepseek_client.httpx.Client", HttpErrorClient)
    with pytest.raises(DeepSeekProviderError) as http_error:
        generate_deepseek_knowledge_outline(lesson, [], fake_key)
    assert http_error.value.__cause__ is None
    assert fake_key not in str(http_error.value)
