from pathlib import Path

import pytest
from openpyxl import load_workbook
from sqlalchemy import select

from app import main
from app.models.course import Course
from app.models.lesson import Lesson
from app.models.lesson_draft import LessonDraft
from app.services.ai.lesson_draft_service import build_chaoxing_catalog
from tests.test_course_plan_pages import (
    _build_test_client,
    _create_course,
    _create_first_lesson,
    _create_reviewed_outline,
    anyio_backend,
    inline_threadpool_for_tests,
)


@pytest.mark.anyio
async def test_diagnostic_probe_exports_chaoxing_template(tmp_path: Path) -> None:
    client, session_factory = _build_test_client(tmp_path)
    course = _create_course(session_factory)
    try:
        await _create_first_lesson(client, session_factory, course)
        _create_reviewed_outline(session_factory)
        await client.post("/lessons/1/drafts/generate/diagnostic_probe", follow_redirects=False)
        with session_factory() as session:
            saved_course = session.get(Course, course.id)
            lesson = session.get(Lesson, 1)
            assert saved_course is not None
            assert lesson is not None
            saved_course.title = "数据库基础"
            lesson.lesson_code = "0406"
            lesson.title = "分组查询"
            session.commit()
            draft = session.scalar(select(LessonDraft).where(LessonDraft.draft_type == "diagnostic_probe"))
            assert draft is not None
            draft_id = draft.id

        export_response = await client.post(
            f"/lessons/1/drafts/{draft_id}/export-chaoxing",
            follow_redirects=False,
        )

        assert export_response.status_code == 303
        assert "chaoxing_file=" in export_response.headers["location"]
        export_files = list((tmp_path / "exports" / "chaoxing").glob("*.xlsx"))
        assert len(export_files) == 1
        workbook = load_workbook(export_files[0])
        worksheet = workbook["课程题库"]
        headers = [cell.value for cell in worksheet[1]]
        for header in ["目录", "题目类型", "大题题干", "正确答案", "答案解析", "难易度", "知识点", "标签", "选项数", "选项A", "选项B"]:
            assert header in headers
        rows = list(worksheet.iter_rows(min_row=2, values_only=True))
        assert len(rows) >= 5
        catalogs = {row[0] for row in rows}
        assert "/数据库基础/0406-分组查询" in catalogs
        assert all("智学导评" not in str(catalog) for catalog in catalogs)
        question_types = {row[1] for row in rows}
        assert {"单选题", "判断题", "填空题"}.issubset(question_types)
        judgment_row = next(row for row in rows if row[1] == "判断题")
        assert judgment_row[10] == 2
        assert judgment_row[11] == "正确"
        assert judgment_row[12] == "错误"

        page_response = await client.get(export_response.headers["location"])
        assert page_response.status_code == 200
        assert "下载学习通题库模板" in page_response.text
        assert "/exports/chaoxing/" in page_response.text
        assert "学习通 API" in page_response.text
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


def test_chaoxing_catalog_falls_back_without_course_name() -> None:
    lesson = Lesson(
        id=1,
        course_id=1,
        planned_lesson_id=None,
        week="1",
        lesson_no="1",
        hours="2",
        lesson_code="0406",
        title="分组查询",
        content_summary="分组查询",
        status="draft",
    )

    assert build_chaoxing_catalog(lesson) == "/0406-分组查询"


@pytest.mark.anyio
async def test_guide_low_can_download_markdown(tmp_path: Path) -> None:
    client, session_factory = _build_test_client(tmp_path)
    course = _create_course(session_factory)
    try:
        await _create_first_lesson(client, session_factory, course)
        _create_reviewed_outline(session_factory)
        await client.post("/lessons/1/drafts/generate/guide_low", follow_redirects=False)
        with session_factory() as session:
            draft = session.scalar(select(LessonDraft).where(LessonDraft.draft_type == "guide_low"))
            assert draft is not None
            draft_id = draft.id
            expected_content = draft.content

        response = await client.get(f"/lessons/1/drafts/{draft_id}/download-md")

        assert response.status_code == 200
        assert "text/markdown" in response.headers["content-type"]
        assert response.text == expected_content
        assert "学习导航" in response.text
        assert "rule-based" not in response.text
        assert "rule_based" not in response.text
        assert "mock" not in response.text
        markdown_file = tmp_path / "exports" / "guides" / "lesson_1_core_learning_guide.md"
        assert markdown_file.exists()
        assert markdown_file.read_text(encoding="utf-8") == expected_content
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()
