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
from app.models.lesson import Lesson
from app.models.lesson_draft import LessonDraft


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def inline_threadpool_for_tests(monkeypatch: pytest.MonkeyPatch) -> None:
    """测试中同步执行 service，避免启动真实线程或外部调用。"""

    async def run_inline(func: object, *args: object, **kwargs: object) -> object:
        return func(*args, **kwargs)  # type: ignore[misc]

    monkeypatch.setattr(main, "run_in_threadpool", run_inline)


def _build_test_client(tmp_path: Path) -> tuple[httpx.AsyncClient, sessionmaker[Session]]:
    database_path = tmp_path / "test-draft-isolation.sqlite"
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


def _prepare_lesson_with_outline(session_factory: sessionmaker[Session]) -> None:
    with session_factory() as session:
        course = Course(title="数据库基础", semester="2025-2026-2", status="draft")
        session.add(course)
        session.flush()
        lesson = Lesson(
            course_id=course.id,
            week="1",
            lesson_no="1",
            hours="2",
            lesson_code="0406",
            title="分组查询",
            content_summary="GROUP BY 分组查询。",
            status="draft",
        )
        session.add(lesson)
        session.flush()
        outline = KnowledgeOutline(
            lesson_id=lesson.id,
            ai_raw_output="知识主干：分组查询、结果核验、过程记录和职业规范。",
            edited_content="知识主干：分组查询、结果核验、过程记录和职业规范。",
            status="reviewed",
            generated_by_model="test-model",
        )
        session.add(outline)
        session.commit()


def _insert_draft(session_factory: sessionmaker[Session], draft_type: str, content: str) -> None:
    with session_factory() as session:
        draft = LessonDraft(
            lesson_id=1,
            source_outline_id=1,
            draft_type=draft_type,
            title=f"原有 {draft_type}",
            content=content,
            status="reviewed",
            generated_by="deepseek-v4-pro",
        )
        session.add(draft)
        session.commit()


def _draft_contents(session_factory: sessionmaker[Session]) -> dict[str, str]:
    with session_factory() as session:
        drafts = session.scalars(select(LessonDraft).where(LessonDraft.lesson_id == 1)).all()
        return {draft.draft_type: draft.content for draft in drafts}


@pytest.mark.anyio
async def test_generating_guide_low_does_not_touch_mid_or_high(tmp_path: Path) -> None:
    client, session_factory = _build_test_client(tmp_path)
    try:
        _prepare_lesson_with_outline(session_factory)
        _insert_draft(session_factory, "guide_mid", "原有提升任务包内容")
        _insert_draft(session_factory, "guide_high", "原有拓展挑战包内容")

        response = await client.post("/lessons/1/drafts/generate/guide_low", follow_redirects=False)

        assert response.status_code == 303
        contents = _draft_contents(session_factory)
        assert "基础版导学案" in contents["guide_low"]
        assert contents["guide_mid"] == "原有提升任务包内容"
        assert contents["guide_high"] == "原有拓展挑战包内容"
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_generating_guide_mid_does_not_touch_low_or_high(tmp_path: Path) -> None:
    client, session_factory = _build_test_client(tmp_path)
    try:
        _prepare_lesson_with_outline(session_factory)
        _insert_draft(session_factory, "guide_low", "原有基础版导学案")
        _insert_draft(session_factory, "guide_high", "原有拓展挑战包内容")

        response = await client.post("/lessons/1/drafts/generate/guide_mid", follow_redirects=False)

        assert response.status_code == 303
        contents = _draft_contents(session_factory)
        assert contents["guide_low"] == "原有基础版导学案"
        assert "提升任务包" in contents["guide_mid"]
        assert contents["guide_high"] == "原有拓展挑战包内容"
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_generating_guide_high_does_not_touch_low_or_mid(tmp_path: Path) -> None:
    client, session_factory = _build_test_client(tmp_path)
    try:
        _prepare_lesson_with_outline(session_factory)
        _insert_draft(session_factory, "guide_low", "原有基础版导学案")
        _insert_draft(session_factory, "guide_mid", "原有提升任务包内容")

        response = await client.post("/lessons/1/drafts/generate/guide_high", follow_redirects=False)

        assert response.status_code == 303
        contents = _draft_contents(session_factory)
        assert contents["guide_low"] == "原有基础版导学案"
        assert contents["guide_mid"] == "原有提升任务包内容"
        assert "拓展挑战包" in contents["guide_high"]
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_generating_diagnostic_probe_does_not_touch_guides(tmp_path: Path) -> None:
    client, session_factory = _build_test_client(tmp_path)
    try:
        _prepare_lesson_with_outline(session_factory)
        _insert_draft(session_factory, "guide_low", "原有基础版导学案")
        _insert_draft(session_factory, "guide_mid", "原有提升任务包内容")
        _insert_draft(session_factory, "guide_high", "原有拓展挑战包内容")

        response = await client.post("/lessons/1/drafts/generate/diagnostic_probe", follow_redirects=False)

        assert response.status_code == 303
        contents = _draft_contents(session_factory)
        assert "课前学情测试" in contents["diagnostic_probe"]
        assert contents["guide_low"] == "原有基础版导学案"
        assert contents["guide_mid"] == "原有提升任务包内容"
        assert contents["guide_high"] == "原有拓展挑战包内容"
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()
