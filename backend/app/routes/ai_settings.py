"""AI 设置相关路由。"""

from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.services.ai import provider as ai_provider
from app.services.ai.deepseek_client import (
    get_allowed_deepseek_models,
    get_default_deepseek_model,
    is_allowed_deepseek_model,
    normalize_model_name,
)
from app.services.ai.session_key_store import (
    SESSION_COOKIE_NAME,
    clear_session_api_key,
    delete_session_cookie,
    get_session_api_key,
    get_session_selected_model,
    mask_api_key,
    resolve_session_id,
    set_session_api_key,
    set_session_cookie,
)

SanitizeNextPath = Callable[[str | None], str | None]
RequireSameOrigin = Callable[[Request], None]


def create_ai_settings_router(
    templates: Jinja2Templates,
    sanitize_next_path: SanitizeNextPath,
    require_same_origin: RequireSameOrigin,
) -> APIRouter:
    """创建 AI 设置路由，复用 main.py 中已有公共依赖。"""

    router = APIRouter()

    def _ai_settings_context(
        session_id: str,
        message: str | None = None,
        next_path: str | None = None,
    ) -> dict[str, object]:
        """构造 AI 设置页面上下文。"""

        api_key = get_session_api_key(session_id)
        allowed_models = get_allowed_deepseek_models()
        selected_model = get_session_selected_model(session_id) or get_default_deepseek_model()
        return {
            "is_api_key_set": bool(api_key),
            "masked_api_key": mask_api_key(api_key),
            "message": message,
            "ai_provider": ai_provider.get_ai_provider_name(),
            "next_path": sanitize_next_path(next_path),
            "allowed_models": allowed_models,
            "selected_model": selected_model,
            "default_model": get_default_deepseek_model(),
        }

    @router.get("/ai/settings", response_class=HTMLResponse)
    async def show_ai_settings(request: Request) -> HTMLResponse:
        """显示当前会话 API Key 设置页面。"""

        session_id, created = resolve_session_id(request)
        next_path = sanitize_next_path(request.query_params.get("next"))
        response = templates.TemplateResponse(
            request,
            "ai_settings.html",
            _ai_settings_context(session_id, next_path=next_path),
        )
        if created:
            set_session_cookie(response, session_id)
        return response

    @router.post("/ai/settings", response_class=HTMLResponse)
    async def save_ai_settings(
        request: Request,
    ) -> HTMLResponse:
        """保存当前会话临时 API Key，不入库。"""

        require_same_origin(request)
        form = await request.form()
        api_key = str(form.get("api_key", ""))
        selected_model = normalize_model_name(str(form.get("selected_model", ""))) or get_default_deepseek_model()
        next_path = sanitize_next_path(str(form.get("next", "")))
        session_id, created = resolve_session_id(request)
        cleaned_key = api_key.strip()
        if not is_allowed_deepseek_model(selected_model):
            response = templates.TemplateResponse(
                request,
                "ai_settings.html",
                _ai_settings_context(session_id, "模型配置无效，请选择当前允许列表中的 DeepSeek V4 模型。", next_path=next_path),
                status_code=400,
            )
            if created:
                set_session_cookie(response, session_id)
            return response

        if cleaned_key:
            # API Key 只进入内存会话映射，不写数据库、不写日志、不回显。
            set_session_api_key(session_id, cleaned_key, selected_model)

        if cleaned_key and next_path:
            response = RedirectResponse(url=next_path, status_code=303)
            if created:
                set_session_cookie(response, session_id)
            return response

        message = "当前会话 API Key 已设置。" if cleaned_key else "请输入有效的 DeepSeek API Key。"
        status_code = 200 if cleaned_key else 400
        response = templates.TemplateResponse(
            request,
            "ai_settings.html",
            _ai_settings_context(session_id, message, next_path=next_path),
            status_code=status_code,
        )
        if created:
            set_session_cookie(response, session_id)
        return response

    @router.post("/ai/settings/clear")
    async def clear_ai_settings(request: Request) -> RedirectResponse:
        """清除当前会话临时 API Key。"""

        require_same_origin(request)
        session_id = request.cookies.get(SESSION_COOKIE_NAME)
        clear_session_api_key(session_id)
        response = RedirectResponse(url="/ai/settings", status_code=303)
        delete_session_cookie(response)
        return response

    return router
