from collections.abc import Generator
from pathlib import Path
import re

import httpx
import pytest
from sqlalchemy import String, Text, create_engine, inspect as sa_inspect, select, text
from sqlalchemy.orm import Session, sessionmaker

from app import main
from app.db.base import create_database_tables
from app.models.course import Course
from app.models.course_plan import PlannedLesson
from app.models.knowledge_outline import KnowledgeOutline
from app.models.lesson import LessonMaterial
from app.services.ai.deepseek_client import (
    DeepSeekConfig,
    DeepSeekProviderError,
    build_knowledge_outline_prompt,
    generate_deepseek_knowledge_outline,
    get_allowed_deepseek_models,
    get_deepseek_config,
    get_default_deepseek_model,
    is_allowed_deepseek_model,
)
from app.services.ai.provider import GeneratedOutline
from app.services.ai.sanitizer import sanitize_text_for_outline
from app.services.ai.session_key_store import clear_all_session_api_keys_for_tests


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_PLAN = PROJECT_ROOT / "data" / "sample-course-plans" / "2025-2026-database-course-plan.xlsx"
SAME_ORIGIN_HEADERS = {"origin": "http://testserver"}


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def inline_threadpool_for_tests(monkeypatch: pytest.MonkeyPatch) -> None:
    """测试环境不启动真实线程，避免误触外部请求或沙箱线程限制。"""

    async def run_inline(func: object, *args: object, **kwargs: object) -> object:
        return func(*args, **kwargs)  # type: ignore[misc]

    monkeypatch.setattr(main, "run_in_threadpool", run_inline)


def _build_test_client(tmp_path: Path) -> tuple[httpx.AsyncClient, sessionmaker[Session]]:
    clear_all_session_api_keys_for_tests()
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
    main.LESSON_MATERIAL_UPLOAD_DIR = tmp_path / "lesson-materials"
    main.CHAOXING_EXPORT_DIR = tmp_path / "exports" / "chaoxing"
    main.GUIDE_EXPORT_DIR = tmp_path / "exports" / "guides"
    transport = httpx.ASGITransport(app=main.app)
    return httpx.AsyncClient(transport=transport, base_url="http://testserver"), session_factory


def _create_course(session_factory: sessionmaker[Session]) -> Course:
    with session_factory() as session:
        course = Course(title="数据库应用与数据分析", semester="2025-2026-2", status="draft")
        session.add(course)
        session.commit()
        session.refresh(course)
        return course


def _database_contains_text(session: Session, needle: str) -> bool:
    """扫描业务表文本字段是否包含指定内容，不返回字段值。"""

    bind = session.get_bind()
    inspector = sa_inspect(bind)
    for table_name in inspector.get_table_names():
        if table_name.startswith("sqlite_"):
            continue
        columns = [
            column["name"]
            for column in inspector.get_columns(table_name)
            if isinstance(column["type"], (String, Text))
        ]
        if not columns:
            continue
        quoted_columns = ", ".join(f'"{column}"' for column in columns)
        rows = session.execute(text(f'SELECT {quoted_columns} FROM "{table_name}"')).all()
        for row in rows:
            if any(value is not None and needle in str(value) for value in row):
                return True
    return False


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


async def _create_first_lesson(client: httpx.AsyncClient, session_factory: sessionmaker[Session], course: Course) -> None:
    """通过授课计划确认流程创建一个正式课次。"""

    await _upload_sample_plan(client, course)
    with session_factory() as session:
        selected_id = session.scalar(select(PlannedLesson.id).order_by(PlannedLesson.id))
        assert selected_id is not None
    response = await client.post(
        "/course-plan-uploads/1/confirm",
        data={"planned_lesson_ids": str(selected_id)},
        follow_redirects=False,
    )
    assert response.status_code == 303


def _create_reviewed_outline(session_factory: sessionmaker[Session], lesson_id: int = 1) -> None:
    """为导学草稿测试准备一条已复核知识主干。"""

    with session_factory() as session:
        outline = KnowledgeOutline(
            lesson_id=lesson_id,
            ai_raw_output="知识主干：核心概念、课堂任务、易错点和职业素养提示。",
            edited_content="知识主干：核心概念、课堂任务、易错点和职业素养提示。学生需要完成基础操作并复盘错误。",
            status="reviewed",
            generated_by_model="test-model",
        )
        session.add(outline)
        session.commit()


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
