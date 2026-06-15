"""课次资料整理、上传与删除相关路由。"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from os import SEEK_END, SEEK_SET
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.models.knowledge_outline import KnowledgeOutline
from app.models.lesson import Lesson, LessonMaterial
from app.models.lesson_draft import LessonDraft
from app.services.lesson_materials.document_text_extractor import (
    LessonMaterialExtractionError,
    SUPPORTED_MATERIAL_SUFFIXES,
    extract_text_from_lesson_material,
)
from app.services.teaching_prep_reference_service import TEACHING_PREP_REFERENCE_DRAFT_TYPE

SanitizeNextPath = Callable[[str | None], str | None]
ResolveReturnToPath = Callable[[str | None, str], tuple[str, bool]]
GetLatestKnowledgeOutline = Callable[[Session, int], KnowledgeOutline | None]
GetLessonDraftByType = Callable[[Session, int, str], LessonDraft | None]
GetUploadDir = Callable[[], Path]
MaterialCategoryLabel = Callable[[LessonMaterial], str]

MAX_LESSON_MATERIAL_UPLOAD_BYTES = 50 * 1024 * 1024
LESSON_MATERIAL_UPLOAD_TOO_LARGE_MESSAGE = "文件过大，请拆分资料后上传。"
UPLOAD_SIZE_CHECK_CHUNK_BYTES = 1024 * 1024


async def _is_lesson_material_upload_too_large(uploaded_file: UploadFile) -> bool:
    """检查上传大小，并把文件指针恢复到开头。"""

    try:
        uploaded_file.file.seek(0, SEEK_END)
        size = uploaded_file.file.tell()
        uploaded_file.file.seek(0, SEEK_SET)
        await uploaded_file.seek(0)
        return size > MAX_LESSON_MATERIAL_UPLOAD_BYTES
    except (AttributeError, OSError):
        total_size = 0
        await uploaded_file.seek(0)
        while True:
            chunk = await uploaded_file.read(UPLOAD_SIZE_CHECK_CHUNK_BYTES)
            if not chunk:
                break
            total_size += len(chunk)
            if total_size > MAX_LESSON_MATERIAL_UPLOAD_BYTES:
                await uploaded_file.seek(0)
                return True
        await uploaded_file.seek(0)
        return False


def create_materials_router(
    templates: Jinja2Templates,
    sanitize_next_path: SanitizeNextPath,
    resolve_return_to_path: ResolveReturnToPath,
    get_latest_knowledge_outline: GetLatestKnowledgeOutline,
    get_lesson_draft_by_type: GetLessonDraftByType,
    get_lesson_material_upload_dir: GetUploadDir,
    material_type_labels: Mapping[str, str],
    lesson_status_labels: Mapping[str, str],
    knowledge_outline_status_labels: Mapping[str, str],
    lesson_draft_status_labels: Mapping[str, str],
    default_material_title_labels: Mapping[str, str],
    material_category_options: Sequence[tuple[str, str]],
    material_category_label: MaterialCategoryLabel,
) -> APIRouter:
    """创建课次资料路由，复用 main.py 中已有公共依赖。"""

    router = APIRouter()

    def _lesson_material_title_prefix(lesson: Lesson) -> str:
        """生成资料标题前缀，优先使用课次编码。"""

        return lesson.lesson_code or f"课次{lesson.id}"

    def _generate_lesson_material_title(
        db: Session,
        lesson: Lesson,
        material_type: str,
        requested_title: str | None = None,
    ) -> str:
        """生成不重复的课次资料标题。"""

        requested_title = (requested_title or "").strip()
        if requested_title:
            base_title = requested_title
        else:
            label = default_material_title_labels.get(material_type, "资料")
            base_title = f"{_lesson_material_title_prefix(lesson)}-{label}"

        existing_titles = set(
            db.scalars(select(LessonMaterial.title).where(LessonMaterial.lesson_id == lesson.id)).all()
        )
        if base_title not in existing_titles:
            return base_title

        index = 2
        while f"{base_title}（{index}）" in existing_titles:
            index += 1
        return f"{base_title}（{index}）"

    def _lesson_material_context(db: Session, lesson: Lesson, error_message: str | None = None) -> dict[str, object]:
        """构造课次材料页面上下文。"""

        materials = db.scalars(
            select(LessonMaterial)
            .where(LessonMaterial.lesson_id == lesson.id)
            .order_by(LessonMaterial.id.desc())
        ).all()
        knowledge_outline = get_latest_knowledge_outline(db, lesson.id)
        return {
            "lesson": lesson,
            "materials": materials,
            "error_message": error_message,
            "material_type_labels": material_type_labels,
            "material_category_options": material_category_options,
            "material_category_label": material_category_label,
            "lesson_status_labels": lesson_status_labels,
            "knowledge_outline": knowledge_outline,
            "knowledge_outline_status_labels": knowledge_outline_status_labels,
            "teaching_prep_reference": get_lesson_draft_by_type(
                db,
                lesson.id,
                TEACHING_PREP_REFERENCE_DRAFT_TYPE,
            ),
            "draft_status_labels": lesson_draft_status_labels,
        }

    def _lesson_material_error_response(
        request: Request,
        db: Session,
        lesson: Lesson,
        error_message: str,
        redirect_to: str,
    ) -> HTMLResponse:
        """按来源页面渲染课次资料错误提示。"""

        template_name = (
            "lesson_materials_outline_v2.html"
            if redirect_to.split("?", 1)[0] == f"/ui-v2/lessons/{lesson.id}/materials-outline"
            else "lesson_detail.html"
        )
        return templates.TemplateResponse(
            request,
            template_name,
            _lesson_material_context(db, lesson, error_message),
            status_code=400,
        )

    @router.get("/ui-v2/lessons/{lesson_id}/materials-outline", response_class=HTMLResponse)
    async def show_lesson_materials_outline_v2(
        lesson_id: int,
        request: Request,
        db: Session = Depends(get_db),
    ) -> HTMLResponse:
        """课次资料与知识主干 V2 preview。"""

        lesson = db.scalar(
            select(Lesson)
            .options(selectinload(Lesson.course))
            .where(Lesson.id == lesson_id)
        )
        if lesson is None:
            raise HTTPException(status_code=404, detail="课次不存在")

        materials = db.scalars(
            select(LessonMaterial)
            .where(LessonMaterial.lesson_id == lesson.id)
            .order_by(LessonMaterial.id.desc())
        ).all()
        knowledge_outline = get_latest_knowledge_outline(db, lesson.id)
        teaching_prep_reference = get_lesson_draft_by_type(db, lesson.id, TEACHING_PREP_REFERENCE_DRAFT_TYPE)
        return templates.TemplateResponse(
            request,
            "lesson_materials_outline_v2.html",
            {
                "lesson": lesson,
                "materials": materials,
                "knowledge_outline": knowledge_outline,
                "material_type_labels": material_type_labels,
                "material_category_options": material_category_options,
                "material_category_label": material_category_label,
                "knowledge_outline_status_labels": knowledge_outline_status_labels,
                "teaching_prep_reference": teaching_prep_reference,
                "draft_status_labels": lesson_draft_status_labels,
            },
        )

    @router.post("/lessons/{lesson_id}/materials", response_class=HTMLResponse)
    async def add_lesson_material(
        lesson_id: int,
        request: Request,
        title: str = Form(""),
        material_type: str = Form("pasted_text"),
        input_mode: str = Form(""),
        material_category: str = Form(""),
        content: str = Form(""),
        return_to: str = Form(""),
        files: list[UploadFile] | None = File(None),
        db: Session = Depends(get_db),
    ) -> Response:
        """为课次添加教学材料，支持粘贴文本和多文件上传。"""

        redirect_to, _return_to_invalid = resolve_return_to_path(return_to, f"/lessons/{lesson_id}")
        lesson = db.get(Lesson, lesson_id)
        if lesson is None:
            raise HTTPException(status_code=404, detail="课次不存在")

        title_text = title.strip()
        effective_material_type = material_category.strip() or material_type
        if effective_material_type not in material_type_labels:
            effective_material_type = "supplementary"
        uploaded_files = [uploaded_file for uploaded_file in (files or []) if uploaded_file.filename]
        is_pasted_text = input_mode == "pasted_text" or (not input_mode and material_type == "pasted_text")
        if is_pasted_text:
            material_content = content.strip()
            if not material_content:
                return _lesson_material_error_response(
                    request,
                    db,
                    lesson,
                    "请选择“粘贴文本”并填写文本内容。",
                    redirect_to,
                )
            material = LessonMaterial(
                lesson_id=lesson.id,
                material_type=effective_material_type,
                title=_generate_lesson_material_title(db, lesson, effective_material_type, title_text),
                content=material_content,
                file_path=None,
            )
            db.add(material)
            db.commit()
            return RedirectResponse(url=redirect_to, status_code=303)

        if not uploaded_files:
            return _lesson_material_error_response(
                request,
                db,
                lesson,
                "请选择一个或多个 .txt / .md / .docx / .pptx / .xlsx 文件；暂不支持 .xls。",
                redirect_to,
            )

        lesson_material_upload_dir = get_lesson_material_upload_dir()
        lesson_material_upload_dir.mkdir(parents=True, exist_ok=True)
        errors: list[str] = []
        created_count = 0
        multiple_files = len(uploaded_files) > 1
        for uploaded_file in uploaded_files:
            safe_filename = Path(uploaded_file.filename or "lesson-material").name
            suffix = Path(safe_filename).suffix.lower()
            if suffix == ".xls":
                errors.append(f"{safe_filename}：暂不支持旧版 .xls 表格文件。请另存为 .xlsx 后上传，或复制表格内容粘贴到文本框。")
                continue
            if suffix not in SUPPORTED_MATERIAL_SUFFIXES:
                errors.append(f"{safe_filename}：暂不支持该文件类型。请上传 .txt / .md / .docx / .pptx / .xlsx；不支持 .xls、PDF、图片、扫描件和旧版 .doc / .ppt。")
                continue
            if await _is_lesson_material_upload_too_large(uploaded_file):
                errors.append(f"{safe_filename}：{LESSON_MATERIAL_UPLOAD_TOO_LARGE_MESSAGE}")
                continue

            saved_path = lesson_material_upload_dir / f"{uuid4().hex}-{safe_filename}"
            # 文件材料保存到运行时目录；目录由 .gitignore 排除，不进入公开仓库。
            file_bytes = await uploaded_file.read()
            saved_path.write_bytes(file_bytes)
            try:
                file_content = extract_text_from_lesson_material(saved_path, safe_filename)
            except LessonMaterialExtractionError as exc:
                errors.append(f"{safe_filename}：{exc} 如果提取结果不完整，请复制文字粘贴到文本框中补充。")
                saved_path.unlink(missing_ok=True)
                continue

            requested_title = f"{title_text} - {safe_filename}" if title_text and multiple_files else title_text
            material = LessonMaterial(
                lesson_id=lesson.id,
                material_type=effective_material_type,
                title=_generate_lesson_material_title(db, lesson, effective_material_type, requested_title),
                content=file_content,
                file_path=str(saved_path),
            )
            db.add(material)
            created_count += 1

        db.commit()
        if errors:
            message = "；".join(errors)
            if created_count:
                message = f"已成功添加 {created_count} 份资料。以下文件未能保存：{message}"
            return _lesson_material_error_response(
                request,
                db,
                lesson,
                message,
                redirect_to,
            )

        return RedirectResponse(url=redirect_to, status_code=303)

    @router.post("/lesson-materials/{material_id}/delete")
    async def delete_lesson_material(
        material_id: int,
        return_to: str = Form(""),
        db: Session = Depends(get_db),
    ) -> RedirectResponse:
        """删除课次教学资料，并尽量删除对应上传文件。"""

        material = db.get(LessonMaterial, material_id)
        if material is None:
            raise HTTPException(status_code=404, detail="资料不存在")

        lesson_id = material.lesson_id
        if material.file_path:
            Path(material.file_path).unlink(missing_ok=True)
        db.delete(material)
        db.commit()
        redirect_to, _return_to_invalid = resolve_return_to_path(return_to, f"/lessons/{lesson_id}")
        return RedirectResponse(url=redirect_to, status_code=303)

    return router
