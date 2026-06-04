"""智学导评 V0.2 后端入口。"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import quote, urlparse

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.db.base import create_database_tables
from app.db.session import engine, get_db
from app.models.knowledge_outline import KnowledgeOutline
from app.models.lesson import Lesson, LessonMaterial
from app.models.lesson_draft import LESSON_DRAFT_TYPES, LessonDraft
from app.routes.ai_settings import create_ai_settings_router
from app.routes.course_plans import create_course_plans_router
from app.routes.courses import create_courses_router
from app.routes.drafts import create_drafts_router
from app.routes.exports import create_exports_router
from app.routes.lessons import create_lessons_router
from app.routes.materials import create_materials_router
from app.routes.outlines import create_outlines_router
from app.services.ai import provider as ai_provider
from app.services.ai.lesson_draft_service import (
    DRAFT_TYPE_LABELS,
    DiagnosticQuestionBlock,
    parse_diagnostic_probe_question_blocks,
)
from app.services.teaching_prep_reference_service import TEACHING_PREP_REFERENCE_DRAFT_TYPE

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
STATIC_DIR = Path(__file__).resolve().parent / "static"
COURSE_PLAN_UPLOAD_DIR = PROJECT_ROOT / "data" / "uploads" / "course-plans"
LESSON_MATERIAL_UPLOAD_DIR = PROJECT_ROOT / "data" / "uploads" / "lesson-materials"
CHAOXING_EXPORT_DIR = PROJECT_ROOT / "data" / "exports" / "chaoxing"
GUIDE_EXPORT_DIR = PROJECT_ROOT / "data" / "exports" / "guides"
MATERIAL_TYPE_LABELS = {
    "pasted_text": "粘贴文本",
    "lesson_plan": "教案",
    "course_ppt": "PPT课件",
    "training_guide": "实训指导书",
    "task_sheet": "任务书 / 学习单",
    "evaluation_sheet": "评价表 / 记录表",
    "supplementary": "补充材料",
    "text": "粘贴文本",
    "ppt_text": "PPT课件",
    "other": "其他",
}
LESSON_STATUS_LABELS = {"draft": "草稿", "published": "已发布", "archived": "已归档"}
KNOWLEDGE_OUTLINE_STATUS_LABELS = {"draft": "草稿", "reviewed": "已复核", "published": "已发布"}
LESSON_DRAFT_STATUS_LABELS = {"draft": "草稿", "reviewed": "已复核"}
LESSON_DRAFT_DOWNLOAD_NAME_PARTS = {
    "guide_low": "core_learning_guide",
    "guide_mid": "enhancement_task_pack",
    "guide_high": "extension_challenge_pack",
    TEACHING_PREP_REFERENCE_DRAFT_TYPE: "teaching_prep_reference_suggestions",
}
DEFAULT_MATERIAL_TITLE_LABELS = {
    "pasted_text": "粘贴文本",
    "lesson_plan": "教案",
    "course_ppt": "PPT课件",
    "training_guide": "实训指导书",
    "task_sheet": "任务书",
    "evaluation_sheet": "评价表",
    "supplementary": "补充材料",
    "other": "其他资料",
}
MATERIAL_CATEGORY_OPTIONS = [
    ("lesson_plan", "教案"),
    ("course_ppt", "PPT / 课件"),
    ("training_guide", "实训指导书"),
    ("task_sheet", "任务书 / 学习单"),
    ("evaluation_sheet", "评价表 / 记录表"),
    ("supplementary", "补充材料"),
    ("other", "其他"),
]


def sanitize_next_path(next_path: str | None) -> str | None:
    """清洗 AI 设置页返回路径，只允许站内相对路径。

    Args:
        next_path: 用户提供的返回路径。

    Returns:
        合法时返回原路径；非法或为空时返回 None。

    Raises:
        不主动抛出业务异常。
    """

    if not next_path:
        return None

    if not next_path.startswith("/") or next_path.startswith("//"):
        return None
    if "\\" in next_path:
        return None
    if any(ord(char) < 32 or ord(char) == 127 for char in next_path):
        return None

    parsed_next = urlparse(next_path)
    if parsed_next.scheme or parsed_next.netloc:
        return None
    return next_path


def require_same_origin(request: Request) -> None:
    """对关键 POST 做最小 same-origin 校验。"""

    source = request.headers.get("origin") or request.headers.get("referer")
    if not source:
        raise HTTPException(status_code=403, detail="出于安全考虑，请从系统页面提交表单。")

    parsed_source = urlparse(source)
    source_host = parsed_source.netloc
    request_host = request.headers.get("host", "")
    request_scheme = request.url.scheme
    if not source_host or source_host != request_host or parsed_source.scheme != request_scheme:
        raise HTTPException(status_code=403, detail="安全校验未通过，请从当前系统页面重新提交。")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """应用生命周期：启动时使用 create_all 初始化默认数据库。"""

    # V0.2 初期不用 Alembic，先用 create_all 支撑本地开发和演示。
    create_database_tables(engine)
    yield


app = FastAPI(title="AI Guided SQL Assessment", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))
templates.env.filters["basename"] = lambda value: Path(value).name if value else ""
templates.env.filters["splitext"] = lambda value: Path(value).suffix.lstrip(".") if value else ""


def _lesson_material_category_label(material: LessonMaterial) -> str:
    """返回教师可见的资料类别。"""

    return MATERIAL_TYPE_LABELS.get(material.material_type, MATERIAL_TYPE_LABELS.get("other", "其他"))


def _get_latest_knowledge_outline(db: Session, lesson_id: int) -> KnowledgeOutline | None:
    """读取课次最新一条知识主干。"""

    return db.scalar(
        select(KnowledgeOutline)
        .where(KnowledgeOutline.lesson_id == lesson_id)
        .order_by(KnowledgeOutline.id.desc())
    )


def _get_lesson_drafts(db: Session, lesson_id: int) -> list[LessonDraft]:
    """读取当前课次全部导学草稿。"""

    return db.scalars(
        select(LessonDraft)
        .where(LessonDraft.lesson_id == lesson_id)
        .order_by(LessonDraft.id)
    ).all()


def _get_lesson_draft_by_type(db: Session, lesson_id: int, draft_type: str) -> LessonDraft | None:
    """读取某课次指定类型草稿。"""

    return db.scalar(
        select(LessonDraft)
        .where(LessonDraft.lesson_id == lesson_id, LessonDraft.draft_type == draft_type)
        .order_by(LessonDraft.id.desc())
    )


def _learning_guide_dependency_message(draft_type: str, has_low: bool, has_mid: bool) -> str | None:
    """返回学生导学案任务包的依赖提示。"""

    if draft_type == "guide_mid" and not has_low:
        return "请先生成全班通用导学案，再生成巩固提升任务包。"
    if draft_type == "guide_high" and not has_mid:
        return "请先生成巩固提升任务包，再生成拓展探究任务包。"
    return None


def _upsert_lesson_drafts(
    db: Session,
    lesson: Lesson,
    outline: KnowledgeOutline | None,
    generated_drafts: list[object],
) -> None:
    """按 lesson_id + draft_type 更新当前草稿，不保留历史版本。"""

    existing_drafts = {
        draft.draft_type: draft
        for draft in db.scalars(select(LessonDraft).where(LessonDraft.lesson_id == lesson.id)).all()
    }
    for generated in generated_drafts:
        if generated.draft_type not in LESSON_DRAFT_TYPES:
            continue
        draft = existing_drafts.get(generated.draft_type)
        if draft is None:
            draft = LessonDraft(
                lesson_id=lesson.id,
                source_outline_id=outline.id if outline else None,
                draft_type=generated.draft_type,
                title=generated.title,
                content=generated.content,
                status="draft",
                generated_by=generated.generated_by,
            )
            db.add(draft)
        else:
            draft.source_outline_id = outline.id if outline else None
            draft.title = generated.title
            draft.content = generated.content
            draft.status = "draft"
            draft.generated_by = generated.generated_by


def _safe_export_part(value: str | None, fallback: str) -> str:
    """生成安全的导出文件名片段。"""

    cleaned = "".join(char for char in (value or "") if char.isalnum() or char in {"-", "_"})
    return cleaned or fallback


def _safe_export_filename(filename: str | None, suffix: str) -> str | None:
    """只允许下载固定导出目录下的简单文件名。"""

    if not filename:
        return None
    basename = Path(filename).name
    if basename != filename or "\\" in filename or not basename.endswith(suffix):
        return None
    return basename


def _append_query_param(path: str, key: str, value: str) -> str:
    """向站内路径追加简单查询参数。"""

    separator = "&" if "?" in path else "?"
    return f"{path}{separator}{key}={quote(value, safe='')}"


def _distribution(items: list[str]) -> list[dict[str, object]]:
    """生成页面使用的轻量分布数据。"""

    counts: dict[str, int] = {}
    for item in items:
        label = item.strip() or "不详"
        if label in {"基础"}:
            label = "易 / 基础"
        elif label in {"中等"}:
            label = "中 / 中等"
        elif label in {"提高"}:
            label = "难 / 提高"
        counts[label] = counts.get(label, 0) + 1
    total = sum(counts.values()) or 1
    return [
        {
            "label": label,
            "count": count,
            "percent": round(count / total * 100),
            "percent_display": f"{count / total * 100:.1f}%",
        }
        for label, count in counts.items()
    ]


def _diagnostic_probe_view_context(draft: LessonDraft | None) -> dict[str, object]:
    """构造课前学情测试 V2 的题卡与结构概览。"""

    question_blocks: list[DiagnosticQuestionBlock] = []
    if draft is not None:
        question_blocks = parse_diagnostic_probe_question_blocks(draft.content)
    return {
        "question_blocks": question_blocks,
        "question_type_distribution": _distribution([block.question.question_type for block in question_blocks]),
        "difficulty_distribution": _distribution([block.question.difficulty for block in question_blocks]),
    }


app.include_router(create_ai_settings_router(templates, sanitize_next_path, require_same_origin))
app.include_router(create_courses_router(templates, sanitize_next_path))
app.include_router(create_course_plans_router(templates, sanitize_next_path, lambda: COURSE_PLAN_UPLOAD_DIR))
app.include_router(
    create_lessons_router(
        templates,
        _get_latest_knowledge_outline,
        MATERIAL_TYPE_LABELS,
        LESSON_STATUS_LABELS,
        KNOWLEDGE_OUTLINE_STATUS_LABELS,
    )
)
app.include_router(
    create_materials_router(
        templates,
        sanitize_next_path,
        _get_latest_knowledge_outline,
        _get_lesson_draft_by_type,
        lambda: LESSON_MATERIAL_UPLOAD_DIR,
        MATERIAL_TYPE_LABELS,
        LESSON_STATUS_LABELS,
        KNOWLEDGE_OUTLINE_STATUS_LABELS,
        LESSON_DRAFT_STATUS_LABELS,
        DEFAULT_MATERIAL_TITLE_LABELS,
        MATERIAL_CATEGORY_OPTIONS,
        _lesson_material_category_label,
    )
)
app.include_router(
    create_outlines_router(
        templates,
        sanitize_next_path,
        require_same_origin,
        lambda func, *args, **kwargs: run_in_threadpool(func, *args, **kwargs),
        _get_latest_knowledge_outline,
        _get_lesson_draft_by_type,
        MATERIAL_TYPE_LABELS,
        KNOWLEDGE_OUTLINE_STATUS_LABELS,
        LESSON_DRAFT_STATUS_LABELS,
        MATERIAL_CATEGORY_OPTIONS,
        _lesson_material_category_label,
    )
)
app.include_router(
    create_drafts_router(
        templates,
        sanitize_next_path,
        lambda func, *args, **kwargs: run_in_threadpool(func, *args, **kwargs),
        _get_latest_knowledge_outline,
        _get_lesson_drafts,
        _get_lesson_draft_by_type,
        _learning_guide_dependency_message,
        _upsert_lesson_drafts,
        _safe_export_filename,
        _append_query_param,
        _diagnostic_probe_view_context,
        DRAFT_TYPE_LABELS,
        LESSON_DRAFT_STATUS_LABELS,
    )
)
app.include_router(
    create_exports_router(
        sanitize_next_path,
        _safe_export_part,
        _safe_export_filename,
        _append_query_param,
        lambda: CHAOXING_EXPORT_DIR,
        lambda: GUIDE_EXPORT_DIR,
        LESSON_DRAFT_DOWNLOAD_NAME_PARTS,
        TEACHING_PREP_REFERENCE_DRAFT_TYPE,
    )
)
