"""学习通习题文件导出与草稿下载相关路由。"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.lesson import Lesson
from app.models.lesson_draft import LessonDraft
from app.services.ai.lesson_draft_service import write_chaoxing_template_xlsx
from app.services.exports.docx_exporter import (
    DOCX_MIME_TYPE,
    DocxExportError,
    build_lesson_draft_docx,
)

SanitizeNextPath = Callable[[str | None], str | None]
ResolveReturnToPath = Callable[[str | None, str], tuple[str, bool]]
SafeExportPart = Callable[[str | None, str], str]
SafeExportFilename = Callable[[str | None, str], str | None]
AppendQueryParam = Callable[[str, str, str], str]
GetExportDir = Callable[[], Path]

DOWNLOAD_ERROR_MESSAGE = "下载文件生成失败，请重新生成或稍后再试。"
CHAOXING_EXPORT_ERROR_QUERY_PARAM = "chaoxing_export_error"


def create_exports_router(
    sanitize_next_path: SanitizeNextPath,
    resolve_return_to_path: ResolveReturnToPath,
    safe_export_part: SafeExportPart,
    safe_export_filename: SafeExportFilename,
    append_query_param: AppendQueryParam,
    get_chaoxing_export_dir: GetExportDir,
    get_guide_export_dir: GetExportDir,
    lesson_draft_download_name_parts: Mapping[str, str],
    teaching_prep_reference_draft_type: str,
) -> APIRouter:
    """创建导出与下载路由，复用 main.py 中已有公共依赖。"""

    router = APIRouter()

    @router.post("/lessons/{lesson_id}/drafts/{draft_id}/export-chaoxing")
    async def export_diagnostic_probe_to_chaoxing(
        lesson_id: int,
        draft_id: int,
        return_to: str = Form(""),
        db: Session = Depends(get_db),
    ) -> RedirectResponse:
        """将导学案前测导出为学习通题库导入 xlsx。"""

        lesson = db.get(Lesson, lesson_id)
        draft = db.get(LessonDraft, draft_id)
        if lesson is None or draft is None or draft.lesson_id != lesson_id:
            raise HTTPException(status_code=404, detail="导学草稿不存在")
        if draft.draft_type != "diagnostic_probe":
            raise HTTPException(status_code=400, detail="只有导学案前测可以导出学习通题库模板")

        redirect_to, _return_to_invalid = resolve_return_to_path(return_to, f"/lessons/{lesson.id}/drafts")
        try:
            chaoxing_export_dir = get_chaoxing_export_dir()
            chaoxing_export_dir.mkdir(parents=True, exist_ok=True)
            lesson_part = safe_export_part(lesson.lesson_code, str(lesson.id))
            filename = f"lesson_{lesson.id}_{lesson_part}_diagnostic_probe.xlsx"
            output_path = chaoxing_export_dir / filename
            write_chaoxing_template_xlsx(lesson, draft, output_path)
        except Exception:
            return RedirectResponse(
                url=append_query_param(redirect_to, CHAOXING_EXPORT_ERROR_QUERY_PARAM, "1"),
                status_code=303,
            )
        return RedirectResponse(url=append_query_param(redirect_to, "chaoxing_file", filename), status_code=303)

    @router.get("/exports/chaoxing/{filename}")
    async def download_chaoxing_export(filename: str) -> Response:
        """下载已生成的学习通题库导入文件。"""

        safe_filename = safe_export_filename(filename, ".xlsx")
        if safe_filename is None:
            raise HTTPException(status_code=404, detail="导出文件不存在")
        file_path = get_chaoxing_export_dir() / safe_filename
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="导出文件不存在")
        return Response(
            content=file_path.read_bytes(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{safe_filename}"'},
        )

    @router.get("/lessons/{lesson_id}/drafts/{draft_id}/download-md")
    async def download_lesson_draft_markdown(
        lesson_id: int,
        draft_id: int,
        db: Session = Depends(get_db),
    ) -> Response:
        """将当前导学案或备课参考建议草稿下载为 Markdown。"""

        lesson = db.get(Lesson, lesson_id)
        draft = db.get(LessonDraft, draft_id)
        if lesson is None or draft is None or draft.lesson_id != lesson_id:
            raise HTTPException(status_code=404, detail="导学草稿不存在")
        downloadable_types = {"guide_low", "guide_mid", "guide_high", teaching_prep_reference_draft_type}
        if draft.draft_type not in downloadable_types:
            raise HTTPException(status_code=400, detail="只有导学案或备课参考建议草稿可以下载 Markdown")

        try:
            guide_export_dir = get_guide_export_dir()
            guide_export_dir.mkdir(parents=True, exist_ok=True)
            filename_part = lesson_draft_download_name_parts.get(draft.draft_type, "learning_draft")
            filename = f"lesson_{lesson.id}_{filename_part}.md"
            output_path = guide_export_dir / filename
            output_path.write_text(draft.content, encoding="utf-8")
            return Response(
                content=draft.content,
                media_type="text/markdown; charset=utf-8",
                headers={"Content-Disposition": f'attachment; filename="{filename}"'},
            )
        except Exception:
            return _friendly_export_error(DOWNLOAD_ERROR_MESSAGE, 503)

    @router.get("/lessons/{lesson_id}/drafts/{draft_id}/download-docx")
    async def download_lesson_draft_docx(
        lesson_id: int,
        draft_id: int,
        db: Session = Depends(get_db),
    ) -> Response:
        """将当前导学案或备课参考建议草稿下载为基础 DOCX。"""

        lesson = db.get(Lesson, lesson_id)
        draft = db.get(LessonDraft, draft_id)
        if lesson is None or draft is None or draft.lesson_id != lesson_id:
            return _friendly_export_error("导学草稿不存在", 404)
        downloadable_types = {"guide_low", "guide_mid", "guide_high", teaching_prep_reference_draft_type}
        if draft.draft_type not in downloadable_types:
            return _friendly_export_error("只有导学案或备课参考建议草稿可以下载 DOCX", 400)

        try:
            filename_part = lesson_draft_download_name_parts.get(draft.draft_type, "learning_draft")
            lesson_part = _ascii_export_part(safe_export_part(lesson.lesson_code, str(lesson.id)), str(lesson.id))
            filename = f"lesson_{lesson.id}_{lesson_part}_{filename_part}.docx"
            docx_content = build_lesson_draft_docx(lesson, draft)
            guide_export_dir = get_guide_export_dir()
            guide_export_dir.mkdir(parents=True, exist_ok=True)
            output_path = guide_export_dir / filename
            output_path.write_bytes(docx_content)
            return Response(
                content=docx_content,
                media_type=DOCX_MIME_TYPE,
                headers={"Content-Disposition": f'attachment; filename="{filename}"'},
            )
        except DocxExportError:
            return _friendly_export_error(DOWNLOAD_ERROR_MESSAGE, 400)
        except Exception:
            return _friendly_export_error(DOWNLOAD_ERROR_MESSAGE, 503)

    return router


def _friendly_export_error(message: str, status_code: int) -> Response:
    return Response(content=message, status_code=status_code, media_type="text/plain; charset=utf-8")


def _ascii_export_part(value: str, fallback: str) -> str:
    cleaned = "".join(char for char in value if char.isascii() and (char.isalnum() or char in {"-", "_"}))
    return cleaned or fallback
