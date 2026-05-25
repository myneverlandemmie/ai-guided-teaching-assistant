from collections.abc import Generator
from pathlib import Path

import httpx
import pytest
from docx import Document
from pptx import Presentation
from sqlalchemy import String, Text, create_engine, inspect as sa_inspect, select, text
from sqlalchemy.orm import Session, sessionmaker

from app import main
from app.db.base import create_database_tables
from app.models.course import Course
from app.models.course_plan import CoursePlanUpload, PlannedLesson
from app.models.knowledge_outline import KnowledgeOutline
from app.models.lesson import Lesson, LessonMaterial
from app.services.ai import session_key_store
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
from app.services.ai.session_key_store import (
    SESSION_COOKIE_NAME,
    clear_all_session_api_keys_for_tests,
    clear_session_api_key,
    get_session_api_key,
    get_session_selected_model,
    get_session_store_size_for_tests,
    has_session_api_key_for_tests,
    set_session_api_key,
)


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


def test_session_api_key_store_expires_and_clears(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_all_session_api_keys_for_tests()
    monkeypatch.setenv("AI_SESSION_KEY_IDLE_TIMEOUT_SECONDS", "10")
    current_time = [100.0]
    monkeypatch.setattr(session_key_store, "_now", lambda: current_time[0])
    session_id = "A" * 40

    set_session_api_key(session_id, "sk-" + "x" * 16 + "1111", "deepseek-v4-flash")

    assert get_session_api_key(session_id) is not None
    assert get_session_selected_model(session_id) == "deepseek-v4-flash"
    current_time[0] = 111.0
    assert get_session_api_key(session_id) is None
    assert get_session_selected_model(session_id) is None
    assert has_session_api_key_for_tests(session_id) is False

    set_session_api_key(session_id, "sk-" + "x" * 16 + "2222", "deepseek-v4-pro")
    clear_session_api_key(session_id)
    assert get_session_api_key(session_id) is None
    assert get_session_selected_model(session_id) is None


def test_session_api_key_store_capacity_and_invalid_env(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_all_session_api_keys_for_tests()
    monkeypatch.setenv("AI_SESSION_KEY_IDLE_TIMEOUT_SECONDS", "bad")
    monkeypatch.setenv("AI_SESSION_KEY_MAX_ENTRIES", "2")
    current_time = [200.0]
    monkeypatch.setattr(session_key_store, "_now", lambda: current_time[0])

    for index, session_id in enumerate(["B" * 40, "C" * 40, "D" * 40]):
        current_time[0] += index + 1
        set_session_api_key(session_id, "sk-" + "y" * 16 + str(index).zfill(4))

    assert get_session_store_size_for_tests() == 2
    assert get_session_api_key("B" * 40) is None
    assert get_session_api_key("C" * 40) is not None
    assert get_session_api_key("D" * 40) is not None

    monkeypatch.setenv("AI_SESSION_KEY_MAX_ENTRIES", "bad")
    set_session_api_key("E" * 40, "sk-" + "z" * 16 + "9999")
    assert get_session_api_key("E" * 40) is not None


def test_sanitizer_covers_common_administrative_variants() -> None:
    source = "\n".join(
        [
            "学校名称：示例学校",
            "教师：张老师",
            "任课老师：张老师",
            "班级：23物联网2班",
            "学校 | 示例学校",
            "授课班级 23物联网2班",
            "教学目标：掌握 WHERE 条件查询。",
            "实验步骤：编写 SQL 语句。",
        ]
    )

    sanitized = sanitize_text_for_outline(source)

    assert "示例学校" not in sanitized
    assert "张老师" not in sanitized
    assert "23物联网2班" not in sanitized
    assert "教学目标" in sanitized
    assert "WHERE" in sanitized
    assert "实验步骤" in sanitized


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


@pytest.mark.anyio
async def test_lessons_list_links_to_lesson_detail(tmp_path: Path) -> None:
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
        assert "查看详情" in response.text
        assert "/lessons/1" in response.text
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


@pytest.mark.anyio
async def test_can_submit_text_lesson_material(tmp_path: Path) -> None:
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

        response = await client.post(
            "/lessons/1/materials",
            data={
                "title": "本节课导入材料",
                "material_type": "pasted_text",
                "content": "SELECT 与 WHERE 的课堂说明。",
            },
            follow_redirects=False,
        )

        assert response.status_code == 303
        assert response.headers["location"] == "/lessons/1"
        with session_factory() as session:
            materials = session.scalars(select(LessonMaterial)).all()
            assert len(materials) == 1
            assert materials[0].lesson_id == 1
            assert materials[0].title == "本节课导入材料"
            assert materials[0].content == "SELECT 与 WHERE 的课堂说明。"
            assert materials[0].file_path is None
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_lesson_detail_shows_saved_material(tmp_path: Path) -> None:
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
        await client.post(
            "/lessons/1/materials",
            data={
                "title": "课堂讲义文本",
                "material_type": "pasted_text",
                "content": "本节课讲解简单查询和条件筛选。",
            },
            follow_redirects=False,
        )

        response = await client.get("/lessons/1")

        assert response.status_code == 200
        assert "课堂讲义文本" in response.text
        assert "本节课讲解简单查询和条件筛选。" in response.text
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_lesson_detail_shows_material_support_scope(tmp_path: Path) -> None:
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
        assert "当前支持直接粘贴文本" in response.text
        assert "添加到本课次" in response.text
        assert "上传 .txt、.md、.docx 文件" in response.text
        assert "实验性支持 .pptx 文本提取" in response.text
        assert "暂不支持旧版 .doc、.ppt、PDF、图片文件" in response.text
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_unsupported_lesson_material_file_type_shows_hint(tmp_path: Path) -> None:
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

        response = await client.post(
            "/lessons/1/materials",
            data={"title": "PDF 材料", "material_type": "supplementary", "content": ""},
            files={"files": ("lesson.pdf", b"fake pdf", "application/pdf")},
        )

        assert response.status_code == 400
        assert "暂不支持该文件类型" in response.text
        assert "暂不支持旧版 .doc、.ppt、PDF、图片文件" in response.text
        with session_factory() as session:
            assert session.scalars(select(LessonMaterial)).all() == []
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


def _create_minimal_docx(path: Path) -> None:
    document = Document()
    document.add_paragraph("教学目标：理解 INNER JOIN")
    table = document.add_table(rows=1, cols=2)
    table.cell(0, 0).text = "重点"
    table.cell(0, 1).text = "GROUP BY 与 HAVING"
    document.save(path)


def _create_table_lesson_plan_docx(path: Path) -> None:
    document = Document()
    document.add_paragraph("条件查询教学设计")
    table = document.add_table(rows=7, cols=2)
    rows = [
        ("教学目标", "知识目标\n掌握WHERE子句的使用方法\n能力目标\n能够根据任务选择合适的筛选条件\n素养目标\n形成规范书写 SQL 的习惯"),
        ("重点", "WHERE、AND、OR、NOT 条件筛选"),
        ("难点", "多个条件组合时的逻辑关系"),
        ("教学过程", "组织教学\n复习导入\n新课讲授：WHERE 条件查询\n课堂练习：查询指定类别商品"),
        ("课堂练习", "使用 IN关键字 完成多条件筛选。"),
        ("布置作业", "完成 WHERE 子句练习题。"),
        ("教学反思", "学生对多条件组合还需要更多示例。"),
    ]
    for index, (label, value) in enumerate(rows):
        table.cell(index, 0).text = label
        table.cell(index, 1).text = value
    document.save(path)


def _create_minimal_pptx(path: Path) -> None:
    presentation = Presentation()
    slide = presentation.slides.add_slide(presentation.slide_layouts[5])
    title = slide.shapes.title
    title.text = "SQL 高级查询"
    text_box = slide.shapes.add_textbox(0, 0, 5000000, 1000000)
    text_box.text_frame.text = "INNER JOIN 与 OUTER JOIN"
    footer = slide.shapes.add_textbox(0, 1000000, 5000000, 1000000)
    footer.text_frame.text = "© Microsoft Corporation All rights reserved"
    presentation.save(path)


@pytest.mark.anyio
async def test_can_upload_docx_lesson_material_with_paragraph_and_table_text(tmp_path: Path) -> None:
    client, session_factory = _build_test_client(tmp_path)
    course = _create_course(session_factory)
    docx_path = tmp_path / "lesson.docx"
    _create_minimal_docx(docx_path)
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

        response = await client.post(
            "/lessons/1/materials",
            data={"title": "Word 教案", "material_type": "lesson_plan", "content": ""},
            files={
                "files": (
                    "lesson.docx",
                    docx_path.read_bytes(),
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
            follow_redirects=False,
        )

        assert response.status_code == 303
        with session_factory() as session:
            material = session.scalar(select(LessonMaterial))
            assert material is not None
            assert "教学目标：理解 INNER JOIN" in material.content
            assert "重点" in material.content
            assert "GROUP BY 与 HAVING" in material.content
            assert material.file_path is not None

        page_response = await client.get("/lessons/1")
        assert page_response.status_code == 200
        assert "lesson.docx" in page_response.text
        assert str(tmp_path) not in page_response.text
        assert "data/uploads" not in page_response.text
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_can_extract_table_style_docx_lesson_plan_completely(tmp_path: Path) -> None:
    client, session_factory = _build_test_client(tmp_path)
    course = _create_course(session_factory)
    docx_path = tmp_path / "table-lesson-plan.docx"
    _create_table_lesson_plan_docx(docx_path)
    try:
        await _upload_sample_plan(client, course)
        with session_factory() as session:
            selected_id = session.scalar(select(PlannedLesson.id).where(PlannedLesson.lesson_code == "0402"))
            assert selected_id is not None
        await client.post(
            "/course-plan-uploads/1/confirm",
            data={"planned_lesson_ids": str(selected_id)},
            follow_redirects=False,
        )

        response = await client.post(
            "/lessons/1/materials",
            data={"title": "", "material_type": "lesson_plan", "content": ""},
            files={
                "files": (
                    "table-lesson-plan.docx",
                    docx_path.read_bytes(),
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
            follow_redirects=False,
        )

        assert response.status_code == 303
        with session_factory() as session:
            material = session.scalar(select(LessonMaterial))
            assert material is not None
            assert material.title == "0402-教案"
            assert "知识目标" in material.content
            assert "掌握WHERE子句的使用方法" in material.content
            assert "能力目标" in material.content
            assert "素养目标" in material.content
            assert "重点" in material.content
            assert "难点" in material.content
            assert "教学过程" in material.content
            assert "课堂练习" in material.content
            assert "教学反思" in material.content
            assert "\n" in material.content
            assert len(material.content) > 180
            assert material.content.count("教学过程") == 1

        page_response = await client.get("/lessons/1")
        assert page_response.status_code == 200
        assert "table-lesson-plan.docx" in page_response.text
        assert str(tmp_path) not in page_response.text
        assert "data/uploads" not in page_response.text
        assert "掌握WHERE子句的使用方法" in page_response.text
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_default_lesson_material_title_adds_sequence_for_duplicates(tmp_path: Path) -> None:
    client, session_factory = _build_test_client(tmp_path)
    course = _create_course(session_factory)
    docx_path = tmp_path / "table-lesson-plan.docx"
    _create_table_lesson_plan_docx(docx_path)
    try:
        await _upload_sample_plan(client, course)
        with session_factory() as session:
            selected_id = session.scalar(select(PlannedLesson.id).where(PlannedLesson.lesson_code == "0402"))
            assert selected_id is not None
        await client.post(
            "/course-plan-uploads/1/confirm",
            data={"planned_lesson_ids": str(selected_id)},
            follow_redirects=False,
        )

        for _ in range(2):
            response = await client.post(
                "/lessons/1/materials",
                data={"title": "", "material_type": "lesson_plan", "content": ""},
                files={
                    "files": (
                        "table-lesson-plan.docx",
                        docx_path.read_bytes(),
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    )
                },
                follow_redirects=False,
            )
            assert response.status_code == 303

        with session_factory() as session:
            titles = session.scalars(select(LessonMaterial.title).order_by(LessonMaterial.id)).all()
            assert titles == ["0402-教案", "0402-教案（2）"]
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_can_upload_pptx_lesson_material_with_slide_text_and_cleaned_footer(tmp_path: Path) -> None:
    client, session_factory = _build_test_client(tmp_path)
    course = _create_course(session_factory)
    pptx_path = tmp_path / "lesson.pptx"
    _create_minimal_pptx(pptx_path)
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

        response = await client.post(
            "/lessons/1/materials",
            data={"title": "PPT 材料", "material_type": "course_ppt", "content": ""},
            files={
                "files": (
                    "lesson.pptx",
                    pptx_path.read_bytes(),
                    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                )
            },
            follow_redirects=False,
        )

        assert response.status_code == 303
        with session_factory() as session:
            material = session.scalar(select(LessonMaterial))
            assert material is not None
            assert "【Slide 1】" in material.content
            assert "SQL 高级查询" in material.content
            assert "INNER JOIN 与 OUTER JOIN" in material.content
            assert "© Microsoft Corporation" not in material.content
            assert "All rights reserved" not in material.content
            assert material.file_path is not None
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_can_upload_multiple_lesson_material_files(tmp_path: Path) -> None:
    client, session_factory = _build_test_client(tmp_path)
    course = _create_course(session_factory)
    guide_path = tmp_path / "guide.md"
    note_path = tmp_path / "note.txt"
    guide_path.write_text("实训指导：完成 INNER JOIN 查询", encoding="utf-8")
    note_path.write_text("补充资料：GROUP BY 练习", encoding="utf-8")
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

        response = await client.post(
            "/lessons/1/materials",
            data={"title": "批量资料", "material_type": "supplementary", "content": ""},
            files=[
                ("files", ("guide.md", guide_path.read_bytes(), "text/markdown")),
                ("files", ("note.txt", note_path.read_bytes(), "text/plain")),
            ],
            follow_redirects=False,
        )

        assert response.status_code == 303
        with session_factory() as session:
            materials = session.scalars(select(LessonMaterial).order_by(LessonMaterial.id)).all()
            assert len(materials) == 2
            assert "实训指导：完成 INNER JOIN 查询" in materials[0].content
            assert "补充资料：GROUP BY 练习" in materials[1].content
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_docx_extraction_deduplicates_repeated_lines(tmp_path: Path) -> None:
    client, session_factory = _build_test_client(tmp_path)
    course = _create_course(session_factory)
    docx_path = tmp_path / "duplicate.docx"
    document = Document()
    document.add_paragraph("教学目标：理解连接查询")
    document.add_paragraph("教学目标：理解连接查询")
    table = document.add_table(rows=2, cols=1)
    table.cell(0, 0).text = "教学过程：演示 INNER JOIN"
    table.cell(1, 0).text = "教学过程：演示 INNER JOIN"
    document.save(docx_path)
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

        response = await client.post(
            "/lessons/1/materials",
            data={"title": "去重教案", "material_type": "lesson_plan", "content": ""},
            files={
                "files": (
                    "duplicate.docx",
                    docx_path.read_bytes(),
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
            follow_redirects=False,
        )

        assert response.status_code == 303
        with session_factory() as session:
            material = session.scalar(select(LessonMaterial))
            assert material is not None
            assert material.content.count("教学目标：理解连接查询") == 1
            assert material.content.count("教学过程：演示 INNER JOIN") == 1
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_can_delete_lesson_material(tmp_path: Path) -> None:
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
        await client.post(
            "/lessons/1/materials",
            data={"title": "待删除资料", "material_type": "pasted_text", "content": "传错的资料"},
            follow_redirects=False,
        )
        with session_factory() as session:
            material = session.scalar(select(LessonMaterial))
            assert material is not None
            material_id = material.id

        response = await client.post(f"/lesson-materials/{material_id}/delete", follow_redirects=False)

        assert response.status_code == 303
        assert response.headers["location"] == "/lessons/1"
        with session_factory() as session:
            assert session.scalars(select(LessonMaterial)).all() == []
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_lesson_detail_shows_knowledge_outline_entry(tmp_path: Path) -> None:
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
        assert "知识主干" in response.text
        assert "生成知识主干" in response.text
        assert "/lessons/1/knowledge-outline" in response.text
        assert "/ai/settings?next=/lessons/1" in response.text
        assert "默认基于本课次下已添加资料生成" in response.text
        assert "如果 PPT 覆盖多个课次或整章内容" in response.text
        assert "必须由教师复核后使用" in response.text
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_ai_settings_can_set_mask_and_clear_session_key(tmp_path: Path) -> None:
    client, _ = _build_test_client(tmp_path)
    try:
        page_response = await client.get("/ai/settings")
        assert page_response.status_code == 200
        assert "状态：未设置" in page_response.text
        assert "API Key 仅保存在当前浏览器会话" in page_response.text
        assert "deepseek-v4-flash" in page_response.text
        assert "deepseek-v4-pro" in page_response.text
        assert "deepseek-chat" not in page_response.text
        assert "deepseek-reasoner" not in page_response.text
        assert "DEEPSEEK_ALLOWED_MODELS" in page_response.text
        assert "DEEPSEEK_DEFAULT_MODEL" in page_response.text
        assert "项目根目录" in page_response.text
        assert ".env.example" in page_response.text
        assert "https://api-docs.deepseek.com/zh-cn/api/list-models" in page_response.text
        assert "https://api-docs.deepseek.com/zh-cn/api/create-chat-completion" in page_response.text

        save_response = await client.post(
            "/ai/settings",
            data={"api_key": "sk-test-secret-abcd", "selected_model": "deepseek-v4-flash"},
            headers=SAME_ORIGIN_HEADERS,
        )
        assert save_response.status_code == 200
        assert "状态：已设置" in save_response.text
        assert "sk-****abcd" in save_response.text
        assert "sk-test-secret-abcd" not in save_response.text
        old_session_id = client.cookies.get(SESSION_COOKIE_NAME)
        assert old_session_id is not None
        assert has_session_api_key_for_tests(old_session_id) is True
        assert get_session_selected_model(old_session_id) == "deepseek-v4-flash"

        clear_redirect = await client.post("/ai/settings/clear", headers=SAME_ORIGIN_HEADERS, follow_redirects=False)
        assert clear_redirect.status_code == 303
        assert "Max-Age=0" in clear_redirect.headers.get("set-cookie", "")
        assert has_session_api_key_for_tests(old_session_id) is False
        assert get_session_selected_model(old_session_id) is None

        clear_response = await client.get("/ai/settings")
        assert clear_response.status_code == 200
        assert "状态：未设置" in clear_response.text
        assert client.cookies.get(SESSION_COOKIE_NAME) != old_session_id
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


def test_ai_settings_next_path_sanitizer() -> None:
    assert main.sanitize_next_path("/lessons/1") == "/lessons/1"
    assert main.sanitize_next_path("/lessons/1/knowledge-outline") == "/lessons/1/knowledge-outline"
    assert main.sanitize_next_path("/courses/1/lessons") == "/courses/1/lessons"
    assert main.sanitize_next_path("http://evil.com") is None
    assert main.sanitize_next_path("https://evil.com") is None
    assert main.sanitize_next_path("//evil.com") is None
    assert main.sanitize_next_path("/\\evil") is None
    assert main.sanitize_next_path("/lessons/1\nSet-Cookie: bad=1") is None
    assert main.sanitize_next_path("/lessons/1\rLocation: http://evil.com") is None
    assert main.sanitize_next_path("lessons/1") is None
    assert main.sanitize_next_path("") is None


@pytest.mark.anyio
async def test_ai_settings_safe_next_redirects_after_saving_key(tmp_path: Path) -> None:
    client, _ = _build_test_client(tmp_path)
    fake_key = "sk-" + "n" * 16 + "8888"
    try:
        page_response = await client.get("/ai/settings?next=/lessons/1")
        assert page_response.status_code == 200
        assert 'name="next"' in page_response.text
        assert 'value="/lessons/1"' in page_response.text

        save_response = await client.post(
            "/ai/settings",
            data={"api_key": fake_key, "selected_model": "deepseek-v4-pro", "next": "/lessons/1"},
            headers=SAME_ORIGIN_HEADERS,
            follow_redirects=False,
        )

        assert save_response.status_code == 303
        assert save_response.headers["location"] == "/lessons/1"
        assert fake_key not in save_response.text
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_ai_settings_rejects_unsafe_next_without_echo_or_external_redirect(tmp_path: Path) -> None:
    client, _ = _build_test_client(tmp_path)
    fake_key = "sk-" + "u" * 16 + "9999"
    unsafe_next_values = [
        "http://evil.com",
        "//evil.com",
        "/\\evil",
        "/lessons/1\nLocation: http://evil.com",
    ]
    try:
        for unsafe_next in unsafe_next_values:
            page_response = await client.get("/ai/settings", params={"next": unsafe_next})
            assert page_response.status_code == 200
            assert unsafe_next not in page_response.text
            assert 'name="next"' not in page_response.text

            save_response = await client.post(
                "/ai/settings",
                data={"api_key": fake_key, "selected_model": "deepseek-v4-flash", "next": unsafe_next},
                headers=SAME_ORIGIN_HEADERS,
                follow_redirects=False,
            )

            assert save_response.status_code == 200
            assert "当前会话 API Key 已设置" in save_response.text
            assert "evil.com" not in save_response.text
            assert "/\\evil" not in save_response.text
            assert fake_key not in save_response.text
            assert "location" not in save_response.headers
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_ai_settings_next_keeps_same_origin_protection(tmp_path: Path) -> None:
    client, _ = _build_test_client(tmp_path)
    fake_key = "sk-" + "x" * 16 + "0000"
    try:
        response = await client.post(
            "/ai/settings",
            data={"api_key": fake_key, "selected_model": "deepseek-v4-flash", "next": "/lessons/1"},
            headers={"origin": "http://evil.example"},
            follow_redirects=False,
        )

        assert response.status_code == 403
        assert fake_key not in response.text
        assert response.headers.get("location") is None
        assert get_session_store_size_for_tests() == 0
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_ai_settings_rejects_invalid_selected_model_without_saving_key(tmp_path: Path) -> None:
    client, _ = _build_test_client(tmp_path)
    fake_key = "sk-" + "v" * 16 + "1212"
    try:
        response = await client.post(
            "/ai/settings",
            data={"api_key": fake_key, "selected_model": "deepseek-chat"},
            headers=SAME_ORIGIN_HEADERS,
            follow_redirects=False,
        )

        assert response.status_code == 400
        assert "模型配置无效" in response.text
        assert fake_key not in response.text
        assert get_session_store_size_for_tests() == 0
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_invalid_session_cookie_is_replaced_without_echo(tmp_path: Path) -> None:
    client, _ = _build_test_client(tmp_path)
    invalid_session = "bad/session"
    try:
        response = await client.get("/ai/settings", headers={"cookie": f"{SESSION_COOKIE_NAME}={invalid_session}"})

        assert response.status_code == 200
        assert invalid_session not in response.text
        new_session_id = response.cookies.get(SESSION_COOKIE_NAME)
        assert new_session_id is not None
        assert new_session_id != invalid_session
        assert has_session_api_key_for_tests(invalid_session) is False
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_api_key_is_not_written_to_database(tmp_path: Path) -> None:
    client, session_factory = _build_test_client(tmp_path)
    fake_key = "sk-" + "d" * 16 + "3333"
    try:
        response = await client.post(
            "/ai/settings",
            data={"api_key": fake_key, "selected_model": "deepseek-v4-pro"},
            headers=SAME_ORIGIN_HEADERS,
        )

        assert response.status_code == 200
        assert fake_key not in response.text
        with session_factory() as session:
            key_tables = session.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND lower(name) LIKE '%key%'")
            ).all()
            assert key_tables == []
            assert session.scalar(select(KnowledgeOutline)) is None
            assert _database_contains_text(session, fake_key) is False
            assert _database_contains_text(session, "deepseek-v4-pro") is False
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_ai_settings_rejects_cross_origin_without_setting_key(tmp_path: Path) -> None:
    client, _ = _build_test_client(tmp_path)
    fake_key = "sk-" + "o" * 16 + "4444"
    try:
        response = await client.post(
            "/ai/settings",
            data={"api_key": fake_key, "selected_model": "deepseek-v4-flash"},
            headers={"origin": "http://evil.example"},
        )

        assert response.status_code == 403
        assert fake_key not in response.text
        assert get_session_store_size_for_tests() == 0
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_deepseek_generation_without_api_key_prompts_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_PROVIDER", "deepseek")
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

        response = await client.post(
            "/lessons/1/knowledge-outline/generate",
            headers=SAME_ORIGIN_HEADERS,
            follow_redirects=False,
        )

        assert response.status_code == 400
        assert "请先设置当前会话 DeepSeek API Key" in response.text
        assert "/ai/settings" in response.text
        with session_factory() as session:
            assert session.scalar(select(KnowledgeOutline)) is None
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_knowledge_outline_generation_rejects_cross_origin_without_creating_outline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AI_PROVIDER", "deepseek")
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

        response = await client.post(
            "/lessons/1/knowledge-outline/generate",
            headers={"origin": "http://evil.example"},
            follow_redirects=False,
        )

        assert response.status_code == 403
        with session_factory() as session:
            assert session.scalar(select(KnowledgeOutline)) is None
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_deepseek_generation_uses_provider_and_saves_outline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AI_PROVIDER", "deepseek")
    captured: dict[str, object] = {}

    def fake_generate(
        lesson: Lesson,
        materials: list[LessonMaterial],
        api_key: str | None,
        selected_model: str | None = None,
    ) -> GeneratedOutline:
        captured["lesson_title"] = lesson.title
        captured["material_text"] = "\n".join(material.content for material in materials)
        captured["has_api_key"] = bool(api_key)
        captured["api_key_tail"] = api_key[-4:] if api_key else ""
        captured["selected_model"] = selected_model
        return GeneratedOutline("真实 Provider 测试返回：WHERE 与 IN关键字 知识主干。", selected_model or "deepseek-v4-flash")

    monkeypatch.setattr(main.ai_provider, "generate_knowledge_outline_with_provider", fake_generate)
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
        await client.post(
            "/lessons/1/materials",
            data={
                "title": "课堂材料",
                "material_type": "pasted_text",
                "content": "教学目标：掌握 WHERE 条件查询和 IN关键字。",
            },
            follow_redirects=False,
        )
        await client.post(
            "/ai/settings",
            data={"api_key": "sk-provider-test-abcd", "selected_model": "deepseek-v4-pro"},
            headers=SAME_ORIGIN_HEADERS,
        )

        response = await client.post(
            "/lessons/1/knowledge-outline/generate",
            headers=SAME_ORIGIN_HEADERS,
            follow_redirects=False,
        )

        assert response.status_code == 303
        assert response.headers["location"] == "/lessons/1/knowledge-outline"
        assert captured["has_api_key"] is True
        assert captured["api_key_tail"] == "abcd"
        assert captured["selected_model"] == "deepseek-v4-pro"
        assert "WHERE" in str(captured["material_text"])
        with session_factory() as session:
            outline = session.scalar(select(KnowledgeOutline))
            assert outline is not None
            assert outline.generated_by_model == "deepseek-v4-pro"
            assert outline.status == "draft"
            assert outline.ai_raw_output == "真实 Provider 测试返回：WHERE 与 IN关键字 知识主干。"
            assert outline.edited_content == outline.ai_raw_output
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_deepseek_generation_error_does_not_save_outline_or_expose_key(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AI_PROVIDER", "deepseek")
    fake_key = "sk-" + "e" * 16 + "6666"

    def fake_generate(
        lesson: Lesson,
        materials: list[LessonMaterial],
        api_key: str | None,
        selected_model: str | None = None,
    ) -> GeneratedOutline:
        raise DeepSeekProviderError("DeepSeek 请求超时，请稍后重试或减少材料长度。")

    monkeypatch.setattr(main.ai_provider, "generate_knowledge_outline_with_provider", fake_generate)
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
        await client.post(
            "/ai/settings",
            data={"api_key": fake_key, "selected_model": "deepseek-v4-flash"},
            headers=SAME_ORIGIN_HEADERS,
        )

        response = await client.post(
            "/lessons/1/knowledge-outline/generate",
            headers=SAME_ORIGIN_HEADERS,
            follow_redirects=False,
        )

        assert response.status_code == 400
        assert "请求超时" in response.text
        assert fake_key not in response.text
        with session_factory() as session:
            assert session.scalar(select(KnowledgeOutline)) is None
            assert _database_contains_text(session, fake_key) is False
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_invalid_ai_provider_shows_safe_error_without_outline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AI_PROVIDER", "bad")
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

        response = await client.post(
            "/lessons/1/knowledge-outline/generate",
            headers=SAME_ORIGIN_HEADERS,
            follow_redirects=False,
        )

        assert response.status_code == 400
        assert "AI Provider 配置无效" in response.text
        with session_factory() as session:
            assert session.scalar(select(KnowledgeOutline)) is None
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_deepseek_generation_uses_flash_selected_model(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AI_PROVIDER", "deepseek")
    captured: dict[str, object] = {}

    def fake_generate(
        lesson: Lesson,
        materials: list[LessonMaterial],
        api_key: str | None,
        selected_model: str | None = None,
    ) -> GeneratedOutline:
        captured["has_api_key"] = bool(api_key)
        captured["selected_model"] = selected_model
        return GeneratedOutline("flash 模型测试返回。", selected_model or "deepseek-v4-flash")

    monkeypatch.setattr(main.ai_provider, "generate_knowledge_outline_with_provider", fake_generate)
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
        await client.post(
            "/ai/settings",
            data={"api_key": "sk-" + "m" * 16 + "7777", "selected_model": "deepseek-v4-flash"},
            headers=SAME_ORIGIN_HEADERS,
        )

        response = await client.post(
            "/lessons/1/knowledge-outline/generate",
            headers=SAME_ORIGIN_HEADERS,
            follow_redirects=False,
        )

        assert response.status_code == 303
        assert captured["has_api_key"] is True
        assert captured["selected_model"] == "deepseek-v4-flash"
        with session_factory() as session:
            outline = session.scalar(select(KnowledgeOutline))
            assert outline is not None
            assert outline.generated_by_model == "deepseek-v4-flash"
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


def test_deepseek_prompt_filters_sensitive_material_information() -> None:
    lesson = Lesson(
        course_id=1,
        planned_lesson_id=None,
        week="1",
        lesson_no="1",
        hours="2",
        lesson_code="0402",
        title="WHERE 条件查询",
        content_summary="班级：23物联网2班\n讲解 WHERE 与 IN关键字。",
        status="draft",
    )
    material = LessonMaterial(
        lesson_id=1,
        material_type="pasted_text",
        title="虚构材料",
        content="\n".join(
            [
                "学校：示例学校",
                "学校名称：示例学校",
                "学校 | 示例学校",
                "教师：张老师",
                "任课教师：张老师",
                "任课老师：张老师",
                "班级：23物联网2班",
                "授课班级：23物联网2班",
                "授课班级 23物联网2班",
                "教学目标：掌握 WHERE 条件查询。",
                "重点：WHERE、IN关键字 的使用。",
                "难点：多个条件组合。",
            ]
        ),
    )

    prompt = build_knowledge_outline_prompt(lesson, [material])

    assert "示例学校" not in prompt
    assert "张老师" not in prompt
    assert "23物联网2班" not in prompt
    assert "教学目标" in prompt
    assert "WHERE" in prompt
    assert "IN关键字" in prompt
    assert "重点" in prompt
    assert "难点" in prompt


def test_knowledge_outline_prompt_contains_fixed_sections_and_disclaimers() -> None:
    lesson = Lesson(
        course_id=1,
        planned_lesson_id=None,
        week="1",
        lesson_no="1",
        hours="2",
        lesson_code="0402",
        title="WHERE 条件查询",
        content_summary="条件查询。",
        status="draft",
    )
    material = LessonMaterial(
        lesson_id=1,
        material_type="pasted_text",
        title="虚构材料",
        content="\n".join(
            [
                "学校：示例学校",
                "任课教师：张老师",
                "授课班级：23物联网2班",
                "教学目标：掌握 WHERE 条件查询。",
                "重点：理解数据筛选条件。",
            ]
        ),
    )

    prompt = build_knowledge_outline_prompt(lesson, [material])

    for section in [
        "本节课定位",
        "学习目标",
        "核心知识点",
        "知识结构",
        "重点与难点",
        "课程思政与职业素养融入点",
        "学生易错点",
        "课堂任务建议",
        "可测知识点与题型蓝图",
        "补充内容建议",
        "教师使用提示",
        "AI 草稿声明",
    ]:
        assert section in prompt
    assert "审阅、修改与确认" in prompt
    assert "严禁编造政策文件、政策原文、标准编号、行业规范条款、真实企业案例、真实数据来源" in prompt
    assert "以上课程思政与职业素养融入点为 AI 根据当前材料生成的参考建议" in prompt
    assert "以上题型蓝图仅供教师设计小测时参考" in prompt
    assert "必须至少包含 1 条与本节相关的课程思政 / 职业素养测试方向" in prompt
    assert "以上补充建议为 AI 根据当前材料生成的参考方向" in prompt
    assert "不得输出学校、教师姓名、真实班级等行政信息" in prompt
    assert "示例学校" not in prompt
    assert "张老师" not in prompt
    assert "23物联网2班" not in prompt


def test_deepseek_prompt_prioritizes_key_material_and_limits_length(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_PROMPT_MATERIAL_MAX_CHARS", "9000")
    lesson = Lesson(
        course_id=1,
        planned_lesson_id=None,
        week="1",
        lesson_no="1",
        hours="2",
        lesson_code="0402",
        title="WHERE 条件查询",
        content_summary="条件查询。",
        status="draft",
    )
    material = LessonMaterial(
        lesson_id=1,
        material_type="pasted_text",
        title="长材料",
        content="\n".join(
            [
                *(f"普通铺垫内容 {index}" for index in range(80)),
                "学校名称：示例学校",
                "教学目标：掌握 WHERE 子句。",
                "实验步骤：编写 SQL 条件查询。",
            ]
        ),
    )

    prompt = build_knowledge_outline_prompt(lesson, [material])

    assert len(prompt) <= 9000
    assert "教学目标" in prompt
    assert "实验步骤" in prompt
    assert "SQL" in prompt
    assert "示例学校" not in prompt


def test_deepseek_model_config_parses_allowed_models(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "DEEPSEEK_ALLOWED_MODELS",
        " deepseek-v4-flash,deepseek-v4-pro,,deepseek-v4-flash,deepseek-chat,deepseek-reasoner,unknown-model ",
    )
    monkeypatch.setenv("DEEPSEEK_DEFAULT_MODEL", "deepseek-v4-pro")

    assert get_allowed_deepseek_models() == ["deepseek-v4-flash", "deepseek-v4-pro"]
    assert get_default_deepseek_model() == "deepseek-v4-pro"
    assert is_allowed_deepseek_model("deepseek-v4-flash") is True
    assert is_allowed_deepseek_model("deepseek-v4-pro") is True
    assert is_allowed_deepseek_model("deepseek-chat") is False
    assert is_allowed_deepseek_model("deepseek-reasoner") is False
    assert is_allowed_deepseek_model("unknown-model") is False


def test_deepseek_model_config_falls_back_when_env_is_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEEPSEEK_ALLOWED_MODELS", "deepseek-chat,unknown-model,,")
    monkeypatch.setenv("DEEPSEEK_DEFAULT_MODEL", "unknown-model")

    assert get_allowed_deepseek_models() == ["deepseek-v4-flash", "deepseek-v4-pro"]
    assert get_default_deepseek_model() == "deepseek-v4-flash"
    assert get_deepseek_config().model == "deepseek-v4-flash"
    with pytest.raises(DeepSeekProviderError):
        get_deepseek_config("deepseek-chat")


def test_deepseek_config_accepts_v4_models_and_invalid_timeout_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_REQUEST_TIMEOUT_SECONDS", "bad")
    for model_name in ["deepseek-v4-pro", "deepseek-v4-flash"]:
        config = get_deepseek_config(model_name)
        assert config.model == model_name
        assert config.timeout_seconds == 60.0

    monkeypatch.setenv("AI_PROMPT_MATERIAL_MAX_CHARS", "bad")
    config = get_deepseek_config()
    assert config.prompt_material_max_chars == 12000


def test_deepseek_http_errors_do_not_keep_exception_chain_or_key(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_key = "sk-" + "h" * 16 + "5555"
    lesson = Lesson(
        course_id=1,
        planned_lesson_id=None,
        week="1",
        lesson_no="1",
        hours="2",
        lesson_code="0402",
        title="WHERE 条件查询",
        content_summary="条件查询。",
        status="draft",
    )

    class TimeoutClient:
        def __init__(self, timeout: float) -> None:
            self.timeout = timeout

        def __enter__(self) -> "TimeoutClient":
            return self

        def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
            return None

        def post(self, *args: object, **kwargs: object) -> httpx.Response:
            request = httpx.Request("POST", "https://api.example.test", headers={"Authorization": f"Bearer {fake_key}"})
            raise httpx.TimeoutException("timeout", request=request)

    monkeypatch.setattr("app.services.ai.deepseek_client.httpx.Client", TimeoutClient)
    with pytest.raises(DeepSeekProviderError) as timeout_error:
        generate_deepseek_knowledge_outline(lesson, [], fake_key)
    assert timeout_error.value.__cause__ is None
    assert fake_key not in str(timeout_error.value)

    class HttpErrorClient(TimeoutClient):
        def post(self, *args: object, **kwargs: object) -> httpx.Response:
            request = httpx.Request("POST", "https://api.example.test", headers={"Authorization": f"Bearer {fake_key}"})
            raise httpx.RequestError("network", request=request)

    monkeypatch.setattr("app.services.ai.deepseek_client.httpx.Client", HttpErrorClient)
    with pytest.raises(DeepSeekProviderError) as http_error:
        generate_deepseek_knowledge_outline(lesson, [], fake_key)
    assert http_error.value.__cause__ is None
    assert fake_key not in str(http_error.value)


@pytest.mark.anyio
async def test_can_generate_mock_knowledge_outline_without_materials(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_PROVIDER", "mock")
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

        response = await client.post(
            "/lessons/1/knowledge-outline/generate",
            headers=SAME_ORIGIN_HEADERS,
            follow_redirects=False,
        )

        assert response.status_code == 303
        assert response.headers["location"] == "/lessons/1/knowledge-outline"
        with session_factory() as session:
            outline = session.scalar(select(KnowledgeOutline))
            lesson = session.get(Lesson, 1)
            assert outline is not None
            assert lesson is not None
            assert outline.lesson_id == 1
            assert outline.generated_by_model == "mock-ai-v0.2"
            assert outline.status == "draft"
            assert outline.ai_raw_output == outline.edited_content
            assert lesson.title in outline.edited_content
            assert "当前课次尚未添加教学材料" in outline.edited_content
            assert "## 6. 课程思政与职业素养融入点" in outline.edited_content
            assert "## 9. 可测知识点与题型蓝图" in outline.edited_content
            assert "## 10. 补充内容建议" in outline.edited_content
            assert "## 12. AI 草稿声明" in outline.edited_content
            assert "仅供教师参考，需教师审阅、修改与确认" in outline.edited_content
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_mock_knowledge_outline_uses_lesson_material_keywords(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_PROVIDER", "mock")
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
        await client.post(
            "/lessons/1/materials",
            data={
                "title": "课堂材料",
                "material_type": "pasted_text",
                "content": "本节课练习 SELECT、WHERE、GROUP BY 和 HAVING。",
            },
            follow_redirects=False,
        )

        response = await client.post(
            "/lessons/1/knowledge-outline/generate",
            headers=SAME_ORIGIN_HEADERS,
            follow_redirects=False,
        )

        assert response.status_code == 303
        with session_factory() as session:
            outline = session.scalar(select(KnowledgeOutline))
            assert outline is not None
            assert "SELECT" in outline.edited_content
            assert "WHERE" in outline.edited_content
            assert "GROUP BY" in outline.edited_content
            assert "HAVING" in outline.edited_content
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_mock_knowledge_outline_filters_sensitive_material_information(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AI_PROVIDER", "mock")
    client, session_factory = _build_test_client(tmp_path)
    course = _create_course(session_factory)
    sensitive_material = "\n".join(
        [
            "学校：示例学校",
            "任课教师：张老师",
            "授课班级：23物联网2班",
            "授课地点：示例机房",
            "教学目标：掌握 WHERE 条件查询。",
            "重点：WHERE、IN关键字 的使用。",
            "难点：多个条件组合。",
        ]
    )
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
        await client.post(
            "/lessons/1/materials",
            data={
                "title": "含行政信息的虚构材料",
                "material_type": "pasted_text",
                "content": sensitive_material,
            },
            follow_redirects=False,
        )

        response = await client.post(
            "/lessons/1/knowledge-outline/generate",
            headers=SAME_ORIGIN_HEADERS,
            follow_redirects=False,
        )

        assert response.status_code == 303
        with session_factory() as session:
            material = session.scalar(select(LessonMaterial))
            outline = session.scalar(select(KnowledgeOutline))
            assert material is not None
            assert outline is not None
            assert "示例学校" in material.content
            assert "张老师" in material.content
            assert "23物联网2班" in material.content
            assert "示例学校" not in outline.edited_content
            assert "张老师" not in outline.edited_content
            assert "23物联网2班" not in outline.edited_content
            assert "教学目标" in outline.edited_content
            assert "WHERE" in outline.edited_content
            assert "IN关键字" in outline.edited_content
            assert "重点" in outline.edited_content
            assert "难点" in outline.edited_content
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_knowledge_outline_page_and_save_reviewed_content(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AI_PROVIDER", "mock")
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
        await client.post(
            "/lessons/1/knowledge-outline/generate",
            headers=SAME_ORIGIN_HEADERS,
            follow_redirects=False,
        )

        page_response = await client.get("/lessons/1/knowledge-outline")

        assert page_response.status_code == 200
        assert "知识主干内容" in page_response.text
        assert "mock-ai-v0.2" in page_response.text
        assert "默认基于本课次下已添加资料生成" in page_response.text
        assert "/ai/settings?next=/lessons/1/knowledge-outline" in page_response.text

        save_response = await client.post(
            "/knowledge-outlines/1/save",
            data={"edited_content": "教师复核后的知识主干：保留 WHERE 条件查询重点。"},
            follow_redirects=False,
        )

        assert save_response.status_code == 303
        assert save_response.headers["location"] == "/lessons/1/knowledge-outline"
        with session_factory() as session:
            outline = session.get(KnowledgeOutline, 1)
            assert outline is not None
            assert outline.status == "reviewed"
            assert outline.edited_content == "教师复核后的知识主干：保留 WHERE 条件查询重点。"
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()
