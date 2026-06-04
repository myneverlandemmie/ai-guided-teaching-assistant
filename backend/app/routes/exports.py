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

SanitizeNextPath = Callable[[str | None], str | None]
SafeExportPart = Callable[[str | None, str], str]
SafeExportFilename = Callable[[str | None, str], str | None]
AppendQueryParam = Callable[[str, str, str], str]
GetExportDir = Callable[[], Path]


def create_exports_router(
    sanitize_next_path: SanitizeNextPath,
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

        chaoxing_export_dir = get_chaoxing_export_dir()
        chaoxing_export_dir.mkdir(parents=True, exist_ok=True)
        lesson_part = safe_export_part(lesson.lesson_code, str(lesson.id))
        filename = f"lesson_{lesson.id}_{lesson_part}_diagnostic_probe.xlsx"
        output_path = chaoxing_export_dir / filename
        write_chaoxing_template_xlsx(lesson, draft, output_path)
        redirect_to = sanitize_next_path(return_to) or f"/lessons/{lesson.id}/drafts"
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

    return router
