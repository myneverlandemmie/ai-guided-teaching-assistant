from pathlib import Path

import pytest
from sqlalchemy import select

from app import main
from app.models.course_plan import PlannedLesson
from app.models.knowledge_outline import KnowledgeOutline
from tests.test_course_plan_pages import (
    SAME_ORIGIN_HEADERS,
    _build_test_client,
    _create_course,
    _upload_sample_plan,
    anyio_backend,
    inline_threadpool_for_tests,
)


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
        assert "课次任务面板" in response.text
        assert "AI 配置" in response.text
        assert "课程知识主干" in response.text
        assert "课前学情测试" in response.text
        assert "学生导学案" in response.text
        assert "自动批阅演示" in response.text
        assert "规划中" in response.text
        assert "前往课前学情测试" in response.text
        assert "前往学生导学案" in response.text
        assert "生成知识主干" in response.text
        assert "/lessons/1/knowledge-outline" in response.text
        assert "/ai/settings?next=/lessons/1" in response.text
        assert "默认基于本课次下已添加资料生成" in response.text
        assert "如果 PPT 覆盖多个课次或整章内容" in response.text
        assert "必须由教师复核后使用" in response.text
        assert 'id="lesson-detail-outline-generation-form"' in response.text
        assert "data-outline-generation-form" in response.text
        assert 'data-loading-target="lesson-detail-outline-generation-hint"' in response.text
        assert 'id="lesson-detail-outline-generation-button"' in response.text
        assert "data-outline-generation-button" in response.text
        assert 'id="lesson-detail-outline-generation-hint"' in response.text
        assert "display:none" in response.text
        assert 'onsubmit="return handleOutlineGenerationSubmit(this);"' in response.text
        assert "handleOutlineGenerationSubmit" in response.text
        assert "AI 正在生成，请稍候..." in response.text
        assert "可能需要几十秒" in response.text
        assert "服务繁忙" in response.text
        assert "网络波动" in response.text
        assert "超时" in response.text
        assert "请勿重复点击、刷新页面或关闭窗口" in response.text
        assert "生成失败时可稍后重试" in response.text
        assert "/lessons/1/drafts" in response.text
        assert "/demo-grading/sql" not in response.text
        assert "/demo-grading/python" not in response.text
        assert "/demo-grading/c" not in response.text
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
        assert "本地结构化草稿" in page_response.text
        assert "mock-ai-v0.2" not in page_response.text
        assert "默认基于本课次下已添加资料生成" in page_response.text
        assert "/ai/settings?next=/lessons/1/knowledge-outline" in page_response.text
        assert "前往课前学情与学生导学案" in page_response.text
        assert "/lessons/1/drafts" in page_response.text

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


@pytest.mark.anyio
async def test_knowledge_outline_page_shows_generation_hint_and_disable_script(
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

        page_response = await client.get("/lessons/1/knowledge-outline")

        assert page_response.status_code == 200
        assert "正在生成知识主干" in page_response.text
        assert "使用真实 AI 时" in page_response.text
        assert "可能需要几十秒" in page_response.text
        assert "服务繁忙" in page_response.text
        assert "网络波动" in page_response.text
        assert "超时" in page_response.text
        assert "请勿重复点击、刷新页面或关闭窗口" in page_response.text
        assert "生成失败时可稍后重试" in page_response.text
        assert "生成内容需教师审核、修改与确认" in page_response.text
        assert 'id="outline-generation-form"' in page_response.text
        assert "data-outline-generation-form" in page_response.text
        assert 'data-loading-target="outline-generation-hint"' in page_response.text
        assert 'id="outline-generation-button"' in page_response.text
        assert "data-outline-generation-button" in page_response.text
        assert 'id="outline-generation-hint"' in page_response.text
        assert "data-outline-generation-hint" in page_response.text
        assert "display:none" in page_response.text
        assert 'onsubmit="return handleOutlineGenerationSubmit(this);"' in page_response.text
        assert "handleOutlineGenerationSubmit" in page_response.text
        assert "AI 正在生成，请稍候..." in page_response.text
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()
