from pathlib import Path

import pytest
from sqlalchemy import select

from app import main
from app.models.course_plan import PlannedLesson
from app.models.lesson import Lesson
from tests.support.course_plan_helpers import (
    _build_test_client,
    _create_course,
    _upload_sample_plan,
    anyio_backend,
    inline_threadpool_for_tests,
)


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


@pytest.mark.anyio
async def test_lessons_list_links_to_v2_materials_outline(tmp_path: Path) -> None:
    client, session_factory = _build_test_client(tmp_path)
    course = _create_course(session_factory)
    try:
        await _upload_sample_plan(client, course)
        with session_factory() as session:
            selected_id = session.scalar(select(PlannedLesson.id).order_by(PlannedLesson.id))
            assert selected_id is not None

        await client.post(
            "/course-plan-uploads/1/confirm",
            data={"planned_lesson_ids": str(selected_id)},
            follow_redirects=False,
        )
        response = await client.get(f"/courses/{course.id}/lessons")

        assert response.status_code == 200
        assert "查看详情" not in response.text
        assert "作业提示" not in response.text
        assert "课程资料整理" in response.text
        assert "资料与主干" not in response.text
        assert "资料主干" not in response.text
        assert "学情测试" in response.text
        assert "导学案" in response.text
        assert "/ui-v2/lessons/1/materials-outline" in response.text
        assert f"/courses/{course.id}/course-plan/upload?return_to=/ui-v2/courses" in response.text
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_lesson_detail_page_is_accessible(tmp_path: Path) -> None:
    client, session_factory = _build_test_client(tmp_path)
    course = _create_course(session_factory)
    try:
        await _upload_sample_plan(client, course)
        with session_factory() as session:
            selected_id = session.scalar(select(PlannedLesson.id).order_by(PlannedLesson.id))
            assert selected_id is not None
        await client.post(
            "/course-plan-uploads/1/confirm",
            data={"planned_lesson_ids": str(selected_id)},
            follow_redirects=False,
        )

        response = await client.get("/lessons/1")

        assert response.status_code == 200
        assert "课次详情" in response.text
        assert "添加教学资料" in response.text
        assert "已添加资料" in response.text
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()
