"""知识主干生成、查看与保存相关路由。"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping, Sequence
from types import SimpleNamespace
from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.knowledge_outline import KnowledgeOutline
from app.models.lesson import Lesson, LessonMaterial
from app.models.lesson_draft import LessonDraft
from app.services.ai import provider as ai_provider
from app.services.ai.deepseek_client import DeepSeekProviderError
from app.services.ai.deepseek_client import get_default_deepseek_model
from app.services.ai.fallback import (
    FALLBACK_REASON_PROVIDER_ERROR,
    FALLBACK_REASON_QUERY_PARAM,
    fallback_message_for_reason,
)
from app.services.ai.sanitizer import sanitize_text_for_outline
from app.services.ai.session_key_store import (
    SESSION_COOKIE_NAME,
    get_session_api_key,
    get_session_selected_model,
)
from app.services.teaching_prep_reference_service import TEACHING_PREP_REFERENCE_DRAFT_TYPE

SanitizeNextPath = Callable[[str | None], str | None]
RequireSameOrigin = Callable[[Request], None]
GetLatestKnowledgeOutline = Callable[[Session, int], KnowledgeOutline | None]
GetLessonDraftByType = Callable[[Session, int, str], LessonDraft | None]
MaterialCategoryLabel = Callable[[LessonMaterial], str]
RunInThreadpool = Callable[..., Awaitable[object]]


def create_outlines_router(
    templates: Jinja2Templates,
    sanitize_next_path: SanitizeNextPath,
    require_same_origin: RequireSameOrigin,
    run_in_threadpool_func: RunInThreadpool,
    get_latest_knowledge_outline: GetLatestKnowledgeOutline,
    get_lesson_draft_by_type: GetLessonDraftByType,
    material_type_labels: Mapping[str, str],
    knowledge_outline_status_labels: Mapping[str, str],
    lesson_draft_status_labels: Mapping[str, str],
    material_category_options: Sequence[tuple[str, str]],
    material_category_label: MaterialCategoryLabel,
) -> APIRouter:
    """创建知识主干路由，复用 main.py 中已有公共依赖。"""

    router = APIRouter()

    def _append_fallback_reason(path: str, reason: str | None) -> str:
        """向站内路径追加 AI fallback reason。"""

        if not reason:
            return path
        separator = "&" if "?" in path else "?"
        return f"{path}{separator}{FALLBACK_REASON_QUERY_PARAM}={quote(reason, safe='')}"

    @router.post("/lessons/{lesson_id}/knowledge-outline/generate")
    async def generate_lesson_knowledge_outline(
        lesson_id: int,
        request: Request,
        return_to: str = Form(""),
        db: Session = Depends(get_db),
    ) -> Response:
        """使用当前 AI Provider 为课次生成知识主干初稿。"""

        require_same_origin(request)
        redirect_to = sanitize_next_path(return_to) or f"/lessons/{lesson_id}/knowledge-outline"
        lesson = db.get(Lesson, lesson_id)
        if lesson is None:
            raise HTTPException(status_code=404, detail="课次不存在")

        materials = db.scalars(
            select(LessonMaterial)
            .where(LessonMaterial.lesson_id == lesson.id)
            .order_by(LessonMaterial.id)
        ).all()
        session_id = request.cookies.get(SESSION_COOKIE_NAME)
        api_key = get_session_api_key(session_id)
        selected_model = get_session_selected_model(session_id) or get_default_deepseek_model()
        lesson_for_ai = SimpleNamespace(
            lesson_code=lesson.lesson_code,
            title=lesson.title,
            content_summary=lesson.content_summary,
        )
        materials_for_ai = [SimpleNamespace(content=material.content) for material in materials]
        try:
            generated_outline = await run_in_threadpool_func(
                ai_provider.generate_knowledge_outline_with_provider,
                lesson_for_ai,
                materials_for_ai,
                api_key,
                selected_model,
            )
        except DeepSeekProviderError as exc:
            if ai_provider.get_ai_provider_name() == "deepseek" and api_key:
                generated_outline = ai_provider.generate_local_knowledge_outline(
                    lesson_for_ai,
                    materials_for_ai,
                    FALLBACK_REASON_PROVIDER_ERROR,
                )
            else:
                if redirect_to.startswith("/ui-v2/"):
                    materials = db.scalars(
                        select(LessonMaterial)
                        .where(LessonMaterial.lesson_id == lesson.id)
                        .order_by(LessonMaterial.id.desc())
                    ).all()
                    return templates.TemplateResponse(
                        request,
                        "lesson_materials_outline_v2.html",
                        {
                            "lesson": lesson,
                            "materials": materials,
                            "knowledge_outline": get_latest_knowledge_outline(db, lesson.id),
                            "material_type_labels": material_type_labels,
                            "material_category_options": material_category_options,
                            "material_category_label": material_category_label,
                            "knowledge_outline_status_labels": knowledge_outline_status_labels,
                            "teaching_prep_reference": get_lesson_draft_by_type(
                                db,
                                lesson.id,
                                TEACHING_PREP_REFERENCE_DRAFT_TYPE,
                            ),
                            "draft_status_labels": lesson_draft_status_labels,
                            "error_message": exc.user_message,
                        },
                        status_code=400,
                    )
                return templates.TemplateResponse(
                    request,
                    "knowledge_outline.html",
                    {
                        "lesson": lesson,
                        "outline": get_latest_knowledge_outline(db, lesson.id),
                        "knowledge_outline_status_labels": knowledge_outline_status_labels,
                        "error_message": exc.user_message,
                        "fallback_message": None,
                        "ai_provider": ai_provider.get_ai_provider_name(),
                    },
                    status_code=400,
                )

        sanitized_generated_content = sanitize_text_for_outline(generated_outline.content)
        # AI 初稿和教师编辑稿初始一致，后续必须由教师编辑保存。
        outline = KnowledgeOutline(
            lesson_id=lesson.id,
            ai_raw_output=sanitized_generated_content,
            edited_content=sanitized_generated_content,
            status="draft",
            generated_by_model=generated_outline.model_name,
        )
        db.add(outline)
        db.commit()
        return RedirectResponse(
            url=_append_fallback_reason(redirect_to, getattr(generated_outline, "fallback_reason", None)),
            status_code=303,
        )

    @router.get("/lessons/{lesson_id}/knowledge-outline", response_class=HTMLResponse)
    async def show_lesson_knowledge_outline(
        lesson_id: int,
        request: Request,
        db: Session = Depends(get_db),
    ) -> HTMLResponse:
        """显示课次知识主干编辑页面。"""

        lesson = db.get(Lesson, lesson_id)
        if lesson is None:
            raise HTTPException(status_code=404, detail="课次不存在")

        outline = get_latest_knowledge_outline(db, lesson.id)
        return templates.TemplateResponse(
            request,
            "knowledge_outline.html",
            {
                "lesson": lesson,
                "outline": outline,
                "knowledge_outline_status_labels": knowledge_outline_status_labels,
                "error_message": None,
                "fallback_message": fallback_message_for_reason(
                    request.query_params.get(FALLBACK_REASON_QUERY_PARAM)
                ),
                "ai_provider": ai_provider.get_ai_provider_name(),
            },
        )

    @router.post("/knowledge-outlines/{outline_id}/save")
    async def save_knowledge_outline(
        outline_id: int,
        edited_content: str = Form(...),
        return_to: str = Form(""),
        db: Session = Depends(get_db),
    ) -> RedirectResponse:
        """保存教师编辑后的知识主干。"""

        outline = db.get(KnowledgeOutline, outline_id)
        if outline is None:
            raise HTTPException(status_code=404, detail="知识主干不存在")

        # 保存教师复核后的版本；后续页面使用 edited_content 展示。
        outline.edited_content = edited_content.strip()
        outline.status = "reviewed"
        db.commit()
        return RedirectResponse(
            url=sanitize_next_path(return_to) or f"/lessons/{outline.lesson_id}/knowledge-outline",
            status_code=303,
        )

    return router
