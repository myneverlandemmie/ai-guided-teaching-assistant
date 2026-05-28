from pathlib import Path


def test_teaching_prep_reference_prompt_documents_boundaries() -> None:
    path = Path(__file__).resolve().parents[2] / "docs/prompts/teaching-prep-reference-suggestions-v0.1.md"
    content = path.read_text(encoding="utf-8")

    assert "备课参考建议" in content
    assert "不替代教师判断" in content
    assert "不输出完整教案" in content
    assert "不输出比赛教案成稿" in content
    assert "不评价教师能力" in content
    assert "不把高标准公开课结构作为日常教案硬性要求" in content
    assert "导学案生成提示" in content
    assert "课前学情测试提示" in content
    assert "学生自评" in content
    assert "小组互评" in content
