from pathlib import Path

import pytest
from sqlalchemy import select

from app import main
from app.services.ai.deepseek_client import DeepSeekProviderError
from app.services.ai.fallback import (
    FALLBACK_REASON_MISSING_API_KEY,
    FALLBACK_REASON_PROVIDER_ERROR,
    MISSING_API_KEY_FALLBACK_MESSAGE,
    PROVIDER_ERROR_FALLBACK_MESSAGE,
)
from app.models.lesson_draft import LessonDraft
from tests.support.course_plan_helpers import (
    SAME_ORIGIN_HEADERS,
    _build_test_client,
    _create_course,
    _create_first_lesson,
    _create_reviewed_outline,
    anyio_backend,
    inline_threadpool_for_tests,
)


@pytest.mark.anyio
async def test_lesson_drafts_page_requires_knowledge_outline(tmp_path: Path) -> None:
    client, session_factory = _build_test_client(tmp_path)
    course = _create_course(session_factory)
    try:
        await _create_first_lesson(client, session_factory, course)

        response = await client.get("/lessons/1/drafts")

        assert response.status_code == 200
        assert "课前学情与学生导学案" in response.text
        assert "请先生成并保存知识主干" in response.text
        assert "本系统不做学生答题、不做发布、不做统计、不对接学习通 API" in response.text
        with session_factory() as session:
            assert session.scalars(select(LessonDraft)).all() == []
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_default_lesson_draft_generation_creates_probe_and_low_guide(tmp_path: Path) -> None:
    client, session_factory = _build_test_client(tmp_path)
    course = _create_course(session_factory)
    try:
        await _create_first_lesson(client, session_factory, course)
        _create_reviewed_outline(session_factory)

        diagnostic_response = await client.post("/lessons/1/drafts/generate/diagnostic_probe", follow_redirects=False)
        response = await client.post("/lessons/1/drafts/generate/guide_low", follow_redirects=False)

        assert diagnostic_response.status_code == 303
        assert response.status_code == 303
        assert response.headers["location"] == f"/lessons/1/drafts?ai_fallback_reason={FALLBACK_REASON_MISSING_API_KEY}"
        with session_factory() as session:
            drafts = session.scalars(select(LessonDraft).order_by(LessonDraft.draft_type)).all()
            assert len(drafts) == 2
            assert {draft.draft_type for draft in drafts} == {
                "diagnostic_probe",
                "guide_low",
            }
            assert {draft.status for draft in drafts} == {"draft"}
            assert {draft.generated_by for draft in drafts} == {"local-structured-draft"}

            diagnostic = next(draft for draft in drafts if draft.draft_type == "diagnostic_probe")
            for text_value in [
                "题目",
                "参考答案",
                "简短解析",
                "诊断点",
                "难度",
                "基础版主文档建议",
                "提升任务包建议",
                "拓展挑战包建议",
            ]:
                assert text_value in diagnostic.content
            assert "本前测用于判断学习起点，不作为正式考试成绩" in diagnostic.content

            guide_contents = {draft.draft_type: draft.content for draft in drafts}
            assert "基础版导学案" in guide_contents["guide_low"]
            four_char_headings = [
                "学习导航",
                "学习情境",
                "知识要点",
                "边学边填",
                "例题引路",
                "仿做练习",
                "过程记录",
                "重点速记",
                "带回小练",
                "学习记录",
                "学习自评",
            ]
            for content in [guide_contents["guide_low"]]:
                for heading in four_char_headings:
                    assert heading in content
                assert "AI 草稿声明" in content
                assert "rule-based" not in content
                assert "rule_based" not in content
                assert "mock" not in content

        page_response = await client.get(response.headers["location"])
        assert page_response.status_code == 200
        assert MISSING_API_KEY_FALLBACK_MESSAGE in page_response.text
        assert f'<p class="notice ai-fallback-notice">{MISSING_API_KEY_FALLBACK_MESSAGE}</p>' in page_response.text
        assert f'<p class="alert">{MISSING_API_KEY_FALLBACK_MESSAGE}</p>' not in page_response.text
        assert "课前学情测试" in page_response.text
        assert "课前学情与学生导学案" in page_response.text
        assert "以下内容为教师草稿，仅供审阅、修改、复制与导出" in page_response.text
        assert "系统不会自动发布给学生" in page_response.text
        assert "全班通用导学案" in page_response.text
        assert "AI 生成工作台" in page_response.text
        assert "本页主文档" in page_response.text
        assert "巩固提升任务包" in page_response.text
        assert "拓展探究任务包" in page_response.text
        assert "生成课前学情测试" in page_response.text
        assert "生成基础版导学案" in page_response.text
        assert "生成巩固提升任务包" in page_response.text
        assert "生成拓展探究任务包" in page_response.text
        assert "AI 正在生成，请稍候" in page_response.text
        assert "请勿重复点击" in page_response.text
        assert "本地结构化草稿" in page_response.text
        assert "下载 DOCX" in page_response.text
        assert "/download-docx" in page_response.text
        assert "rule_based" not in page_response.text
        assert "rule-based" not in page_response.text
        assert "mock" not in page_response.text
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_lesson_draft_provider_error_uses_local_fallback_and_friendly_message(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_call(*args: object, **kwargs: object) -> tuple[str, str]:
        raise DeepSeekProviderError("底层异常：连接被拒绝")

    monkeypatch.setattr("app.services.ai.lesson_draft_ai_service._call_deepseek_lesson_draft", fail_call)
    client, session_factory = _build_test_client(tmp_path)
    course = _create_course(session_factory)
    return_to = "/ui-v2/lessons/1/diagnostic-probe"
    try:
        await _create_first_lesson(client, session_factory, course)
        _create_reviewed_outline(session_factory)
        await client.post(
            "/ai/settings",
            data={"api_key": "sk-draft-provider-error-1234", "selected_model": "deepseek-v4-flash"},
            headers=SAME_ORIGIN_HEADERS,
        )

        response = await client.post(
            "/lessons/1/drafts/generate/diagnostic_probe",
            data={"return_to": return_to},
            follow_redirects=False,
        )

        assert response.status_code == 303
        assert response.headers["location"] == f"{return_to}?ai_fallback_reason={FALLBACK_REASON_PROVIDER_ERROR}"
        with session_factory() as session:
            draft = session.scalar(select(LessonDraft).where(LessonDraft.draft_type == "diagnostic_probe"))
            assert draft is not None
            assert draft.generated_by == "local-structured-draft"
            assert "题目" in draft.content

        page_response = await client.get(response.headers["location"])
        assert page_response.status_code == 200
        assert PROVIDER_ERROR_FALLBACK_MESSAGE in page_response.text
        assert f'<p class="notice ai-fallback-notice">{PROVIDER_ERROR_FALLBACK_MESSAGE}</p>' in page_response.text
        assert f'<p class="alert">{PROVIDER_ERROR_FALLBACK_MESSAGE}</p>' not in page_response.text
        assert "底层异常" not in page_response.text
        assert "Traceback" not in page_response.text
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_lesson_draft_ai_success_does_not_show_fallback_message(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_call(*args: object, **kwargs: object) -> tuple[str, str]:
        return """# 0401-测试课次｜基础版导学案草稿

## 学习导航
- 本课学习目标：理解核心任务。

## 学习情境
- 结合真实任务观察现象。

## 知识要点
- 记录关键概念和操作步骤。

## 边学边填
- 关键步骤是：______。

## 过程记录
- 记录操作、结果和问题。

## 学习自评
- [ ] 我能说明本课重点。
""", "deepseek-v4-flash"

    monkeypatch.setattr("app.services.ai.lesson_draft_ai_service._call_deepseek_lesson_draft", fake_call)
    client, session_factory = _build_test_client(tmp_path)
    course = _create_course(session_factory)
    return_to = "/ui-v2/lessons/1/learning-guides"
    try:
        await _create_first_lesson(client, session_factory, course)
        _create_reviewed_outline(session_factory)
        await client.post(
            "/ai/settings",
            data={"api_key": "sk-draft-success-1234", "selected_model": "deepseek-v4-flash"},
            headers=SAME_ORIGIN_HEADERS,
        )

        response = await client.post(
            "/lessons/1/drafts/generate/guide_low",
            data={"return_to": return_to},
            follow_redirects=False,
        )

        assert response.status_code == 303
        assert response.headers["location"] == return_to
        with session_factory() as session:
            draft = session.scalar(select(LessonDraft).where(LessonDraft.draft_type == "guide_low"))
            assert draft is not None
            assert draft.generated_by == "deepseek-v4-flash"
            assert "结合真实任务观察现象" in draft.content

        page_response = await client.get(response.headers["location"])
        assert page_response.status_code == 200
        assert MISSING_API_KEY_FALLBACK_MESSAGE not in page_response.text
        assert PROVIDER_ERROR_FALLBACK_MESSAGE not in page_response.text
        assert "ai-fallback-notice" not in page_response.text
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_can_generate_mid_and_high_guides_after_low_guide_exists(tmp_path: Path) -> None:
    client, session_factory = _build_test_client(tmp_path)
    course = _create_course(session_factory)
    try:
        await _create_first_lesson(client, session_factory, course)
        _create_reviewed_outline(session_factory)
        await client.post("/lessons/1/drafts/generate/diagnostic_probe", follow_redirects=False)
        await client.post("/lessons/1/drafts/generate/guide_low", follow_redirects=False)

        mid_response = await client.post("/lessons/1/drafts/generate/guide_mid", follow_redirects=False)
        high_response = await client.post("/lessons/1/drafts/generate/guide_high", follow_redirects=False)

        assert mid_response.status_code == 303
        assert high_response.status_code == 303
        with session_factory() as session:
            drafts = session.scalars(select(LessonDraft).order_by(LessonDraft.draft_type)).all()
            assert len(drafts) == 4
            draft_types = {draft.draft_type for draft in drafts}
            assert draft_types == {"diagnostic_probe", "guide_low", "guide_mid", "guide_high"}
            guide_mid = next(draft for draft in drafts if draft.draft_type == "guide_mid")
            guide_high = next(draft for draft in drafts if draft.draft_type == "guide_high")
            assert "提升任务包" in guide_mid.content
            assert "拓展挑战包" in guide_high.content
            assert "学习导航" not in guide_mid.content
            assert "学习导航" not in guide_high.content
            assert "不是完整导学案" in guide_mid.content
            assert "不是完整导学案" in guide_high.content

            for draft in [guide_mid, guide_high]:
                download_response = await client.get(f"/lessons/1/drafts/{draft.id}/download-md")
                assert download_response.status_code == 200
                assert "text/markdown" in download_response.headers["content-type"]
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_lesson_draft_can_be_edited_and_saved(tmp_path: Path) -> None:
    client, session_factory = _build_test_client(tmp_path)
    course = _create_course(session_factory)
    try:
        await _create_first_lesson(client, session_factory, course)
        _create_reviewed_outline(session_factory)
        await client.post("/lessons/1/drafts/generate/guide_low", follow_redirects=False)
        await client.post("/lessons/1/drafts/generate/guide_mid", follow_redirects=False)
        with session_factory() as session:
            draft = session.scalar(select(LessonDraft).where(LessonDraft.draft_type == "guide_mid"))
            assert draft is not None
            draft_id = draft.id

        response = await client.post(
            f"/lessons/1/drafts/{draft_id}/save",
            data={"title": "教师修改后的提升任务包", "content": "教师已修改：保留关键提示并增加半开放任务。"},
            follow_redirects=False,
        )

        assert response.status_code == 303
        assert response.headers["location"] == "/lessons/1/drafts"
        with session_factory() as session:
            saved = session.get(LessonDraft, draft_id)
            assert saved is not None
            assert saved.title == "教师修改后的提升任务包"
            assert saved.content == "教师已修改：保留关键提示并增加半开放任务。"
            assert saved.status == "reviewed"
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_regenerating_lesson_drafts_upserts_current_drafts(tmp_path: Path) -> None:
    client, session_factory = _build_test_client(tmp_path)
    course = _create_course(session_factory)
    try:
        await _create_first_lesson(client, session_factory, course)
        _create_reviewed_outline(session_factory)

        first_response = await client.post("/lessons/1/drafts/generate/diagnostic_probe", follow_redirects=False)
        second_response = await client.post("/lessons/1/drafts/generate/diagnostic_probe", follow_redirects=False)

        assert first_response.status_code == 303
        assert second_response.status_code == 303
        with session_factory() as session:
            drafts = session.scalars(select(LessonDraft)).all()
            assert len(drafts) == 1
            assert len({(draft.lesson_id, draft.draft_type) for draft in drafts}) == 1
    finally:
        await client.aclose()
        main.app.dependency_overrides.clear()
