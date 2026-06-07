from pathlib import Path

import pytest

from app import main
from tests.support.course_plan_helpers import _build_test_client, anyio_backend, inline_threadpool_for_tests


@pytest.mark.anyio
async def test_no_sql_python_c_grading_demo_routes_added(tmp_path: Path) -> None:
    client, _ = _build_test_client(tmp_path)
    try:
        for path in ["/demo-grading/sql", "/demo-grading/python", "/demo-grading/c"]:
            response = await client.get(path)
            assert response.status_code == 404
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()
