from __future__ import annotations

import re
from collections.abc import Generator
from pathlib import Path

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app import main
from app.db.base import create_database_tables
from app.models.course import Course
from app.models.knowledge_outline import KnowledgeOutline
from app.models.lesson import Lesson
from app.models.lesson_draft import LessonDraft


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def _build_test_client(tmp_path: Path) -> tuple[httpx.AsyncClient, sessionmaker[Session]]:
    database_path = tmp_path / "test-learning-guides-v2.sqlite"
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
    transport = httpx.ASGITransport(app=main.app)
    return httpx.AsyncClient(transport=transport, base_url="http://testserver"), session_factory


def _visible_text(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


def _create_lesson(
    session_factory: sessionmaker[Session],
    with_guides: bool = True,
    guide_types: set[str] | None = None,
) -> int:
    with session_factory() as session:
        course = Course(title="传感器应用基础", semester="2025-2026-2", status="draft")
        session.add(course)
        session.flush()
        lesson = Lesson(
            course_id=course.id,
            week="3",
            lesson_no="2",
            hours="2",
            lesson_code="0302",
            title="光敏传感器实验",
            content_summary="认识光敏传感器并完成基础实验。",
            homework_hint="整理实验现象。",
            status="draft",
        )
        session.add(lesson)
        session.flush()
        outline = KnowledgeOutline(
            lesson_id=lesson.id,
            ai_raw_output="知识主干草稿",
            edited_content="知识主干草稿",
            status="reviewed",
            generated_by_model="local-structured-draft",
        )
        session.add(outline)
        session.flush()
        selected_guide_types = guide_types if guide_types is not None else {"guide_low", "guide_mid", "guide_high"}
        if with_guides:
            for draft_type, title in [
                ("guide_low", "光敏传感器实验｜全班通用导学案"),
                ("guide_mid", "光敏传感器实验｜巩固提升任务包"),
                ("guide_high", "光敏传感器实验｜拓展探究任务包"),
            ]:
                if draft_type not in selected_guide_types:
                    continue
                session.add(
                    LessonDraft(
                        lesson_id=lesson.id,
                        source_outline_id=outline.id,
                        draft_type=draft_type,
                        title=title,
                        content=f"# {title}\n\n教师可审阅、修改后使用。",
                        status="draft",
                        generated_by="local-structured-draft",
                    )
                )
        session.commit()
        return lesson.id


@pytest.mark.anyio
async def test_learning_guides_v2_page_renders_generation_and_editing_sections(tmp_path: Path) -> None:
    client, session_factory = _build_test_client(tmp_path)
    lesson_id = _create_lesson(session_factory, with_guides=True)
    try:
        response = await client.get(f"/ui-v2/lessons/{lesson_id}/learning-guides")

        assert response.status_code == 200
        text = response.text
        visible = _visible_text(text)
        assert "智学导评 V0.2" in text
        assert "学生导学案" in visible
        assert "课程资料整理" in visible
        assert "整理资料，形成知识主干与备课参考" in visible
        assert "课前学情测试" in visible
        assert "了解学生课前基础" in visible
        assert "形成学生学习单与任务包" in visible
        assert "全班通用导学案" in visible
        assert "基础版导学案" in visible
        assert "巩固提升任务包" in visible
        assert "拓展探究任务包" in visible
        assert "不会自动发布给学生" in visible
        assert "巩固提升与拓展探究任务包为可选补充" in visible
        assert 'class="course-note-v2"' in text
        assert "deepseek-v4-pro" in text
        assert "flash 模型时可能因响应较慢回退为本地结构化草稿" in text
        assert 'class="task-pack-model-note-v2 course-note-v2"' in text
        assert "自动评分" not in visible
        assert "学生端" not in visible
        assert "主文档" in visible
        assert "可选补充" in visible
        assert "可选挑战" in visible
        assert f'action="/lessons/{lesson_id}/drafts/generate/guide_low"' in text
        assert f'action="/lessons/{lesson_id}/drafts/generate/guide_mid"' in text
        assert f'action="/lessons/{lesson_id}/drafts/generate/guide_high"' in text
        assert 'data-status-target="learning-core-status"' in text
        assert 'data-status-target="learning-enhancement-status"' in text
        assert 'data-status-target="learning-extension-status"' in text
        assert "AI 正在生成全班通用导学案，请稍候……生成内容为草稿，需教师审阅、修改与确认。" in text
        assert "AI 正在生成巩固提升任务包，请稍候……生成内容为可选补充，需教师审阅、修改与确认。" in text
        assert "AI 正在生成拓展探究任务包，请稍候……生成内容为可选挑战，需教师审阅、修改与确认。" in text
        assert "查看 / 编辑" not in text
        assert "保存教师修改" in visible
        assert "下载 Markdown" in visible
        assert "下载 DOCX" in visible
        assert f"/ui-v2/lessons/{lesson_id}/diagnostic-probe" in text
        assert f"/ui-v2/lessons/{lesson_id}/materials-outline" in text
        assert f"/lessons/{lesson_id}/drafts/" in text
        assert "/download-docx" in text
        for forbidden in ["guide_low", "guide_mid", "guide_high", " low ", " mid ", " high "]:
            assert forbidden not in visible
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_learning_guides_v2_empty_state_and_legacy_drafts_page_still_work(tmp_path: Path) -> None:
    client, session_factory = _build_test_client(tmp_path)
    lesson_id = _create_lesson(session_factory, with_guides=False)
    try:
        v2_response = await client.get(f"/ui-v2/lessons/{lesson_id}/learning-guides")
        legacy_response = await client.get(f"/lessons/{lesson_id}/drafts")

        assert v2_response.status_code == 200
        assert "当前还没有学生导学案草稿" in v2_response.text
        assert "生成全班通用导学案" in v2_response.text
        assert legacy_response.status_code == 200
        assert "课前学情与学生导学案" in legacy_response.text
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_learning_guides_v2_entry_links_from_lessons_and_diagnostic_pages(tmp_path: Path) -> None:
    client, session_factory = _build_test_client(tmp_path)
    lesson_id = _create_lesson(session_factory, with_guides=True)
    with session_factory() as session:
        lesson = session.get(Lesson, lesson_id)
        assert lesson is not None
        course_id = lesson.course_id
    try:
        lessons_response = await client.get(f"/courses/{course_id}/lessons")
        diagnostic_response = await client.get(f"/ui-v2/lessons/{lesson_id}/diagnostic-probe")

        assert lessons_response.status_code == 200
        assert "导学案" in lessons_response.text
        assert f"/ui-v2/lessons/{lesson_id}/learning-guides" in lessons_response.text
        assert diagnostic_response.status_code == 200
        assert "进入学生导学案" in diagnostic_response.text
        assert f"/ui-v2/lessons/{lesson_id}/learning-guides" in diagnostic_response.text
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_learning_guides_v2_disables_task_packs_until_dependencies_exist(tmp_path: Path) -> None:
    client, session_factory = _build_test_client(tmp_path)
    lesson_id = _create_lesson(session_factory, with_guides=False)
    try:
        response = await client.get(f"/ui-v2/lessons/{lesson_id}/learning-guides")

        assert response.status_code == 200
        assert "请先生成全班通用导学案，再生成巩固提升任务包" in response.text
        assert "请先生成巩固提升任务包，再生成拓展探究任务包" in response.text
        assert 'title="请先生成全班通用导学案"' in response.text
        assert 'title="请先生成巩固提升任务包"' in response.text
        assert "查看 / 编辑" not in response.text
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_learning_guides_v2_blocks_mid_and_high_generation_without_dependencies(tmp_path: Path) -> None:
    client, session_factory = _build_test_client(tmp_path)
    lesson_id = _create_lesson(session_factory, with_guides=False)
    return_to = f"/ui-v2/lessons/{lesson_id}/learning-guides"
    try:
        mid_response = await client.post(
            f"/lessons/{lesson_id}/drafts/generate/guide_mid",
            data={"return_to": return_to},
            follow_redirects=False,
        )
        high_response = await client.post(
            f"/lessons/{lesson_id}/drafts/generate/guide_high",
            data={"return_to": return_to},
            follow_redirects=False,
        )

        assert mid_response.status_code == 303
        assert high_response.status_code == 303
        assert mid_response.headers["location"].startswith(f"{return_to}?dependency_message=")
        assert high_response.headers["location"].startswith(f"{return_to}?dependency_message=")
        with session_factory() as session:
            assert session.query(LessonDraft).filter_by(lesson_id=lesson_id, draft_type="guide_mid").first() is None
            assert session.query(LessonDraft).filter_by(lesson_id=lesson_id, draft_type="guide_high").first() is None
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_learning_guides_v2_allows_mid_after_low_and_high_after_mid(tmp_path: Path) -> None:
    client, session_factory = _build_test_client(tmp_path)
    lesson_id = _create_lesson(session_factory, with_guides=True, guide_types={"guide_low"})
    return_to = f"/ui-v2/lessons/{lesson_id}/learning-guides"
    try:
        mid_response = await client.post(
            f"/lessons/{lesson_id}/drafts/generate/guide_mid",
            data={"return_to": return_to},
            follow_redirects=False,
        )
        assert mid_response.status_code == 303
        with session_factory() as session:
            assert session.query(LessonDraft).filter_by(lesson_id=lesson_id, draft_type="guide_mid").first() is not None
            assert session.query(LessonDraft).filter_by(lesson_id=lesson_id, draft_type="guide_high").first() is None

        high_response = await client.post(
            f"/lessons/{lesson_id}/drafts/generate/guide_high",
            data={"return_to": return_to},
            follow_redirects=False,
        )
        assert high_response.status_code == 303
        with session_factory() as session:
            assert session.query(LessonDraft).filter_by(lesson_id=lesson_id, draft_type="guide_high").first() is not None
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()
