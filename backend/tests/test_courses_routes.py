from pathlib import Path

import pytest
from sqlalchemy import select

from app import main
from app.models.course import Course
from tests.support.course_plan_helpers import _build_test_client, anyio_backend, inline_threadpool_for_tests


@pytest.mark.anyio
async def test_courses_page_is_accessible(tmp_path: Path) -> None:
    client, session_factory = _build_test_client(tmp_path)
    try:
        response = await client.get("/courses")

        assert response.status_code == 200
        assert "课程列表" in response.text
        assert "查看正式课次" in response.text
        assert "/courses/1/lessons" in response.text
        with session_factory() as session:
            assert session.scalar(select(Course)) is not None
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()
