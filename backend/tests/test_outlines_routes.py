from pathlib import Path

import pytest
from sqlalchemy import select

from app import main
from app.models.course_plan import PlannedLesson
from app.models.knowledge_outline import KnowledgeOutline
from app.models.lesson import Lesson, LessonMaterial
from app.services.ai.deepseek_client import (
    DeepSeekProviderError,
)
from app.services.ai.provider import GeneratedOutline
from tests.test_course_plan_pages import (
    SAME_ORIGIN_HEADERS,
    _build_test_client,
    _create_course,
    _database_contains_text,
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
async def test_deepseek_generation_without_api_key_uses_local_structured_draft(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
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
            headers=SAME_ORIGIN_HEADERS,
            follow_redirects=False,
        )

        assert response.status_code == 303
        assert response.headers["location"] == "/lessons/1/knowledge-outline"
        with session_factory() as session:
            outline = session.scalar(select(KnowledgeOutline))
            assert outline is not None
            assert outline.generated_by_model == "local-structured-draft"
            assert "本地结构化草稿" in outline.edited_content
            assert "仅供教师参考，需教师审阅、修改与确认" in outline.edited_content
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
async def test_generated_outline_is_sanitized_before_saving(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AI_PROVIDER", "deepseek")

    def fake_generate(
        lesson: Lesson,
        materials: list[LessonMaterial],
        api_key: str | None,
        selected_model: str | None = None,
    ) -> GeneratedOutline:
        return GeneratedOutline(
            "\n".join(
                [
                    "# 测试知识主干",
                    "授课班级：23物联网2班",
                    "本课面向23物联网2班开展条件查询练习。",
                    "张老师提醒学生核验 WHERE 查询结果。",
                    "student 表、score 表、学生表、教师表用于教学示例。",
                ]
            ),
            selected_model or "deepseek-v4-flash",
        )

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
            data={"api_key": "sk-output-sanitize-abcd", "selected_model": "deepseek-v4-pro"},
            headers=SAME_ORIGIN_HEADERS,
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
            assert "23物联网2班" not in outline.ai_raw_output
            assert "23物联网2班" not in outline.edited_content
            assert "某班级" in outline.ai_raw_output
            assert "张老师" not in outline.ai_raw_output
            assert "某教师" in outline.ai_raw_output
            assert "student 表" in outline.ai_raw_output
            assert "score 表" in outline.ai_raw_output
            assert "学生表" in outline.ai_raw_output
            assert "教师表" in outline.ai_raw_output
            assert outline.ai_raw_output == outline.edited_content
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
            for section in [
                "## 1. 本节课定位",
                "## 2. 学习目标",
                "## 3. 核心知识点",
                "## 4. 知识结构",
                "## 5. 重点与难点",
                "## 6. 材料结构分析与教学重心提醒",
                "## 7. 课程思政与职业素养融入点",
                "## 8. 学生易错点",
                "## 9. 课堂任务建议",
                "## 10. 可测知识点与题型蓝图",
                "## 11. 补充内容建议",
                "## 12. 教师使用提示",
                "## 13. AI 草稿声明",
            ]:
                assert section in outline.edited_content
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
