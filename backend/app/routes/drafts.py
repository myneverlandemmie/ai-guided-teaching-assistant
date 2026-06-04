"""草稿列表、前测、导学案与备课参考建议相关路由。"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.models.knowledge_outline import KnowledgeOutline
from app.models.lesson import Lesson, LessonMaterial
from app.models.lesson_draft import LESSON_DRAFT_TYPES, LessonDraft
from app.services.ai.deepseek_client import get_default_deepseek_model
from app.services.ai.lesson_draft_ai_service import generate_single_lesson_draft_with_ai
from app.services.ai.session_key_store import (
    SESSION_COOKIE_NAME,
    get_session_api_key,
    get_session_selected_model,
)
from app.services.teaching_prep_reference_service import generate_teaching_prep_reference

SanitizeNextPath = Callable[[str | None], str | None]
GetLatestKnowledgeOutline = Callable[[Session, int], KnowledgeOutline | None]
GetLessonDrafts = Callable[[Session, int], list[LessonDraft]]
GetLessonDraftByType = Callable[[Session, int, str], LessonDraft | None]
LearningGuideDependencyMessage = Callable[[str, bool, bool], str | None]
UpsertLessonDrafts = Callable[[Session, Lesson, KnowledgeOutline | None, list[object]], None]
SafeExportFilename = Callable[[str | None, str], str | None]
AppendQueryParam = Callable[[str, str, str], str]
DiagnosticProbeViewContext = Callable[[LessonDraft | None], dict[str, object]]
RunInThreadpool = Callable[..., Awaitable[object]]


def create_drafts_router(
    templates: Jinja2Templates,
    sanitize_next_path: SanitizeNextPath,
    run_in_threadpool_func: RunInThreadpool,
    get_latest_knowledge_outline: GetLatestKnowledgeOutline,
    get_lesson_drafts: GetLessonDrafts,
    get_lesson_draft_by_type: GetLessonDraftByType,
    learning_guide_dependency_message: LearningGuideDependencyMessage,
    upsert_lesson_drafts: UpsertLessonDrafts,
    safe_export_filename: SafeExportFilename,
    append_query_param: AppendQueryParam,
    diagnostic_probe_view_context: DiagnosticProbeViewContext,
    draft_type_labels: Mapping[str, str],
    lesson_draft_status_labels: Mapping[str, str],
) -> APIRouter:
    """创建草稿相关路由，复用 main.py 中已有公共依赖。"""

    router = APIRouter()

    @router.get("/ui-v2/lessons/{lesson_id}/diagnostic-probe", response_class=HTMLResponse)
    async def show_diagnostic_probe_v2(
        lesson_id: int,
        request: Request,
        db: Session = Depends(get_db),
    ) -> HTMLResponse:
        """课前学情测试 V2 preview。"""

        lesson = db.scalar(
            select(Lesson)
            .options(selectinload(Lesson.course))
            .where(Lesson.id == lesson_id)
        )
        if lesson is None:
            raise HTTPException(status_code=404, detail="课次不存在")

        draft = get_lesson_draft_by_type(db, lesson.id, "diagnostic_probe")
        chaoxing_filename = safe_export_filename(request.query_params.get("chaoxing_file"), ".xlsx")
        fallback_message = (
            "DeepSeek 响应较慢、调用失败或当前未设置 API Key，已回退为本地结构化草稿。你可以稍后重试，或减少材料后再生成。"
            if request.query_params.get("draft_fallback") == "1"
            else None
        )
        return templates.TemplateResponse(
            request,
            "diagnostic_probe_v2.html",
            {
                "lesson": lesson,
                "outline": get_latest_knowledge_outline(db, lesson.id),
                "draft": draft,
                "draft_status_labels": lesson_draft_status_labels,
                "chaoxing_export_url": f"/exports/chaoxing/{chaoxing_filename}" if chaoxing_filename else None,
                "fallback_message": fallback_message,
                **diagnostic_probe_view_context(draft),
            },
        )

    @router.get("/ui-v2/lessons/{lesson_id}/learning-guides", response_class=HTMLResponse)
    async def show_learning_guides_v2(
        lesson_id: int,
        request: Request,
        db: Session = Depends(get_db),
    ) -> HTMLResponse:
        """学生导学案 V2 preview。"""

        lesson = db.scalar(
            select(Lesson)
            .options(selectinload(Lesson.course))
            .where(Lesson.id == lesson_id)
        )
        if lesson is None:
            raise HTTPException(status_code=404, detail="课次不存在")

        guide_drafts = {
            draft.draft_type: draft
            for draft in get_lesson_drafts(db, lesson.id)
            if draft.draft_type in {"guide_low", "guide_mid", "guide_high"}
        }
        fallback_message = (
            "DeepSeek 响应较慢、调用失败或当前未设置 API Key，已回退为本地结构化草稿。你可以稍后重试，或减少材料后再生成。"
            if request.query_params.get("draft_fallback") == "1"
            else None
        )
        return templates.TemplateResponse(
            request,
            "learning_guides_v2.html",
            {
                "lesson": lesson,
                "outline": get_latest_knowledge_outline(db, lesson.id),
                "guide_low": guide_drafts.get("guide_low"),
                "guide_mid": guide_drafts.get("guide_mid"),
                "guide_high": guide_drafts.get("guide_high"),
                "draft_status_labels": lesson_draft_status_labels,
                "fallback_message": fallback_message,
                "dependency_message": request.query_params.get("dependency_message") or None,
            },
        )

    @router.get("/lessons/{lesson_id}/drafts", response_class=HTMLResponse)
    async def show_lesson_drafts(
        lesson_id: int,
        request: Request,
        db: Session = Depends(get_db),
    ) -> HTMLResponse:
        """显示导学案前测与三阶导学案草稿。"""

        lesson = db.get(Lesson, lesson_id)
        if lesson is None:
            raise HTTPException(status_code=404, detail="课次不存在")

        outline = get_latest_knowledge_outline(db, lesson.id)
        drafts = get_lesson_drafts(db, lesson.id)
        chaoxing_filename = safe_export_filename(request.query_params.get("chaoxing_file"), ".xlsx")
        fallback_message = (
            "DeepSeek 响应较慢、调用失败或当前未设置 API Key，已回退为本地结构化草稿。你可以稍后重试，或减少材料后再生成。"
            if request.query_params.get("draft_fallback") == "1"
            else None
        )
        return templates.TemplateResponse(
            request,
            "lesson_drafts.html",
            {
                "lesson": lesson,
                "outline": outline,
                "drafts": drafts,
                "draft_type_labels": draft_type_labels,
                "draft_status_labels": lesson_draft_status_labels,
                "has_low_guide": any(draft.draft_type == "guide_low" for draft in drafts),
                "chaoxing_export_url": f"/exports/chaoxing/{chaoxing_filename}" if chaoxing_filename else None,
                "error_message": None if outline else "请先生成并保存知识主干，再生成课前学情测试与学生导学案草稿。",
                "fallback_message": fallback_message,
            },
        )

    @router.post("/lessons/{lesson_id}/drafts/generate")
    async def generate_lesson_drafts_route(
        lesson_id: int,
        request: Request,
        db: Session = Depends(get_db),
    ) -> RedirectResponse:
        """兼容旧入口：只生成或更新课前学情测试，不连带生成导学案。"""

        lesson = db.get(Lesson, lesson_id)
        if lesson is None:
            raise HTTPException(status_code=404, detail="课次不存在")

        outline = get_latest_knowledge_outline(db, lesson.id)
        if outline is None:
            return RedirectResponse(url=f"/lessons/{lesson.id}/drafts", status_code=303)

        session_id = request.cookies.get(SESSION_COOKIE_NAME)
        draft, used_fallback = await run_in_threadpool_func(
            generate_single_lesson_draft_with_ai,
            lesson,
            outline,
            "diagnostic_probe",
            get_session_api_key(session_id),
            get_session_selected_model(session_id) or get_default_deepseek_model(),
        )
        upsert_lesson_drafts(db, lesson, outline, [draft])
        db.commit()
        suffix = "?draft_fallback=1" if used_fallback else ""
        return RedirectResponse(url=f"/lessons/{lesson.id}/drafts{suffix}", status_code=303)

    @router.post("/lessons/{lesson_id}/drafts/generate/teaching_prep_reference")
    async def generate_teaching_prep_reference_route(
        lesson_id: int,
        request: Request,
        return_to: str = Form(""),
        db: Session = Depends(get_db),
    ) -> RedirectResponse:
        """生成或更新备课参考建议草稿。"""

        lesson = db.scalar(
            select(Lesson)
            .options(selectinload(Lesson.materials), selectinload(Lesson.course))
            .where(Lesson.id == lesson_id)
        )
        if lesson is None:
            raise HTTPException(status_code=404, detail="课次不存在")

        materials = db.scalars(
            select(LessonMaterial)
            .where(LessonMaterial.lesson_id == lesson.id)
            .order_by(LessonMaterial.id)
        ).all()
        outline = get_latest_knowledge_outline(db, lesson.id)
        session_id = request.cookies.get(SESSION_COOKIE_NAME)
        draft, _used_fallback = await run_in_threadpool_func(
            generate_teaching_prep_reference,
            lesson,
            materials,
            outline,
            get_session_api_key(session_id),
            get_session_selected_model(session_id) or get_default_deepseek_model(),
        )
        upsert_lesson_drafts(db, lesson, outline, [draft])
        db.commit()
        redirect_to = sanitize_next_path(return_to) or f"/lessons/{lesson.id}/drafts"
        return RedirectResponse(url=redirect_to, status_code=303)

    @router.post("/lessons/{lesson_id}/drafts/generate/{draft_type}")
    async def generate_tiered_lesson_draft_route(
        lesson_id: int,
        draft_type: str,
        request: Request,
        return_to: str = Form(""),
        db: Session = Depends(get_db),
    ) -> RedirectResponse:
        """按需生成或更新单个导学草稿。"""

        if draft_type not in LESSON_DRAFT_TYPES:
            raise HTTPException(status_code=404, detail="导学草稿类型不存在")

        lesson = db.get(Lesson, lesson_id)
        if lesson is None:
            raise HTTPException(status_code=404, detail="课次不存在")

        outline = get_latest_knowledge_outline(db, lesson.id)
        if outline is None:
            return RedirectResponse(
                url=sanitize_next_path(return_to) or f"/lessons/{lesson.id}/drafts",
                status_code=303,
            )

        low_guide = get_lesson_draft_by_type(db, lesson.id, "guide_low")
        mid_guide = get_lesson_draft_by_type(db, lesson.id, "guide_mid")
        dependency_message = learning_guide_dependency_message(
            draft_type,
            low_guide is not None,
            mid_guide is not None,
        )
        if dependency_message:
            redirect_to = sanitize_next_path(return_to) or f"/lessons/{lesson.id}/drafts"
            return RedirectResponse(
                url=append_query_param(redirect_to, "dependency_message", dependency_message),
                status_code=303,
            )

        session_id = request.cookies.get(SESSION_COOKIE_NAME)
        related_drafts = {
            related_type: draft.content
            for related_type, draft in {"guide_low": low_guide, "guide_mid": mid_guide}.items()
            if draft is not None
        }
        api_key = get_session_api_key(session_id)
        selected_model = get_session_selected_model(session_id) or get_default_deepseek_model()
        if api_key:
            draft, used_fallback = await run_in_threadpool_func(
                generate_single_lesson_draft_with_ai,
                lesson,
                outline,
                draft_type,
                api_key,
                selected_model,
                related_drafts,
            )
        else:
            draft, used_fallback = generate_single_lesson_draft_with_ai(
                lesson,
                outline,
                draft_type,
                None,
                selected_model,
                related_drafts,
            )
        upsert_lesson_drafts(db, lesson, outline, [draft])
        db.commit()
        redirect_to = sanitize_next_path(return_to) or f"/lessons/{lesson.id}/drafts"
        if used_fallback:
            redirect_to = append_query_param(redirect_to, "draft_fallback", "1")
        return RedirectResponse(url=redirect_to, status_code=303)

    @router.post("/lessons/{lesson_id}/drafts/{draft_id}/save")
    async def save_lesson_draft(
        lesson_id: int,
        draft_id: int,
        title: str = Form(...),
        content: str = Form(...),
        return_to: str = Form(""),
        db: Session = Depends(get_db),
    ) -> RedirectResponse:
        """保存教师编辑后的导学草稿。"""

        draft = db.get(LessonDraft, draft_id)
        if draft is None or draft.lesson_id != lesson_id:
            raise HTTPException(status_code=404, detail="导学草稿不存在")

        draft.title = title.strip() or draft.title
        draft.content = content.strip()
        draft.status = "reviewed"
        db.commit()
        return RedirectResponse(url=sanitize_next_path(return_to) or f"/lessons/{lesson_id}/drafts", status_code=303)

    return router
