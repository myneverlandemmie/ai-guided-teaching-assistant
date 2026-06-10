from collections.abc import Generator
from pathlib import Path

import httpx
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app import main
from app.db.base import create_database_tables
from app.models.course import Course
from app.models.knowledge_outline import KnowledgeOutline
from app.models.lesson import Lesson, LessonMaterial
from app.models.lesson_draft import LessonDraft
from app.services.ai.deepseek_client import DeepSeekProviderError
from app.services.ai.fallback import (
    FALLBACK_REASON_MISSING_API_KEY,
    FALLBACK_REASON_PROVIDER_ERROR,
    MISSING_API_KEY_FALLBACK_MESSAGE,
    PROVIDER_ERROR_FALLBACK_MESSAGE,
)
from app.services.teaching_prep_reference_service import TEACHING_PREP_REFERENCE_DRAFT_TYPE

PROMPT_PATH = Path(__file__).resolve().parents[2] / "docs" / "prompts" / "teaching-prep-reference-suggestions-v0.1.md"


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def _build_test_client(tmp_path: Path) -> tuple[httpx.AsyncClient, sessionmaker[Session]]:
    database_path = tmp_path / "test-teaching-prep-reference.sqlite"
    engine = create_engine(
        f"sqlite+pysqlite:///{database_path}",
        connect_args={"check_same_thread": False},
        future=True,
    )
    create_database_tables(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    async def override_get_db() -> Generator[Session, None, None]:
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    main.app.dependency_overrides[main.get_db] = override_get_db
    main.GUIDE_EXPORT_DIR = tmp_path / "exports" / "guides"
    transport = httpx.ASGITransport(app=main.app)
    return httpx.AsyncClient(transport=transport, base_url="http://testserver"), session_factory


def _create_lesson(session_factory: sessionmaker[Session], with_reference: bool = False) -> int:
    with session_factory() as session:
        course = Course(title="传感器应用基础", semester="2025-2026-2", status="draft")
        session.add(course)
        session.flush()
        lesson = Lesson(
            course_id=course.id,
            week="4",
            lesson_no="1",
            hours="2",
            lesson_code="0401",
            title="光敏传感器数据采集",
            content_summary="完成光敏传感器基础连接、观察和记录。",
            homework_hint="整理实验记录。",
            status="draft",
        )
        session.add(lesson)
        session.flush()
        material = LessonMaterial(
            lesson_id=lesson.id,
            material_type="pasted_text",
            title="实训步骤",
            content="教学目标：认识光敏传感器。实训步骤：连接模块、观察输入信号和输出信号。安全规范：断电接线。",
        )
        outline = KnowledgeOutline(
            lesson_id=lesson.id,
            ai_raw_output="知识主干：光敏传感器、静态记录、实验步骤、安全规范。",
            edited_content="知识主干：光敏传感器、静态记录、实验步骤、安全规范。",
            status="reviewed",
            generated_by_model="local-structured-draft",
        )
        session.add_all([material, outline])
        if with_reference:
            session.add(
                LessonDraft(
                    lesson_id=lesson.id,
                    source_outline_id=outline.id,
                    draft_type=TEACHING_PREP_REFERENCE_DRAFT_TYPE,
                    title="原有备课参考建议",
                    content="原有建议内容",
                    status="draft",
                    generated_by="local-structured-draft",
                )
            )
        session.commit()
        return lesson.id


def test_teaching_prep_reference_prompt_document_exists_and_keeps_boundary() -> None:
    assert PROMPT_PATH.exists()
    content = PROMPT_PATH.read_text(encoding="utf-8")
    headings = [line.strip("# ") for line in content.splitlines() if line.startswith("#")]

    assert "备课参考建议" in content
    assert "教师确认声明" in content
    assert "标准 Markdown" in content
    assert "## 一、材料概况" in content
    assert "## 八、教师确认声明" in content
    assert all("教案诊断" not in heading for heading in headings)
    assert all("AI 自动备课" not in heading for heading in headings)
    assert all("一键生成教案" not in heading for heading in headings)


@pytest.mark.anyio
async def test_materials_outline_v2_shows_teaching_prep_reference_entry(tmp_path: Path) -> None:
    client, session_factory = _build_test_client(tmp_path)
    lesson_id = _create_lesson(session_factory)
    try:
        response = await client.get(f"/ui-v2/lessons/{lesson_id}/materials-outline")

        assert response.status_code == 200
        assert "备课参考建议" in response.text
        assert "生成备课参考建议" in response.text
        assert "供教师选择性参考" in response.text
        assert "本建议参考公开课、汇报课、教学能力比赛等较高标准材料的常见结构" in response.text
        assert "整理资料，形成知识主干与备课参考。" in response.text
        assert "完成资料整理、知识主干确认和备课参考建议查看后" in response.text
        assert 'data-status-target="teaching-prep-reference-generation-hint"' in response.text
        assert "AI 正在生成备课参考建议" in response.text
        assert "教案诊断" not in response.text
        assert "自动备课" not in response.text
        assert "一键生成教案" not in response.text
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_generate_teaching_prep_reference_without_api_key_uses_local_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, session_factory = _build_test_client(tmp_path)
    lesson_id = _create_lesson(session_factory)
    return_to = f"/ui-v2/lessons/{lesson_id}/materials-outline"

    async def run_inline(func: object, *args: object, **kwargs: object) -> object:
        return func(*args, **kwargs)  # type: ignore[misc]

    monkeypatch.setattr(main, "run_in_threadpool", run_inline)
    try:
        response = await client.post(
            f"/lessons/{lesson_id}/drafts/generate/teaching_prep_reference",
            data={"return_to": return_to},
            follow_redirects=False,
        )

        assert response.status_code == 303
        assert response.headers["location"] == f"{return_to}?ai_fallback_reason={FALLBACK_REASON_MISSING_API_KEY}"
        with session_factory() as session:
            draft = session.scalar(
                select(LessonDraft).where(
                    LessonDraft.lesson_id == lesson_id,
                    LessonDraft.draft_type == TEACHING_PREP_REFERENCE_DRAFT_TYPE,
                )
            )
            assert draft is not None
            assert draft.generated_by == "local-structured-draft"
            assert "以下为基于现有材料的本地结构化参考建议" in draft.content
            for section in ["材料概况", "已有亮点", "可能遗漏", "教学环节参考", "导学案生成提示", "课前学情测试提示", "评价参考", "教师确认声明"]:
                assert section in draft.content
        page = await client.get(response.headers["location"])
        assert page.status_code == 200
        assert MISSING_API_KEY_FALLBACK_MESSAGE in page.text
        assert f'<p class="notice ai-fallback-notice">{MISSING_API_KEY_FALLBACK_MESSAGE}</p>' in page.text
        assert f'<p class="alert">{MISSING_API_KEY_FALLBACK_MESSAGE}</p>' not in page.text
        assert "Traceback" not in page.text
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_generate_teaching_prep_reference_provider_error_shows_friendly_message(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, session_factory = _build_test_client(tmp_path)
    lesson_id = _create_lesson(session_factory)
    return_to = f"/ui-v2/lessons/{lesson_id}/materials-outline"

    async def run_inline(func: object, *args: object, **kwargs: object) -> object:
        return func(*args, **kwargs)  # type: ignore[misc]

    def fail_call(*args: object, **kwargs: object) -> tuple[str, str]:
        raise DeepSeekProviderError("底层异常：DeepSeek 连接失败")

    monkeypatch.setattr(main, "run_in_threadpool", run_inline)
    monkeypatch.setattr("app.services.teaching_prep_reference_service._call_deepseek_teaching_prep_reference", fail_call)
    try:
        await client.post(
            "/ai/settings",
            data={"api_key": "sk-teaching-prep-error-1234", "selected_model": "deepseek-v4-flash"},
            headers={"origin": "http://testserver"},
        )

        response = await client.post(
            f"/lessons/{lesson_id}/drafts/generate/teaching_prep_reference",
            data={"return_to": return_to},
            follow_redirects=False,
        )

        assert response.status_code == 303
        assert response.headers["location"] == f"{return_to}?ai_fallback_reason={FALLBACK_REASON_PROVIDER_ERROR}"
        with session_factory() as session:
            draft = session.scalar(
                select(LessonDraft).where(
                    LessonDraft.lesson_id == lesson_id,
                    LessonDraft.draft_type == TEACHING_PREP_REFERENCE_DRAFT_TYPE,
                )
            )
            assert draft is not None
            assert draft.generated_by == "local-structured-draft"
            assert "以下为基于现有材料的本地结构化参考建议" in draft.content
        page = await client.get(response.headers["location"])
        assert page.status_code == 200
        assert PROVIDER_ERROR_FALLBACK_MESSAGE in page.text
        assert f'<p class="notice ai-fallback-notice">{PROVIDER_ERROR_FALLBACK_MESSAGE}</p>' in page.text
        assert f'<p class="alert">{PROVIDER_ERROR_FALLBACK_MESSAGE}</p>' not in page.text
        assert "底层异常" not in page.text
        assert "DeepSeek 连接失败" not in page.text
        assert "Traceback" not in page.text
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_generate_teaching_prep_reference_ai_success_does_not_show_fallback_message(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, session_factory = _build_test_client(tmp_path)
    lesson_id = _create_lesson(session_factory)
    return_to = f"/ui-v2/lessons/{lesson_id}/materials-outline"
    ai_content = """
## 一、材料概况
AI 已整理材料概况。
## 二、已有亮点
AI 已识别已有亮点。
## 三、可能遗漏
AI 已给出可能遗漏。
## 四、教学环节参考
AI 已给出教学环节参考。
## 五、导学案生成提示
AI 已给出导学案生成提示。
## 六、课前学情测试提示
AI 已给出课前学情测试提示。
## 七、评价参考
AI 已给出评价参考。
## 八、教师确认声明
本建议仅供教师审阅。
""".strip()

    async def run_inline(func: object, *args: object, **kwargs: object) -> object:
        return func(*args, **kwargs)  # type: ignore[misc]

    def fake_call(*args: object, **kwargs: object) -> tuple[str, str]:
        return ai_content, "deepseek-v4-flash"

    monkeypatch.setattr(main, "run_in_threadpool", run_inline)
    monkeypatch.setattr("app.services.teaching_prep_reference_service._call_deepseek_teaching_prep_reference", fake_call)
    try:
        await client.post(
            "/ai/settings",
            data={"api_key": "sk-teaching-prep-success-1234", "selected_model": "deepseek-v4-flash"},
            headers={"origin": "http://testserver"},
        )

        response = await client.post(
            f"/lessons/{lesson_id}/drafts/generate/teaching_prep_reference",
            data={"return_to": return_to},
            follow_redirects=False,
        )

        assert response.status_code == 303
        assert response.headers["location"] == return_to
        with session_factory() as session:
            draft = session.scalar(
                select(LessonDraft).where(
                    LessonDraft.lesson_id == lesson_id,
                    LessonDraft.draft_type == TEACHING_PREP_REFERENCE_DRAFT_TYPE,
                )
            )
            assert draft is not None
            assert draft.generated_by == "deepseek-v4-flash"
            assert "AI 已整理材料概况" in draft.content
        page = await client.get(response.headers["location"])
        assert page.status_code == 200
        assert MISSING_API_KEY_FALLBACK_MESSAGE not in page.text
        assert PROVIDER_ERROR_FALLBACK_MESSAGE not in page.text
        assert "ai-fallback-notice" not in page.text
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_teaching_prep_reference_can_be_displayed_and_saved(tmp_path: Path) -> None:
    client, session_factory = _build_test_client(tmp_path)
    lesson_id = _create_lesson(session_factory, with_reference=True)
    return_to = f"/ui-v2/lessons/{lesson_id}/materials-outline"
    with session_factory() as session:
        draft = session.scalar(
            select(LessonDraft).where(
                LessonDraft.lesson_id == lesson_id,
                LessonDraft.draft_type == TEACHING_PREP_REFERENCE_DRAFT_TYPE,
            )
        )
        assert draft is not None
        draft_id = draft.id

    try:
        page = await client.get(return_to)
        assert page.status_code == 200
        assert "原有备课参考建议" in page.text
        assert "原有建议内容" in page.text
        assert "下载 Markdown" in page.text
        assert "下载 DOCX" in page.text
        assert f"/lessons/{lesson_id}/drafts/{draft_id}/download-md" in page.text
        assert f"/lessons/{lesson_id}/drafts/{draft_id}/download-docx" in page.text

        response = await client.post(
            f"/lessons/{lesson_id}/drafts/{draft_id}/save",
            data={"title": "教师修改后的备课参考建议", "content": "教师修改后的建议内容", "return_to": return_to},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"] == return_to
        with session_factory() as session:
            saved = session.get(LessonDraft, draft_id)
            assert saved is not None
            assert saved.title == "教师修改后的备课参考建议"
            assert saved.content == "教师修改后的建议内容"
            assert saved.status == "reviewed"
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_teaching_prep_reference_markdown_download_uses_friendly_filename(tmp_path: Path) -> None:
    client, session_factory = _build_test_client(tmp_path)
    lesson_id = _create_lesson(session_factory, with_reference=True)
    with session_factory() as session:
        draft = session.scalar(
            select(LessonDraft).where(
                LessonDraft.lesson_id == lesson_id,
                LessonDraft.draft_type == TEACHING_PREP_REFERENCE_DRAFT_TYPE,
            )
        )
        assert draft is not None
        draft_id = draft.id

    try:
        response = await client.get(f"/lessons/{lesson_id}/drafts/{draft_id}/download-md")

        assert response.status_code == 200
        content_disposition = response.headers["content-disposition"]
        assert "teaching_prep_reference_suggestions.md" in content_disposition
        assert "原有建议内容" in response.text
        exported_files = list(main.GUIDE_EXPORT_DIR.glob("*teaching_prep_reference_suggestions.md"))
        assert len(exported_files) == 1
        assert exported_files[0].read_text(encoding="utf-8") == "原有建议内容"
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


def test_teaching_prep_reference_draft_type_does_not_replace_existing_types(tmp_path: Path) -> None:
    _, session_factory = _build_test_client(tmp_path)
    lesson_id = _create_lesson(session_factory)
    with session_factory() as session:
        outline = session.scalar(select(KnowledgeOutline).where(KnowledgeOutline.lesson_id == lesson_id))
        assert outline is not None
        session.add_all(
            [
                LessonDraft(lesson_id=lesson_id, source_outline_id=outline.id, draft_type="diagnostic_probe", title="前测", content="前测内容"),
                LessonDraft(lesson_id=lesson_id, source_outline_id=outline.id, draft_type="guide_low", title="基础", content="基础内容"),
                LessonDraft(lesson_id=lesson_id, source_outline_id=outline.id, draft_type="guide_mid", title="提升", content="提升内容"),
                LessonDraft(lesson_id=lesson_id, source_outline_id=outline.id, draft_type="guide_high", title="拓展", content="拓展内容"),
                LessonDraft(lesson_id=lesson_id, source_outline_id=outline.id, draft_type=TEACHING_PREP_REFERENCE_DRAFT_TYPE, title="参考", content="参考内容"),
            ]
        )
        session.commit()
        draft_types = set(session.scalars(select(LessonDraft.draft_type).where(LessonDraft.lesson_id == lesson_id)).all())

    assert draft_types == {"diagnostic_probe", "guide_low", "guide_mid", "guide_high", TEACHING_PREP_REFERENCE_DRAFT_TYPE}
    main.app.dependency_overrides.clear()
