from pathlib import Path

import pytest
from sqlalchemy import select

from app import main
from app.models.course_plan import CoursePlanUpload, PlannedLesson
from app.models.lesson import Lesson
from tests.support.course_plan_helpers import (
    SAMPLE_PLAN,
    _build_test_client,
    _create_course,
    _upload_sample_plan,
    anyio_backend,
    inline_threadpool_for_tests,
)


@pytest.mark.anyio
async def test_upload_page_is_accessible(tmp_path: Path) -> None:
    client, session_factory = _build_test_client(tmp_path)
    course = _create_course(session_factory)
    try:
        response = await client.get(f"/courses/{course.id}/course-plan/upload")

        assert response.status_code == 200
        assert "上传授课计划" in response.text
        assert "选择 .xlsx 授课计划文件" in response.text
        assert 'href="/courses"' in response.text
        assert "智学导评 V0.2" not in response.text
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_upload_page_uses_safe_return_to_for_v2_entry(tmp_path: Path) -> None:
    client, session_factory = _build_test_client(tmp_path)
    course = _create_course(session_factory)
    try:
        response = await client.get(f"/courses/{course.id}/course-plan/upload?return_to=/ui-v2/courses")
        unsafe_response = await client.get(
            f"/courses/{course.id}/course-plan/upload?return_to=https://evil.example/path",
            follow_redirects=False,
        )

        assert response.status_code == 200
        assert 'href="/ui-v2/courses"' in response.text
        assert 'name="return_to" value="/ui-v2/courses"' in response.text
        assert "智学导评 V0.2" in response.text
        assert "课程列表" not in response.text
        assert unsafe_response.status_code == 303
        assert unsafe_response.headers["location"] == "/ui-v2/courses?return_to_invalid=1"
        assert "evil.example" not in unsafe_response.headers["location"]
        unsafe_page = await client.get(unsafe_response.headers["location"])
        assert unsafe_page.status_code == 200
        assert "返回地址无效，已返回课程中心。" in unsafe_page.text
        assert "evil.example" not in unsafe_page.text

        upload_response = await client.post(
            f"/courses/{course.id}/course-plan/upload",
            data={"return_to": "/ui-v2/courses"},
            files={
                "file": (
                    SAMPLE_PLAN.name,
                    SAMPLE_PLAN.read_bytes(),
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
            follow_redirects=False,
        )
        assert upload_response.status_code == 303
        assert upload_response.headers["location"].endswith("?return_to=%2Fui-v2%2Fcourses")
        preview_response = await client.get(upload_response.headers["location"])
        assert preview_response.status_code == 200
        assert "智学导评 V0.2" in preview_response.text
        assert "课程列表" not in preview_response.text
        assert 'href="/ui-v2/courses"' in preview_response.text
        assert 'name="return_to" value="/ui-v2/courses"' in preview_response.text
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
        assert "课次预览数量：28" in preview_response.text
        assert "课次预览与选择" in preview_response.text
        assert "planned lessons" not in preview_response.text
        assert "content_raw" not in preview_response.text
        assert "选择生成正式课次" in preview_response.text
        assert "教学内容摘要" not in preview_response.text
        assert "作业/提示" in preview_response.text
        assert "备注" in preview_response.text
        assert "success" in preview_response.text
        assert "课次标题" in preview_response.text
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


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
