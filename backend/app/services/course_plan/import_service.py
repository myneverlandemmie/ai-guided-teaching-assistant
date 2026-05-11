"""课程计划导入 service 层。

本模块负责连接 parser 与 ORM 模型：创建上传记录、保存 planned lessons、确认课次并生成正式 Lesson。
不包含页面、登录、AI 或 SQL 批阅逻辑。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.course import Course
from app.models.course_plan import CoursePlanUpload, PlannedLesson
from app.models.lesson import Lesson, create_lesson_from_planned_lesson
from app.services.course_plan.parser import parse_course_plan_xlsx


class CoursePlanImportError(ValueError):
    """课程计划导入 service 层错误。"""


def save_planned_lessons(
    session: Session,
    course: Course,
    upload: CoursePlanUpload,
    parsed_lessons: list[dict[str, Any]],
) -> list[PlannedLesson]:
    """保存 parser 返回的 planned lessons。

    Args:
        session: SQLAlchemy Session。
        course: 归属课程。
        upload: 本次授课计划上传记录。
        parsed_lessons: parser 返回的 planned lesson 字典列表。

    Returns:
        已持久化并带有 id 的 PlannedLesson 列表。

    Raises:
        SQLAlchemy 底层写入异常会继续向外抛出。
    """

    planned_lesson_models = [
        PlannedLesson(
            course_plan_upload_id=upload.id,
            course_id=course.id,
            week=lesson_data["week"],
            lesson_no=lesson_data["lesson_no"],
            hours=lesson_data["hours"],
            lesson_code=lesson_data.get("lesson_code", ""),
            lesson_title=lesson_data["lesson_title"],
            content_raw=lesson_data["content_raw"],
            tools=lesson_data.get("tools", ""),
            homework=lesson_data.get("homework", ""),
            notes=lesson_data.get("notes", ""),
            status=lesson_data.get("status", "pending"),
        )
        for lesson_data in parsed_lessons
    ]

    session.add_all(planned_lesson_models)
    session.flush()
    return planned_lesson_models


def import_course_plan(
    session: Session,
    course: Course,
    file_path: str | Path,
    original_filename: str,
) -> dict[str, Any]:
    """导入授课计划 Excel 并保存解析结果。

    Args:
        session: SQLAlchemy Session。
        course: 归属课程。
        file_path: Excel 文件路径。
        original_filename: 原始文件名。

    Returns:
        包含 upload、planned_lesson_count、parsed_status 的导入结果字典。

    Raises:
        不主动向外抛出 parser 业务异常；解析失败会写入 upload.failed 与 error_message。
        数据库提交异常会继续向外抛出。
    """

    upload = CoursePlanUpload(
        course_id=course.id,
        original_filename=original_filename,
        file_path=str(file_path),
        parsed_status="pending",
    )
    session.add(upload)
    session.flush()

    try:
        parsed_lessons = parse_course_plan_xlsx(file_path)
        planned_lessons = save_planned_lessons(session, course, upload, parsed_lessons)
        upload.parsed_status = "success"
        upload.error_message = None
        planned_lesson_count = len(planned_lessons)
    except Exception as exc:  # noqa: BLE001 - service 层需要把解析失败落库供教师排查
        # 业务规则：即使解析失败，也保留上传记录和错误信息。
        upload.parsed_status = "failed"
        upload.error_message = str(exc)
        planned_lesson_count = 0

    session.commit()
    session.refresh(upload)

    return {
        "upload": upload,
        "planned_lesson_count": planned_lesson_count,
        "parsed_status": upload.parsed_status,
    }


def confirm_planned_lessons(session: Session, planned_lesson_ids: list[int]) -> list[PlannedLesson]:
    """确认一组 planned lessons。

    Args:
        session: SQLAlchemy Session。
        planned_lesson_ids: 待确认的 PlannedLesson id 列表。

    Returns:
        已更新为 confirmed 的 PlannedLesson 列表。

    Raises:
        不主动抛出业务异常；不存在的 id 会被忽略。
    """

    if not planned_lesson_ids:
        return []

    planned_lessons = list(
        session.scalars(select(PlannedLesson).where(PlannedLesson.id.in_(planned_lesson_ids))).all()
    )
    for planned_lesson in planned_lessons:
        planned_lesson.status = "confirmed"

    session.commit()
    for planned_lesson in planned_lessons:
        session.refresh(planned_lesson)
    return planned_lessons


def create_lessons_from_confirmed_planned_lessons(
    session: Session,
    planned_lesson_ids: list[int],
) -> list[Lesson]:
    """根据 confirmed planned lessons 生成正式课次。

    Args:
        session: SQLAlchemy Session。
        planned_lesson_ids: 候选 PlannedLesson id 列表。

    Returns:
        实际创建的 Lesson 列表；skipped、pending 或已生成 Lesson 的记录不会重复创建。

    Raises:
        数据库提交异常会继续向外抛出。
    """

    if not planned_lesson_ids:
        return []

    planned_lessons = list(
        session.scalars(select(PlannedLesson).where(PlannedLesson.id.in_(planned_lesson_ids))).all()
    )
    created_lessons: list[Lesson] = []

    for planned_lesson in planned_lessons:
        # 避免重复确认时重复生成正式课次。
        if planned_lesson.lesson is not None:
            continue
        lesson = create_lesson_from_planned_lesson(planned_lesson)
        if lesson is None:
            continue
        session.add(lesson)
        created_lessons.append(lesson)

    session.commit()
    for lesson in created_lessons:
        session.refresh(lesson)
    return created_lessons
