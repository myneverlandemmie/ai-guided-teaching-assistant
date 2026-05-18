from collections.abc import Generator
from pathlib import Path

import httpx
import pytest
from docx import Document
from pptx import Presentation
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app import main
from app.db.base import create_database_tables
from app.models.course import Course
from app.models.course_plan import CoursePlanUpload, PlannedLesson
from app.models.knowledge_outline import KnowledgeOutline
from app.models.lesson import Lesson, LessonMaterial


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
        assert "默认基于本课次下已添加资料生成" in response.text
        assert "如果 PPT 覆盖多个课次或整章内容" in response.text
        assert "必须由教师复核后使用" in response.text
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_can_generate_mock_knowledge_outline_without_materials(tmp_path: Path) -> None:
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

        response = await client.post("/lessons/1/knowledge-outline/generate", follow_redirects=False)

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
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_mock_knowledge_outline_uses_lesson_material_keywords(tmp_path: Path) -> None:
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

        response = await client.post("/lessons/1/knowledge-outline/generate", follow_redirects=False)

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
async def test_mock_knowledge_outline_filters_sensitive_material_information(tmp_path: Path) -> None:
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

        response = await client.post("/lessons/1/knowledge-outline/generate", follow_redirects=False)

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
async def test_knowledge_outline_page_and_save_reviewed_content(tmp_path: Path) -> None:
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
        await client.post("/lessons/1/knowledge-outline/generate", follow_redirects=False)

        page_response = await client.get("/lessons/1/knowledge-outline")

        assert page_response.status_code == 200
        assert "知识主干内容" in page_response.text
        assert "mock-ai-v0.2" in page_response.text
        assert "默认基于本课次下已添加资料生成" in page_response.text

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
