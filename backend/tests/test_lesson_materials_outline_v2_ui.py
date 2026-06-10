from collections.abc import Generator
from pathlib import Path

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app import main
from app.db.base import create_database_tables
from app.models.course import Course
from app.models.course_plan import CoursePlanUpload, PlannedLesson
from app.models.knowledge_outline import KnowledgeOutline
from app.models.lesson import Lesson, LessonMaterial
from app.services.ai.fallback import (
    FALLBACK_REASON_MISSING_API_KEY,
    MISSING_API_KEY_FALLBACK_MESSAGE,
)
from app.services.ai.provider import GeneratedOutline


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def _build_test_client(tmp_path: Path) -> tuple[httpx.AsyncClient, sessionmaker[Session]]:
    database_path = tmp_path / "test-materials-outline-v2.sqlite"
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


def _create_lesson(session_factory: sessionmaker[Session], with_outline: bool = False) -> int:
    with session_factory() as session:
        course = Course(title="传感器应用基础", semester="2025-2026-2", status="draft")
        session.add(course)
        session.flush()
        lesson = Lesson(
            course_id=course.id,
            week="3",
            lesson_no="2",
            hours="2",
            lesson_code="0302",
            title="光敏传感器实验",
            content_summary="认识光敏传感器并完成基础实验。",
            homework_hint="整理实验现象。",
            status="draft",
        )
        session.add(lesson)
        session.flush()
        material = LessonMaterial(
            lesson_id=lesson.id,
            material_type="pasted_text",
            title="实验步骤",
            content="连接光敏传感器，观察输入信号和输出信号变化。",
        )
        session.add(material)
        if with_outline:
            outline = KnowledgeOutline(
                lesson_id=lesson.id,
                ai_raw_output="知识主干草稿",
                edited_content="知识主干草稿",
                status="reviewed",
                generated_by_model="local-structured-draft",
            )
            session.add(outline)
        session.commit()
        return lesson.id


@pytest.mark.anyio
async def test_lessons_and_detail_pages_link_to_materials_outline_v2(tmp_path: Path) -> None:
    client, session_factory = _build_test_client(tmp_path)
    lesson_id = _create_lesson(session_factory)
    with session_factory() as session:
        lesson = session.get(Lesson, lesson_id)
        assert lesson is not None
        course_id = lesson.course_id

    try:
        lessons_response = await client.get(f"/courses/{course_id}/lessons")
        detail_response = await client.get(f"/lessons/{lesson_id}")

        assert lessons_response.status_code == 200
        assert "智学导评 V0.2" in lessons_response.text
        assert "课程中心" in lessons_response.text
        assert "|" in lessons_response.text
        assert "查看详情" not in lessons_response.text
        assert "作业提示" not in lessons_response.text
        assert "教学内容摘要" not in lessons_response.text
        assert "课程资料整理" in lessons_response.text
        assert "资料与主干" not in lessons_response.text
        assert "资料主干" not in lessons_response.text
        assert "学情测试" in lessons_response.text
        assert "导学案" in lessons_response.text
        assert f"/ui-v2/lessons/{lesson_id}/materials-outline" in lessons_response.text
        assert detail_response.status_code == 200
        assert "进入 V2：课次资料与知识主干" in detail_response.text
        assert f"/ui-v2/lessons/{lesson_id}/materials-outline" in detail_response.text
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_lessons_list_uses_planned_lesson_notes_for_summary_column(tmp_path: Path) -> None:
    client, session_factory = _build_test_client(tmp_path)
    with session_factory() as session:
        course = Course(title="电工电子基础", semester="2025-2026-2", status="draft")
        session.add(course)
        session.flush()
        upload = CoursePlanUpload(
            course_id=course.id,
            original_filename="plan.xlsx",
            file_path="/tmp/plan.xlsx",
            parsed_status="success",
        )
        session.add(upload)
        session.flush()
        planned = PlannedLesson(
            course_plan_upload_id=upload.id,
            course_id=course.id,
            week="5",
            lesson_no="1",
            hours="2",
            lesson_code="0501",
            lesson_title="三极管放大电路",
            content_raw="内部原始内容不应直接展示",
            homework="完成练习",
            notes="重点观察输入信号和输出信号变化",
            status="confirmed",
        )
        session.add(planned)
        session.flush()
        lesson = Lesson(
            course_id=course.id,
            planned_lesson_id=planned.id,
            week="5",
            lesson_no="1",
            hours="2",
            lesson_code="0501",
            title="三极管放大电路",
            content_summary="内部原始内容不应直接展示",
            homework_hint="完成练习",
            status="draft",
        )
        session.add(lesson)
        session.commit()
        course_id = course.id
    try:
        response = await client.get(f"/courses/{course_id}/lessons")

        assert response.status_code == 200
        assert "教学内容摘要" in response.text
        assert "重点观察输入信号和输出信号变化" in response.text
        assert "内部原始内容不应直接展示" not in response.text
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_lesson_materials_outline_v2_page_shows_materials_and_forms(tmp_path: Path) -> None:
    client, session_factory = _build_test_client(tmp_path)
    lesson_id = _create_lesson(session_factory)
    try:
        response = await client.get(f"/ui-v2/lessons/{lesson_id}/materials-outline")

        assert response.status_code == 200
        assert "课程资料整理" in response.text
        assert "课次资料与知识主干" not in response.text
        assert "传感器应用基础" in response.text
        assert "光敏传感器实验" in response.text
        assert "周次：3" in response.text
        assert "课次：2" in response.text
        assert "学时：2" in response.text
        assert "编码：0302" in response.text
        assert "上传课次资料" in response.text
        assert "txt / md / docx / pptx / xlsx" in response.text
        assert "xlsx 将提取表格文本" in response.text
        assert "暂不支持 xls、PDF、图片或扫描件" in response.text
        assert f'action="/lessons/{lesson_id}/materials"' in response.text
        assert f'name="return_to" value="/ui-v2/lessons/{lesson_id}/materials-outline"' in response.text
        assert "资料类别" in response.text
        assert 'name="material_category"' in response.text
        assert "教案" in response.text
        assert "PPT / 课件" in response.text
        assert 'name="files"' in response.text
        assert 'accept=".txt,.md,.docx,.pptx,.xlsx"' in response.text
        assert "粘贴补充资料" in response.text
        assert 'name="content"' in response.text
        assert "实验步骤" in response.text
        assert "资料类别：粘贴文本" in response.text
        assert "连接光敏传感器" in response.text
        assert f'action="/lesson-materials/' in response.text
        assert "生成知识主干" in response.text
        assert "data-ai-generation-form" in response.text
        assert 'data-status-target="outline-v2-generation-hint"' in response.text
        assert "智学导评 V0.2" in response.text
        assert "|" in response.text
        assert "课程资料整理" in response.text
        assert "整理资料，形成知识主干与备课参考" in response.text
        assert "了解学生课前基础" in response.text
        assert "形成学生学习单与任务包" in response.text
        assert "返回课程中心 V2" not in response.text
        assert "返回课程中心" in response.text
        assert "返回正式课次列表" in response.text
        assert "进入课前学情测试" in response.text
        assert "进入学生导学案" in response.text
        assert f"/ui-v2/lessons/{lesson_id}/learning-guides" in response.text
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_lesson_materials_outline_v2_shows_outline_editor_when_outline_exists(tmp_path: Path) -> None:
    client, session_factory = _build_test_client(tmp_path)
    lesson_id = _create_lesson(session_factory, with_outline=True)
    try:
        response = await client.get(f"/ui-v2/lessons/{lesson_id}/materials-outline")

        assert response.status_code == 200
        assert "知识主干草稿" in response.text
        assert "保存教师修改" in response.text
        assert "已由教师复核，可继续修改或重新生成。" in response.text
        assert "正在生成知识主干" not in response.text
        assert 'action="/knowledge-outlines/' in response.text
        assert '/save"' in response.text
        assert f'name="return_to" value="/ui-v2/lessons/{lesson_id}/materials-outline"' in response.text
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_material_post_with_return_to_redirects_back_to_v2(tmp_path: Path) -> None:
    client, session_factory = _build_test_client(tmp_path)
    lesson_id = _create_lesson(session_factory)
    return_to = f"/ui-v2/lessons/{lesson_id}/materials-outline"
    try:
        response = await client.post(
            f"/lessons/{lesson_id}/materials",
            data={
                "input_mode": "pasted_text",
                "material_category": "lesson_plan",
                "title": "",
                "content": "课堂补充说明",
                "return_to": return_to,
            },
        )

        assert response.status_code == 303
        assert response.headers["location"] == return_to
        with session_factory() as session:
            material = session.query(LessonMaterial).filter(LessonMaterial.lesson_id == lesson_id).order_by(LessonMaterial.id.desc()).first()
            assert material is not None
            assert material.material_type == "lesson_plan"
            assert material.title == "0302-教案"
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_material_post_rejects_external_return_to_and_keeps_legacy_default(tmp_path: Path) -> None:
    client, session_factory = _build_test_client(tmp_path)
    lesson_id = _create_lesson(session_factory)
    try:
        response = await client.post(
            f"/lessons/{lesson_id}/materials",
            data={
                "material_type": "pasted_text",
                "title": "补充说明",
                "content": "课堂补充说明",
                "return_to": "https://evil.example/path",
            },
        )

        assert response.status_code == 303
        assert response.headers["location"] == f"/lessons/{lesson_id}"
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_material_post_without_return_to_keeps_legacy_redirect(tmp_path: Path) -> None:
    client, session_factory = _build_test_client(tmp_path)
    lesson_id = _create_lesson(session_factory)
    try:
        response = await client.post(
            f"/lessons/{lesson_id}/materials",
            data={"material_type": "pasted_text", "title": "补充说明", "content": "课堂补充说明"},
        )

        assert response.status_code == 303
        assert response.headers["location"] == f"/lessons/{lesson_id}"
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_delete_material_with_return_to_redirects_to_v2(tmp_path: Path) -> None:
    client, session_factory = _build_test_client(tmp_path)
    lesson_id = _create_lesson(session_factory)
    return_to = f"/ui-v2/lessons/{lesson_id}/materials-outline"
    with session_factory() as session:
        material = session.query(LessonMaterial).filter(LessonMaterial.lesson_id == lesson_id).first()
        assert material is not None
        material_id = material.id

    try:
        response = await client.post(f"/lesson-materials/{material_id}/delete", data={"return_to": return_to})

        assert response.status_code == 303
        assert response.headers["location"] == return_to
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_save_knowledge_outline_with_return_to_redirects_to_v2(tmp_path: Path) -> None:
    client, session_factory = _build_test_client(tmp_path)
    lesson_id = _create_lesson(session_factory, with_outline=True)
    return_to = f"/ui-v2/lessons/{lesson_id}/materials-outline"
    with session_factory() as session:
        outline = session.query(KnowledgeOutline).filter(KnowledgeOutline.lesson_id == lesson_id).first()
        assert outline is not None
        outline_id = outline.id

    try:
        response = await client.post(
            f"/knowledge-outlines/{outline_id}/save",
            data={"edited_content": "教师修改后的知识主干", "return_to": return_to},
        )

        assert response.status_code == 303
        assert response.headers["location"] == return_to
        with session_factory() as session:
            outline = session.get(KnowledgeOutline, outline_id)
            assert outline is not None
            assert outline.edited_content == "教师修改后的知识主干"
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_generate_knowledge_outline_without_api_key_shows_v2_fallback_message(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AI_PROVIDER", "deepseek")
    client, session_factory = _build_test_client(tmp_path)
    lesson_id = _create_lesson(session_factory)
    return_to = f"/ui-v2/lessons/{lesson_id}/materials-outline"

    async def run_inline(func: object, *args: object, **kwargs: object) -> object:
        return func(*args, **kwargs)  # type: ignore[misc]

    def fail_if_called(*args: object, **kwargs: object) -> tuple[str, str]:
        raise AssertionError("无 API Key 时不应调用 DeepSeek")

    monkeypatch.setattr(main, "run_in_threadpool", run_inline)
    monkeypatch.setattr(main.ai_provider, "generate_deepseek_knowledge_outline", fail_if_called)
    try:
        response = await client.post(
            f"/lessons/{lesson_id}/knowledge-outline/generate",
            data={"return_to": return_to},
            headers={"origin": "http://testserver"},
            follow_redirects=False,
        )

        assert response.status_code == 303
        assert response.headers["location"] == f"{return_to}?ai_fallback_reason={FALLBACK_REASON_MISSING_API_KEY}"
        with session_factory() as session:
            outline = session.query(KnowledgeOutline).filter(KnowledgeOutline.lesson_id == lesson_id).first()
            assert outline is not None
            assert outline.generated_by_model == "local-structured-draft"

        page = await client.get(response.headers["location"])
        assert page.status_code == 200
        assert MISSING_API_KEY_FALLBACK_MESSAGE in page.text
        assert f'<p class="notice ai-fallback-notice">{MISSING_API_KEY_FALLBACK_MESSAGE}</p>' in page.text
        assert f'<p class="alert">{MISSING_API_KEY_FALLBACK_MESSAGE}</p>' not in page.text
        assert "Traceback" not in page.text
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_generate_knowledge_outline_with_return_to_redirects_to_v2(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, session_factory = _build_test_client(tmp_path)
    lesson_id = _create_lesson(session_factory)
    return_to = f"/ui-v2/lessons/{lesson_id}/materials-outline"

    async def run_inline(func: object, *args: object, **kwargs: object) -> object:
        return func(*args, **kwargs)  # type: ignore[misc]

    def fake_generate(*args: object, **kwargs: object) -> GeneratedOutline:
        return GeneratedOutline(content="V2 知识主干", model_name="fake-model")

    monkeypatch.setattr(main, "run_in_threadpool", run_inline)
    monkeypatch.setattr(main.ai_provider, "generate_knowledge_outline_with_provider", fake_generate)
    try:
        response = await client.post(
            f"/lessons/{lesson_id}/knowledge-outline/generate",
            data={"return_to": return_to},
            headers={"origin": "http://testserver"},
        )

        assert response.status_code == 303
        assert response.headers["location"] == return_to
        with session_factory() as session:
            outline = session.query(KnowledgeOutline).filter(KnowledgeOutline.lesson_id == lesson_id).first()
            assert outline is not None
            assert outline.edited_content == "V2 知识主干"
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_lesson_materials_outline_v2_does_not_change_legacy_pages(tmp_path: Path) -> None:
    client, session_factory = _build_test_client(tmp_path)
    lesson_id = _create_lesson(session_factory, with_outline=True)
    try:
        detail_response = await client.get(f"/lessons/{lesson_id}")
        outline_response = await client.get(f"/lessons/{lesson_id}/knowledge-outline")

        assert detail_response.status_code == 200
        assert "课次详情" in detail_response.text
        assert "lesson-materials-v2" not in detail_response.text
        assert outline_response.status_code == 200
        assert "知识主干" in outline_response.text
        assert "知识主干草稿" in outline_response.text
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()
