from collections.abc import Generator
from pathlib import Path

import httpx
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app import main
from app.db.base import create_database_tables
from app.models.course import Course
from app.models.course_plan import CoursePlanUpload, PlannedLesson


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_PLAN = PROJECT_ROOT / "data" / "sample-course-plans" / "2025-2026-database-course-plan.xlsx"


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def _build_test_client(tmp_path: Path) -> tuple[httpx.AsyncClient, sessionmaker[Session]]:
    database_path = tmp_path / "test-course-plan-pages.sqlite"
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
    main.COURSE_PLAN_UPLOAD_DIR = tmp_path / "course-plans"
    transport = httpx.ASGITransport(app=main.app)
    return httpx.AsyncClient(transport=transport, base_url="http://testserver"), session_factory


def _create_course(session_factory: sessionmaker[Session]) -> Course:
    with session_factory() as session:
        course = Course(title="数据库应用与数据分析", semester="2025-2026-2", status="draft")
        session.add(course)
        session.commit()
        session.refresh(course)
        return course


@pytest.mark.anyio
async def test_courses_page_is_accessible(tmp_path: Path) -> None:
    client, session_factory = _build_test_client(tmp_path)
    try:
        response = await client.get("/courses")

        assert response.status_code == 200
        assert "课程列表" in response.text
        with session_factory() as session:
            assert session.scalar(select(Course)) is not None
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_upload_page_is_accessible(tmp_path: Path) -> None:
    client, session_factory = _build_test_client(tmp_path)
    course = _create_course(session_factory)
    try:
        response = await client.get(f"/courses/{course.id}/course-plan/upload")

        assert response.status_code == 200
        assert "上传授课计划" in response.text
        assert "选择 .xlsx 授课计划文件" in response.text
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_non_xlsx_upload_returns_error(tmp_path: Path) -> None:
    client, session_factory = _build_test_client(tmp_path)
    course = _create_course(session_factory)
    try:
        response = await client.post(
            f"/courses/{course.id}/course-plan/upload",
            files={"file": ("course-plan.txt", b"not xlsx", "text/plain")},
        )

        assert response.status_code == 400
        assert "当前仅支持 .xlsx 格式" in response.text
        with session_factory() as session:
            assert session.scalars(select(CoursePlanUpload)).all() == []
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_upload_sample_xlsx_creates_upload_and_28_planned_lessons(tmp_path: Path) -> None:
    client, session_factory = _build_test_client(tmp_path)
    course = _create_course(session_factory)
    try:
        response = await client.post(
            f"/courses/{course.id}/course-plan/upload",
            files={
                "file": (
                    SAMPLE_PLAN.name,
                    SAMPLE_PLAN.read_bytes(),
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
            follow_redirects=False,
        )

        assert response.status_code == 303
        with session_factory() as session:
            uploads = session.scalars(select(CoursePlanUpload)).all()
            planned_lessons = session.scalars(select(PlannedLesson)).all()
            assert len(uploads) == 1
            assert uploads[0].parsed_status == "success"
            assert len(planned_lessons) == 28
            assert planned_lessons[0].course_id == course.id
            assert planned_lessons[0].course_plan_upload_id == uploads[0].id
        assert list((tmp_path / "course-plans").glob("*.xlsx"))
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_preview_page_shows_import_result(tmp_path: Path) -> None:
    client, session_factory = _build_test_client(tmp_path)
    course = _create_course(session_factory)
    try:
        upload_response = await client.post(
            f"/courses/{course.id}/course-plan/upload",
            files={
                "file": (
                    SAMPLE_PLAN.name,
                    SAMPLE_PLAN.read_bytes(),
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
            follow_redirects=False,
        )

        preview_response = await client.get(upload_response.headers["location"])

        assert preview_response.status_code == 200
        assert "授课计划导入结果" in preview_response.text
        assert "planned lessons 数量：28" in preview_response.text
        assert "success" in preview_response.text
        assert "lesson_title" in preview_response.text
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()
