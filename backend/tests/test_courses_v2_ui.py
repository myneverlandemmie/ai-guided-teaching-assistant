from collections.abc import Generator
from pathlib import Path

import httpx
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app import main
from app.db.base import create_database_tables
from app.models.course import Course


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def _build_test_client(tmp_path: Path) -> tuple[httpx.AsyncClient, sessionmaker[Session]]:
    database_path = tmp_path / "test-courses-v2.sqlite"
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
async def test_courses_v2_page_is_accessible_and_uses_real_courses(tmp_path: Path) -> None:
    client, session_factory = _build_test_client(tmp_path)
    with session_factory() as session:
        course = Course(title="传感器应用基础", semester="2025-2026-2", status="draft")
        session.add(course)
        session.commit()

    try:
        response = await client.get("/ui-v2/courses")

        assert response.status_code == 200
        assert "AI 导学工作台 · 课程中心" in response.text
        assert "智学导评 V0.2" in response.text
        assert "教师 AI 备课工作台" in response.text
        assert "课程资料整理" in response.text
        assert "整理资料，形成知识主干与备课参考" in response.text
        assert "课前学情测试" in response.text
        assert "了解学生课前基础" in response.text
        assert "学生导学案" in response.text
        assert "形成学生学习单与任务包" in response.text
        assert "导入课次资料" not in response.text
        assert "传感器应用基础" in response.text
        assert "新建课程" in response.text
        assert 'action="/courses/create"' in response.text
        assert 'name="return_to" value="/ui-v2/courses"' in response.text
        assert "上传授课计划" in response.text
        assert f"/course-plan/upload?return_to=/ui-v2/courses" in response.text
        assert "查看正式课次" in response.text
        assert "作业批阅" in response.text
        assert "作业批阅（规划中）" not in response.text
        assert "预留功能" in response.text
        assert "仅供教师参考" in response.text
        assert "教师审核确认" in response.text
        assert "规划中" in response.text
        assert "/grading" not in response.text
        assert "AI 评语生成" not in response.text
        assert "立即使用作业批阅" not in response.text
        assert "学生端" not in response.text
        assert "course-rename-details-v2" in response.text
        assert "修改课程名" in response.text
        assert "course-danger-details-v2" in response.text
        assert "危险操作" in response.text
        assert "删除课程" in response.text
        assert "AI 设置" in response.text
        assert "返回旧版课程页" not in response.text
        assert "课程列表" not in response.text
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_courses_v2_create_course_uses_real_backend_and_returns_preview(tmp_path: Path) -> None:
    client, session_factory = _build_test_client(tmp_path)
    try:
        response = await client.post(
            "/courses/create",
            data={"title": "专业英语", "return_to": "/ui-v2/courses"},
        )

        assert response.status_code == 303
        assert response.headers["location"] == "/ui-v2/courses"
        page = await client.get("/ui-v2/courses")
        assert "专业英语" in page.text
        with session_factory() as session:
            assert session.scalar(select(Course).where(Course.title == "专业英语")) is not None
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_courses_v2_does_not_change_legacy_courses_page(tmp_path: Path) -> None:
    client, session_factory = _build_test_client(tmp_path)
    with session_factory() as session:
        course = Course(title="测试课程", semester="2025-2026-2", status="draft")
        session.add(course)
        session.commit()

    try:
        old_page = await client.get("/courses")
        v2_page = await client.get("/ui-v2/courses")

        assert old_page.status_code == 200
        assert "课程中心" in old_page.text
        assert "AI 导学工作台 · 课程中心" not in old_page.text
        assert v2_page.status_code == 200
        assert "AI 导学工作台 · 课程中心" in v2_page.text
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()
