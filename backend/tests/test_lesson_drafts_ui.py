from pathlib import Path

from app import main
from app.services.ai.lesson_draft_service import DRAFT_TYPE_LABELS


def test_lesson_drafts_template_uses_pc_product_layout() -> None:
    template = Path("app/templates/lesson_drafts.html").read_text(encoding="utf-8")

    for phrase in [
        "page-header",
        "process-steps",
        "draft-workbench",
        "primary-draft-card",
        "secondary-task-card",
        "editor-tabs",
        "editor-panel",
        "editor-area",
        "课前学情测试",
        "全班通用导学案",
        "巩固提升任务包",
        "拓展探究任务包",
        "导出学习通题库模板",
        "下载 Markdown",
        "保存教师修改",
    ]:
        assert phrase in template


def test_lesson_drafts_template_has_local_generation_status_targets() -> None:
    template = Path("app/templates/lesson_drafts.html").read_text(encoding="utf-8")
    script = Path("app/static/js/app.js").read_text(encoding="utf-8")

    for status_id in ["diagnostic-probe-status", "guide-low-status", "guide-mid-status", "guide-high-status"]:
        assert status_id in template
    assert "data-status-target=\"diagnostic-probe-status\"" in template
    assert "data-status-target=\"guide-low-status\"" in template
    assert "data-status-target=\"guide-mid-status\"" in template
    assert "data-status-target=\"guide-high-status\"" in template
    assert "data-ai-generation-form" in template
    assert "clickedButton.textContent = form.getAttribute('data-loading-label')" in script
    assert "form.querySelectorAll" in script
    assert "activateDraftTab" in script
    assert "data-draft-tab-target" in template
    assert "data-draft-editor-panel" in template


def test_public_draft_labels_and_download_names_do_not_expose_internal_tiers() -> None:
    assert DRAFT_TYPE_LABELS["guide_low"] == "全班通用导学案 / 基础版导学案"
    assert DRAFT_TYPE_LABELS["guide_mid"] == "巩固提升任务包"
    assert DRAFT_TYPE_LABELS["guide_high"] == "拓展探究任务包"
    assert main.LESSON_DRAFT_DOWNLOAD_NAME_PARTS["guide_low"] == "core_learning_guide"
    assert main.LESSON_DRAFT_DOWNLOAD_NAME_PARTS["guide_mid"] == "enhancement_task_pack"
    assert main.LESSON_DRAFT_DOWNLOAD_NAME_PARTS["guide_high"] == "extension_challenge_pack"
    assert main.LESSON_DRAFT_DOWNLOAD_NAME_PARTS["teaching_prep_reference"] == "teaching_prep_reference_suggestions"
    assert "guide_low" not in set(main.LESSON_DRAFT_DOWNLOAD_NAME_PARTS.values())
    assert "guide_mid" not in set(main.LESSON_DRAFT_DOWNLOAD_NAME_PARTS.values())
    assert "guide_high" not in set(main.LESSON_DRAFT_DOWNLOAD_NAME_PARTS.values())


def test_base_template_loads_external_static_assets() -> None:
    base = Path("app/templates/base.html").read_text(encoding="utf-8")

    assert "/static/css/app.css" in base
    assert "/static/js/app.js" in base
    assert "<style>" not in base
