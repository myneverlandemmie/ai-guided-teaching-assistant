"""会话级 API Key 临时存储。"""

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass, field
from secrets import token_urlsafe
from threading import RLock

from fastapi import Request, Response

SESSION_COOKIE_NAME = "teacher_session_id"
DEFAULT_IDLE_TIMEOUT_SECONDS = 14_400
DEFAULT_MAX_ENTRIES = 200
SESSION_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{32,128}$")


@dataclass
class SessionApiKeyRecord:
    """内存中的会话 Key 记录，repr 不包含 API Key。"""

    api_key: str = field(repr=False)
    created_at: float
    last_used_at: float


_session_api_keys: dict[str, SessionApiKeyRecord] = {}
_store_lock = RLock()


def _now() -> float:
    """返回当前时间戳，测试中可 monkeypatch。"""

    return time.time()


def _parse_positive_int_env(name: str, default: int) -> int:
    """安全解析正整数环境变量，非法值回退默认值。"""

    try:
        value = int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


def get_idle_timeout_seconds() -> int:
    """读取会话 Key 空闲过期秒数。"""

    return _parse_positive_int_env("AI_SESSION_KEY_IDLE_TIMEOUT_SECONDS", DEFAULT_IDLE_TIMEOUT_SECONDS)


def get_max_entries() -> int:
    """读取会话 Key 最大保留项数。"""

    return _parse_positive_int_env("AI_SESSION_KEY_MAX_ENTRIES", DEFAULT_MAX_ENTRIES)


def is_valid_session_id(session_id: str | None) -> bool:
    """校验 session_id 是否为 URL-safe token。"""

    if not session_id:
        return False
    return bool(SESSION_ID_PATTERN.fullmatch(session_id))


def resolve_session_id(request: Request) -> tuple[str, bool]:
    """读取或创建会话 ID，但不直接写 cookie。"""

    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    if is_valid_session_id(session_id):
        return str(session_id), False
    return token_urlsafe(32), True


def set_session_cookie(response: Response, session_id: str) -> None:
    """把 session_id 写入 HttpOnly cookie。"""

    secure_cookie = os.getenv("AI_SESSION_COOKIE_SECURE", "false").strip().lower() in {"1", "true", "yes"}
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_id,
        httponly=True,
        samesite="lax",
        secure=secure_cookie,
    )


def delete_session_cookie(response: Response) -> None:
    """删除临时 session cookie。"""

    response.delete_cookie(key=SESSION_COOKIE_NAME, httponly=True, samesite="lax")


def get_or_create_session_id(request: Request, response: Response) -> str:
    """读取或创建浏览器会话 ID，并写入 HttpOnly cookie。"""

    session_id, created = resolve_session_id(request)
    if created:
        # cookie 只保存 session_id，不保存 API Key；公网 HTTPS 部署时可通过环境开关启用 Secure。
        set_session_cookie(response, session_id)
    return session_id


def _is_expired(record: SessionApiKeyRecord, now: float | None = None) -> bool:
    """判断会话 Key 是否已空闲过期。"""

    active_now = _now() if now is None else now
    return active_now - record.last_used_at > get_idle_timeout_seconds()


def cleanup_expired_session_api_keys() -> None:
    """清理已空闲过期的会话 Key。"""

    now = _now()
    with _store_lock:
        expired_ids = [session_id for session_id, record in _session_api_keys.items() if _is_expired(record, now)]
        for session_id in expired_ids:
            _session_api_keys.pop(session_id, None)


def _enforce_capacity_locked() -> None:
    """在持锁状态下执行容量上限清理。"""

    max_entries = get_max_entries()
    if len(_session_api_keys) <= max_entries:
        return

    now = _now()
    expired_ids = [session_id for session_id, record in _session_api_keys.items() if _is_expired(record, now)]
    for session_id in expired_ids:
        _session_api_keys.pop(session_id, None)

    overflow = len(_session_api_keys) - max_entries
    if overflow <= 0:
        return

    oldest_session_ids = sorted(
        _session_api_keys,
        key=lambda session_id: _session_api_keys[session_id].last_used_at,
    )[:overflow]
    for session_id in oldest_session_ids:
        _session_api_keys.pop(session_id, None)


def set_session_api_key(session_id: str, api_key: str) -> None:
    """为当前会话保存临时 API Key。"""

    if not is_valid_session_id(session_id):
        return
    cleaned_key = api_key.strip()
    if not cleaned_key:
        return
    now = _now()
    with _store_lock:
        _session_api_keys[session_id] = SessionApiKeyRecord(
            api_key=cleaned_key,
            created_at=now,
            last_used_at=now,
        )
        _enforce_capacity_locked()


def get_session_api_key(session_id: str | None) -> str | None:
    """读取当前会话临时 API Key，未过期时更新 last_used_at。"""

    if not is_valid_session_id(session_id):
        return None
    cleanup_expired_session_api_keys()
    now = _now()
    with _store_lock:
        record = _session_api_keys.get(str(session_id))
        if record is None:
            return None
        if _is_expired(record, now):
            _session_api_keys.pop(str(session_id), None)
            return None
        record.last_used_at = now
        return record.api_key


def clear_session_api_key(session_id: str | None) -> None:
    """清除当前会话临时 API Key。"""

    if not is_valid_session_id(session_id):
        return
    with _store_lock:
        _session_api_keys.pop(str(session_id), None)


def mask_api_key(api_key: str | None) -> str:
    """返回可展示的 API Key 掩码，绝不回显完整 Key。"""

    if not api_key:
        return "未设置"
    tail = api_key[-4:] if len(api_key) >= 4 else "****"
    prefix = "sk-" if api_key.startswith("sk-") else ""
    return f"{prefix}****{tail}"


def clear_all_session_api_keys_for_tests() -> None:
    """清空内存 Key 存储，仅供自动化测试隔离使用。"""

    with _store_lock:
        _session_api_keys.clear()


def get_session_store_size_for_tests() -> int:
    """返回当前会话 Key 记录数，仅供测试。"""

    with _store_lock:
        return len(_session_api_keys)


def has_session_api_key_for_tests(session_id: str) -> bool:
    """返回指定 session 是否存在 Key，仅供测试，不返回 Key 内容。"""

    with _store_lock:
        return session_id in _session_api_keys
