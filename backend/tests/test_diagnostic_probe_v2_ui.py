from collections.abc import Generator
from pathlib import Path

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app import main
from app.db.base import create_database_tables
from app.models.course import Course
from app.models.knowledge_outline import KnowledgeOutline
from app.models.lesson import Lesson
from app.models.lesson_draft import LessonDraft


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def _build_test_client(tmp_path: Path) -> tuple[httpx.AsyncClient, sessionmaker[Session]]:
    database_path = tmp_path / "test-diagnostic-v2.sqlite"
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


def _probe_content() -> str:
    return """# 课前学情测试草稿

### 题目 1
- 题型：单选题
- 题干：光敏传感器实验前应先确认什么？
- 选项：A. 接线与供电；B. 字体颜色；C. 座位；D. 无关内容
- 参考答案：A
- 简短解析：接线与供电会影响实验安全和数据可靠性。
- 诊断点：安全规范
- 难度：基础

### 题目 2
- 题型：判断题
- 题干：课前学情测试不作为正式考试成绩。
- 参考答案：正确
- 简短解析：它用于判断学习起点。
- 诊断点：前测定位
- 难度：中等
"""


def _create_lesson(session_factory: sessionmaker[Session], with_draft: bool = True) -> int:
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
        outline = KnowledgeOutline(
            lesson_id=lesson.id,
            ai_raw_output="知识主干草稿",
            edited_content="知识主干草稿",
            status="reviewed",
            generated_by_model="local-structured-draft",
        )
        session.add(outline)
        if with_draft:
            session.add(
                LessonDraft(
                    lesson_id=lesson.id,
                    source_outline_id=outline.id,
                    draft_type="diagnostic_probe",
                    title="光敏传感器实验｜课前学情测试",
                    content=_probe_content(),
                    status="draft",
                    generated_by="local-structured-draft",
                )
            )
        session.commit()
        return lesson.id


@pytest.mark.anyio
async def test_diagnostic_probe_v2_page_renders_cards_stats_and_actions(tmp_path: Path) -> None:
    client, session_factory = _build_test_client(tmp_path)
    lesson_id = _create_lesson(session_factory, with_draft=True)
    try:
        response = await client.get(f"/ui-v2/lessons/{lesson_id}/diagnostic-probe")

        assert response.status_code == 200
        text = response.text
        assert "智学导评 V0.2" in text
        assert "课程中心" in text
        assert "正式课次" in text
        assert "课前学情测试" in text
        assert "不作为正式考试成绩" in text
        assert "选择课程" in text
        assert "课程资料整理" in text
        assert "整理资料，形成知识主干与备课参考" in text
        assert "学生导学案" in text
        assert "前后阶段" in text
        assert "进入课程资料整理" in text
        assert "进入学生导学案" in text
        assert '<a class="flow-step-v2"' not in text
        assert f"/ui-v2/lessons/{lesson_id}/materials-outline" in text
        assert f"/lessons/{lesson_id}/drafts" in text
        assert f'action="/lessons/{lesson_id}/drafts/generate/diagnostic_probe"' in text
        assert 'name="return_to" value="/ui-v2/lessons/' in text
        assert "data-ai-generation-form" in text
        assert 'data-status-target="diagnostic-v2-generation-hint"' in text
        assert "AI 正在生成课前学情测试" in text
        assert "题型分布" in text
        assert "难度分布" in text
        assert "单选题" in text
        assert "判断题" in text
        assert "基础" in text
        assert "中等" in text
        assert "50.0%" in text
        assert "编辑本题" in text
        assert "删除本题" in text
        assert "题卡化预览与轻量编辑" not in text
        assert "本节习题预览" in text
        assert "保存本题修改" in text
        assert "更新本题预览" not in text
        assert "高级编辑：查看完整 Markdown 草稿" in text
        assert "如果题目解析不完整，或需要批量调整原文，可展开编辑完整 Markdown。" in text
        assert text.index("如果题目解析不完整，或需要批量调整原文，可展开编辑完整 Markdown。") < text.index("<details class=\"diagnostic-editor-details-v2\"")
        assert "保存全部修改" not in text
        assert "保存完整草稿" in text
        assert "导出学习通题库模板" not in text
        assert "导出学习通习题文件" in text
        assert "不会自动发布到学习通" in text
        assert "学生端" not in text
        assert "自动评分" not in text
        assert "正式考试成绩统计" not in text
        for forbidden in ["guide_low", "guide_mid", "guide_high"]:
            assert forbidden not in text
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_diagnostic_probe_v2_empty_state_and_legacy_drafts_page_still_work(tmp_path: Path) -> None:
    client, session_factory = _build_test_client(tmp_path)
    lesson_id = _create_lesson(session_factory, with_draft=False)
    try:
        v2_response = await client.get(f"/ui-v2/lessons/{lesson_id}/diagnostic-probe")
        legacy_response = await client.get(f"/lessons/{lesson_id}/drafts")

        assert v2_response.status_code == 200
        assert "生成后展示题型与难度分布" in v2_response.text
        assert "当前还没有课前学情测试草稿" in v2_response.text
        assert "高级编辑：查看完整 Markdown 草稿" not in v2_response.text
        assert legacy_response.status_code == 200
        assert "课前学情与学生导学案" in legacy_response.text
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_v2_entry_links_point_to_diagnostic_probe_page(tmp_path: Path) -> None:
    client, session_factory = _build_test_client(tmp_path)
    lesson_id = _create_lesson(session_factory, with_draft=True)
    with session_factory() as session:
        lesson = session.get(Lesson, lesson_id)
        assert lesson is not None
        course_id = lesson.course_id
    try:
        lessons_response = await client.get(f"/courses/{course_id}/lessons")
        materials_response = await client.get(f"/ui-v2/lessons/{lesson_id}/materials-outline")

        assert lessons_response.status_code == 200
        assert f"/ui-v2/lessons/{lesson_id}/diagnostic-probe" in lessons_response.text
        assert "学情测试" in lessons_response.text
        assert materials_response.status_code == 200
        assert "进入课前学情测试" in materials_response.text
        assert f"/ui-v2/lessons/{lesson_id}/diagnostic-probe" in materials_response.text
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_diagnostic_probe_v2_generate_save_and_export_return_to_v2(tmp_path: Path) -> None:
    client, session_factory = _build_test_client(tmp_path)
    lesson_id = _create_lesson(session_factory, with_draft=True)
    return_to = f"/ui-v2/lessons/{lesson_id}/diagnostic-probe"
    with session_factory() as session:
        draft = session.query(LessonDraft).filter_by(lesson_id=lesson_id, draft_type="diagnostic_probe").one()
        draft_id = draft.id
    try:
        save_response = await client.post(
            f"/lessons/{lesson_id}/drafts/{draft_id}/save",
            data={"title": "修改后的前测", "content": _probe_content(), "return_to": return_to},
            follow_redirects=False,
        )
        export_response = await client.post(
            f"/lessons/{lesson_id}/drafts/{draft_id}/export-chaoxing",
            data={"return_to": return_to},
            follow_redirects=False,
        )

        assert save_response.status_code == 303
        assert save_response.headers["location"] == return_to
        assert export_response.status_code == 303
        assert export_response.headers["location"].startswith(f"{return_to}?chaoxing_file=")
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()
