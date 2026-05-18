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
from app.models.lesson import Lesson


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


async def _upload_sample_plan(
    client: httpx.AsyncClient,
    course: Course,
) -> str:
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
    return response.headers["location"]


@pytest.mark.anyio
async def test_confirm_selected_planned_lessons_and_skip_unselected(tmp_path: Path) -> None:
    client, session_factory = _build_test_client(tmp_path)
    course = _create_course(session_factory)
    try:
        await _upload_sample_plan(client, course)
        with session_factory() as session:
            planned_lessons = session.scalars(select(PlannedLesson).order_by(PlannedLesson.id)).all()
            selected_ids = [lesson.id for lesson in planned_lessons[:3]]
            skipped_id = planned_lessons[3].id

        response = await client.post(
            "/course-plan-uploads/1/confirm",
            data={"planned_lesson_ids": [str(lesson_id) for lesson_id in selected_ids]},
            follow_redirects=False,
        )

        assert response.status_code == 303
        assert response.headers["location"] == f"/courses/{course.id}/lessons"
        with session_factory() as session:
            confirmed = session.scalars(select(PlannedLesson).where(PlannedLesson.id.in_(selected_ids))).all()
            skipped = session.get(PlannedLesson, skipped_id)
            lessons = session.scalars(select(Lesson).order_by(Lesson.id)).all()
            assert {lesson.status for lesson in confirmed} == {"confirmed"}
            assert skipped is not None
            assert skipped.status == "skipped"
            assert len(lessons) == 3
            assert {lesson.planned_lesson_id for lesson in lessons} == set(selected_ids)
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_skipped_planned_lessons_do_not_create_lessons(tmp_path: Path) -> None:
    client, session_factory = _build_test_client(tmp_path)
    course = _create_course(session_factory)
    try:
        await _upload_sample_plan(client, course)
        with session_factory() as session:
            planned_lessons = session.scalars(select(PlannedLesson).order_by(PlannedLesson.id)).all()
            selected_id = planned_lessons[0].id
            unselected_ids = [lesson.id for lesson in planned_lessons[1:]]

        response = await client.post(
            "/course-plan-uploads/1/confirm",
            data={"planned_lesson_ids": str(selected_id)},
            follow_redirects=False,
        )

        assert response.status_code == 303
        with session_factory() as session:
            lessons = session.scalars(select(Lesson)).all()
            skipped_lessons = session.scalars(select(PlannedLesson).where(PlannedLesson.id.in_(unselected_ids))).all()
            assert len(lessons) == 1
            assert lessons[0].planned_lesson_id == selected_id
            assert {lesson.status for lesson in skipped_lessons} == {"skipped"}
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_lessons_page_is_accessible_and_shows_created_lessons(tmp_path: Path) -> None:
    client, session_factory = _build_test_client(tmp_path)
    course = _create_course(session_factory)
    try:
        preview_location = await _upload_sample_plan(client, course)
        preview_response = await client.get(preview_location)
        assert preview_response.status_code == 200
        assert "选择生成正式课次" in preview_response.text

        with session_factory() as session:
            selected_ids = [
                lesson.id
                for lesson in session.scalars(select(PlannedLesson).order_by(PlannedLesson.id).limit(2)).all()
            ]

        await client.post(
            "/course-plan-uploads/1/confirm",
            data={"planned_lesson_ids": [str(lesson_id) for lesson_id in selected_ids]},
            follow_redirects=False,
        )
        response = await client.get(f"/courses/{course.id}/lessons")

        assert response.status_code == 200
        assert "正式课次列表" in response.text
        assert "正式课次数量：2" in response.text
        with session_factory() as session:
            assert len(session.scalars(select(Lesson)).all()) == 2
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()
