from pathlib import Path

import pytest
from openpyxl import Workbook

from app.services.course_plan.parser import (
    CoursePlanParseError,
    build_planned_lesson,
    detect_columns,
    parse_course_plan_xlsx,
    parse_lesson_code_and_title,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_PLAN = PROJECT_ROOT / "data" / "sample-course-plans" / "2025-2026-database-course-plan.xlsx"


def _create_course_plan(path: Path, rows: list[list[object]]) -> None:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.append(["*周次", "*课次", "学时", "教学内容(课堂教学，课带实验)", "教学用具", "作业", "备注"])
    for row in rows:
        worksheet.append(row)
    workbook.save(path)


def test_parse_lesson_code_and_title_with_dash_separator() -> None:
    lesson_code, lesson_title = parse_lesson_code_and_title("0401-简单查询")

    assert lesson_code == "0401"
    assert lesson_title == "简单查询"


def test_parse_lesson_code_and_title_with_chinese_colon_separator() -> None:
    lesson_code, lesson_title = parse_lesson_code_and_title("0801：视图")

    assert lesson_code == "0801"
    assert lesson_title == "视图"


def test_parse_lesson_code_and_title_without_code() -> None:
    lesson_code, lesson_title = parse_lesson_code_and_title("MySQL 数据库概述")

    assert lesson_code == ""
    assert lesson_title == "MySQL 数据库概述"


def test_parse_course_plan_skips_empty_rows(tmp_path: Path) -> None:
    plan_path = tmp_path / "course-plan.xlsx"
    _create_course_plan(
        plan_path,
        [
            [None, None, None, None, None, None, None],
            ["1", "1", "2", "0401-简单查询", "机房", "完成练习", ""],
        ],
    )

    lessons = parse_course_plan_xlsx(plan_path)

    assert len(lessons) == 1
    assert lessons[0]["lesson_code"] == "0401"
    assert lessons[0]["status"] == "pending"


def test_detect_columns_reports_missing_required_field() -> None:
    headers = ["*周次", "*课次", "学时", "教学用具", "作业", "备注"]

    with pytest.raises(CoursePlanParseError, match="缺少必要字段"):
        detect_columns(headers)


def test_build_planned_lesson_returns_required_fields() -> None:
    lesson = build_planned_lesson(
        {
            "week": "4",
            "lesson_no": "7",
            "hours": "2",
            "content_raw": "0502 条件查询",
            "tools": "MySQL",
            "homework": "完成 WHERE 练习",
            "notes": "重点讲比较运算符",
        }
    )

    assert lesson == {
        "week": "4",
        "lesson_no": "7",
        "hours": "2",
        "lesson_code": "0502",
        "lesson_title": "条件查询",
        "content_raw": "0502 条件查询",
        "tools": "MySQL",
        "homework": "完成 WHERE 练习",
        "notes": "重点讲比较运算符",
        "status": "pending",
    }


def test_can_read_sample_xlsx_file() -> None:
    assert SAMPLE_PLAN.exists(), f"样例授课计划不存在: {SAMPLE_PLAN}"

    lessons = parse_course_plan_xlsx(SAMPLE_PLAN)

    assert lessons


def test_sample_xlsx_parses_28_planned_lessons() -> None:
    lessons = parse_course_plan_xlsx(SAMPLE_PLAN)

    assert len(lessons) == 28
