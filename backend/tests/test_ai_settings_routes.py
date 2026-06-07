from pathlib import Path

import pytest
from sqlalchemy import select, text

from app import main
from app.models.knowledge_outline import KnowledgeOutline
from app.services.ai import session_key_store
from app.services.ai.session_key_store import (
    SESSION_COOKIE_NAME,
    clear_all_session_api_keys_for_tests,
    clear_session_api_key,
    get_session_api_key,
    get_session_selected_model,
    get_session_store_size_for_tests,
    has_session_api_key_for_tests,
    set_session_api_key,
)
from tests.support.course_plan_helpers import (
    SAME_ORIGIN_HEADERS,
    _build_test_client,
    _database_contains_text,
    anyio_backend,
    inline_threadpool_for_tests,
)


def test_session_api_key_store_expires_and_clears(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_all_session_api_keys_for_tests()
    monkeypatch.setenv("AI_SESSION_KEY_IDLE_TIMEOUT_SECONDS", "10")
    current_time = [100.0]
    monkeypatch.setattr(session_key_store, "_now", lambda: current_time[0])
    session_id = "A" * 40

    set_session_api_key(session_id, "sk-" + "x" * 16 + "1111", "deepseek-v4-flash")

    assert get_session_api_key(session_id) is not None
    assert get_session_selected_model(session_id) == "deepseek-v4-flash"
    current_time[0] = 111.0
    assert get_session_api_key(session_id) is None
    assert get_session_selected_model(session_id) is None
    assert has_session_api_key_for_tests(session_id) is False

    set_session_api_key(session_id, "sk-" + "x" * 16 + "2222", "deepseek-v4-pro")
    clear_session_api_key(session_id)
    assert get_session_api_key(session_id) is None
    assert get_session_selected_model(session_id) is None


def test_session_api_key_store_capacity_and_invalid_env(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_all_session_api_keys_for_tests()
    monkeypatch.setenv("AI_SESSION_KEY_IDLE_TIMEOUT_SECONDS", "bad")
    monkeypatch.setenv("AI_SESSION_KEY_MAX_ENTRIES", "2")
    current_time = [200.0]
    monkeypatch.setattr(session_key_store, "_now", lambda: current_time[0])

    for index, session_id in enumerate(["B" * 40, "C" * 40, "D" * 40]):
        current_time[0] += index + 1
        set_session_api_key(session_id, "sk-" + "y" * 16 + str(index).zfill(4))

    assert get_session_store_size_for_tests() == 2
    assert get_session_api_key("B" * 40) is None
    assert get_session_api_key("C" * 40) is not None
    assert get_session_api_key("D" * 40) is not None

    monkeypatch.setenv("AI_SESSION_KEY_MAX_ENTRIES", "bad")
    set_session_api_key("E" * 40, "sk-" + "z" * 16 + "9999")
    assert get_session_api_key("E" * 40) is not None


@pytest.mark.anyio
async def test_ai_settings_can_set_mask_and_clear_session_key(tmp_path: Path) -> None:
    client, _ = _build_test_client(tmp_path)
    try:
        page_response = await client.get("/ai/settings")
        assert page_response.status_code == 200
        assert "状态：未设置" in page_response.text
        assert "API Key 仅保存在当前浏览器会话" in page_response.text
        assert "deepseek-v4-flash" in page_response.text
        assert "deepseek-v4-pro" in page_response.text
        assert "deepseek-chat" not in page_response.text
        assert "deepseek-reasoner" not in page_response.text
        assert "DEEPSEEK_ALLOWED_MODELS" in page_response.text
        assert "DEEPSEEK_DEFAULT_MODEL" in page_response.text
        assert "项目根目录" in page_response.text
        assert ".env.example" in page_response.text
        assert 'href="/ui-v2/courses"' in page_response.text
        assert "课程列表" not in page_response.text
        assert "ai-settings-form-v2" in page_response.text
        assert "ai-settings-actions-v2" in page_response.text
        assert 'form="ai-settings-save-form"' in page_response.text
        assert "ui-v2-field" in page_response.text
        assert "https://api-docs.deepseek.com/zh-cn/quick_start/pricing" in page_response.text
        assert "DeepSeek 官方模型与价格" in page_response.text
        assert "Chat Completion" not in page_response.text
        assert "create-chat-completion" not in page_response.text

        save_response = await client.post(
            "/ai/settings",
            data={"api_key": "sk-test-secret-abcd", "selected_model": "deepseek-v4-flash"},
            headers=SAME_ORIGIN_HEADERS,
        )
        assert save_response.status_code == 200
        assert "状态：已设置" in save_response.text
        assert "sk-****abcd" in save_response.text
        assert "sk-test-secret-abcd" not in save_response.text
        old_session_id = client.cookies.get(SESSION_COOKIE_NAME)
        assert old_session_id is not None
        assert has_session_api_key_for_tests(old_session_id) is True
        assert get_session_selected_model(old_session_id) == "deepseek-v4-flash"

        clear_redirect = await client.post("/ai/settings/clear", headers=SAME_ORIGIN_HEADERS, follow_redirects=False)
        assert clear_redirect.status_code == 303
        assert "Max-Age=0" in clear_redirect.headers.get("set-cookie", "")
        assert has_session_api_key_for_tests(old_session_id) is False
        assert get_session_selected_model(old_session_id) is None

        clear_response = await client.get("/ai/settings")
        assert clear_response.status_code == 200
        assert "状态：未设置" in clear_response.text
        assert client.cookies.get(SESSION_COOKIE_NAME) != old_session_id
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


def test_ai_settings_next_path_sanitizer() -> None:
    assert main.sanitize_next_path("/lessons/1") == "/lessons/1"
    assert main.sanitize_next_path("/lessons/1/knowledge-outline") == "/lessons/1/knowledge-outline"
    assert main.sanitize_next_path("/courses/1/lessons") == "/courses/1/lessons"
    assert main.sanitize_next_path("http://evil.com") is None
    assert main.sanitize_next_path("https://evil.com") is None
    assert main.sanitize_next_path("//evil.com") is None
    assert main.sanitize_next_path("/\\evil") is None
    assert main.sanitize_next_path("/lessons/1\nSet-Cookie: bad=1") is None
    assert main.sanitize_next_path("/lessons/1\rLocation: http://evil.com") is None
    assert main.sanitize_next_path("lessons/1") is None
    assert main.sanitize_next_path("") is None


@pytest.mark.anyio
async def test_ai_settings_safe_next_redirects_after_saving_key(tmp_path: Path) -> None:
    client, _ = _build_test_client(tmp_path)
    fake_key = "sk-" + "n" * 16 + "8888"
    try:
        page_response = await client.get("/ai/settings?next=/lessons/1")
        assert page_response.status_code == 200
        assert 'name="next"' in page_response.text
        assert 'value="/lessons/1"' in page_response.text

        save_response = await client.post(
            "/ai/settings",
            data={"api_key": fake_key, "selected_model": "deepseek-v4-pro", "next": "/lessons/1"},
            headers=SAME_ORIGIN_HEADERS,
            follow_redirects=False,
        )

        assert save_response.status_code == 303
        assert save_response.headers["location"] == "/lessons/1"
        assert fake_key not in save_response.text
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_ai_settings_rejects_unsafe_next_without_echo_or_external_redirect(tmp_path: Path) -> None:
    client, _ = _build_test_client(tmp_path)
    fake_key = "sk-" + "u" * 16 + "9999"
    unsafe_next_values = [
        "http://evil.com",
        "//evil.com",
        "/\\evil",
        "/lessons/1\nLocation: http://evil.com",
    ]
    try:
        for unsafe_next in unsafe_next_values:
            page_response = await client.get("/ai/settings", params={"next": unsafe_next})
            assert page_response.status_code == 200
            assert unsafe_next not in page_response.text
            assert 'name="next"' not in page_response.text

            save_response = await client.post(
                "/ai/settings",
                data={"api_key": fake_key, "selected_model": "deepseek-v4-flash", "next": unsafe_next},
                headers=SAME_ORIGIN_HEADERS,
                follow_redirects=False,
            )

            assert save_response.status_code == 200
            assert "当前会话 API Key 已设置" in save_response.text
            assert "evil.com" not in save_response.text
            assert "/\\evil" not in save_response.text
            assert fake_key not in save_response.text
            assert "location" not in save_response.headers
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_ai_settings_next_keeps_same_origin_protection(tmp_path: Path) -> None:
    client, _ = _build_test_client(tmp_path)
    fake_key = "sk-" + "x" * 16 + "0000"
    try:
        response = await client.post(
            "/ai/settings",
            data={"api_key": fake_key, "selected_model": "deepseek-v4-flash", "next": "/lessons/1"},
            headers={"origin": "http://evil.example"},
            follow_redirects=False,
        )

        assert response.status_code == 403
        assert fake_key not in response.text
        assert response.headers.get("location") is None
        assert get_session_store_size_for_tests() == 0
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_ai_settings_rejects_invalid_selected_model_without_saving_key(tmp_path: Path) -> None:
    client, _ = _build_test_client(tmp_path)
    fake_key = "sk-" + "v" * 16 + "1212"
    try:
        response = await client.post(
            "/ai/settings",
            data={"api_key": fake_key, "selected_model": "deepseek-chat"},
            headers=SAME_ORIGIN_HEADERS,
            follow_redirects=False,
        )

        assert response.status_code == 400
        assert "模型配置无效" in response.text
        assert fake_key not in response.text
        assert get_session_store_size_for_tests() == 0
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_invalid_session_cookie_is_replaced_without_echo(tmp_path: Path) -> None:
    client, _ = _build_test_client(tmp_path)
    invalid_session = "bad/session"
    try:
        response = await client.get("/ai/settings", headers={"cookie": f"{SESSION_COOKIE_NAME}={invalid_session}"})

        assert response.status_code == 200
        assert invalid_session not in response.text
        new_session_id = response.cookies.get(SESSION_COOKIE_NAME)
        assert new_session_id is not None
        assert new_session_id != invalid_session
        assert has_session_api_key_for_tests(invalid_session) is False
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_api_key_is_not_written_to_database(tmp_path: Path) -> None:
    client, session_factory = _build_test_client(tmp_path)
    fake_key = "sk-" + "d" * 16 + "3333"
    try:
        response = await client.post(
            "/ai/settings",
            data={"api_key": fake_key, "selected_model": "deepseek-v4-pro"},
            headers=SAME_ORIGIN_HEADERS,
        )

        assert response.status_code == 200
        assert fake_key not in response.text
        with session_factory() as session:
            key_tables = session.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND lower(name) LIKE '%key%'")
            ).all()
            assert key_tables == []
            assert session.scalar(select(KnowledgeOutline)) is None
            assert _database_contains_text(session, fake_key) is False
            assert _database_contains_text(session, "deepseek-v4-pro") is False
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_ai_settings_rejects_cross_origin_without_setting_key(tmp_path: Path) -> None:
    client, _ = _build_test_client(tmp_path)
    fake_key = "sk-" + "o" * 16 + "4444"
    try:
        response = await client.post(
            "/ai/settings",
            data={"api_key": fake_key, "selected_model": "deepseek-v4-flash"},
            headers={"origin": "http://evil.example"},
        )

        assert response.status_code == 403
        assert fake_key not in response.text
        assert get_session_store_size_for_tests() == 0
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()
