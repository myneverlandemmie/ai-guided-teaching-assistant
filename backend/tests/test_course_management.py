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


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def _build_test_client(tmp_path: Path) -> tuple[httpx.AsyncClient, sessionmaker[Session]]:
    database_path = tmp_path / "test-course-management.sqlite"
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


@pytest.mark.anyio
async def test_empty_database_creates_default_test_course(tmp_path: Path) -> None:
    client, session_factory = _build_test_client(tmp_path)
    try:
        response = await client.get("/courses")

        assert response.status_code == 200
        assert "测试课程" in response.text
        assert "数据库应用与数据分析" not in response.text
        assert "上传授课计划" in response.text
        assert "查看正式课次" in response.text
        with session_factory() as session:
            course = session.scalar(select(Course))
            assert course is not None
            assert course.title == "测试课程"
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_create_course_and_show_on_courses_page(tmp_path: Path) -> None:
    client, session_factory = _build_test_client(tmp_path)
    try:
        response = await client.post("/courses/create", data={"title": "Python 程序设计"})

        assert response.status_code == 303
        assert response.headers["location"] == "/courses"
        page = await client.get("/courses")
        assert "Python 程序设计" in page.text
        assert "/course-plan/upload" in page.text
        assert "查看正式课次" in page.text
        with session_factory() as session:
            assert session.scalar(select(Course).where(Course.title == "Python 程序设计")) is not None
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_create_course_rejects_empty_title(tmp_path: Path) -> None:
    client, session_factory = _build_test_client(tmp_path)
    try:
        response = await client.post("/courses/create", data={"title": "   "})

        assert response.status_code == 400
        assert "课程名称不能为空" in response.text
        with session_factory() as session:
            assert session.scalars(select(Course)).all() == []
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_rename_course_keeps_course_and_lesson_entry(tmp_path: Path) -> None:
    client, session_factory = _build_test_client(tmp_path)
    with session_factory() as session:
        course = Course(title="测试课程", semester="2025-2026-2", status="draft")
        session.add(course)
        session.commit()
        course_id = course.id

    try:
        response = await client.post(f"/courses/{course_id}/rename", data={"title": "电子技术基础"})

        assert response.status_code == 303
        page = await client.get("/courses")
        assert "电子技术基础" in page.text
        assert f"/courses/{course_id}/lessons" in page.text
        with session_factory() as session:
            course = session.get(Course, course_id)
            assert course is not None
            assert course.title == "电子技术基础"
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_delete_empty_course_removes_it_from_courses_page(tmp_path: Path) -> None:
    client, session_factory = _build_test_client(tmp_path)
    with session_factory() as session:
        course = Course(title="待删除课程", semester="2025-2026-2", status="draft")
        session.add(course)
        session.commit()
        course_id = course.id

    try:
        response = await client.post(f"/courses/{course_id}/delete")

        assert response.status_code == 303
        with session_factory() as session:
            assert session.get(Course, course_id) is None
        page = await client.get("/courses")
        assert "待删除课程" not in page.text
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_delete_course_cascades_lessons_materials_outlines_and_drafts(tmp_path: Path) -> None:
    client, session_factory = _build_test_client(tmp_path)
    with session_factory() as session:
        course = Course(title="含课次课程", semester="2025-2026-2", status="draft")
        session.add(course)
        session.flush()
        lesson = Lesson(
            course_id=course.id,
            week="1",
            lesson_no="1",
            hours="2",
            lesson_code="0101",
            title="测试课次",
            content_summary="测试内容",
            homework_hint="",
            status="draft",
        )
        session.add(lesson)
        session.flush()
        material = LessonMaterial(lesson_id=lesson.id, material_type="pasted_text", title="资料", content="资料内容")
        outline = KnowledgeOutline(
            lesson_id=lesson.id,
            ai_raw_output="知识主干",
            edited_content="知识主干",
            status="reviewed",
            generated_by_model="mock-ai",
        )
        session.add_all([material, outline])
        session.flush()
        draft = LessonDraft(
            lesson_id=lesson.id,
            source_outline_id=outline.id,
            draft_type="guide_low",
            title="基础版导学案",
            content="导学案内容",
            generated_by="local-structured-draft",
        )
        session.add(draft)
        session.commit()
        course_id = course.id

    try:
        response = await client.post(f"/courses/{course_id}/delete")

        assert response.status_code == 303
        with session_factory() as session:
            assert session.get(Course, course_id) is None
            assert session.scalars(select(Lesson)).all() == []
            assert session.scalars(select(LessonMaterial)).all() == []
            assert session.scalars(select(KnowledgeOutline)).all() == []
            assert session.scalars(select(LessonDraft)).all() == []
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()
