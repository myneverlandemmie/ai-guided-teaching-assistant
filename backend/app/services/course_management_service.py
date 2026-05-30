"""课程管理最小业务服务。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.course import Course


DEFAULT_COURSE_TITLE = "测试课程"
DEFAULT_COURSE_SEMESTER = "2025-2026-2"


def normalize_course_title(title: str) -> str:
    """清洗课程名称。

    Args:
        title: 用户输入的课程名称。

    Returns:
        去除首尾空白后的课程名称。

    Raises:
        不主动抛出业务异常。
    """

    return title.strip()


def get_or_create_default_course(session: Session) -> Course:
    """读取第一门课程；空库时创建通用测试课程。

    Args:
        session: SQLAlchemy Session。

    Returns:
        已存在的第一门课程，或新建的“测试课程”。

    Raises:
        SQLAlchemy 写入异常会继续向外抛出。
    """

    course = session.query(Course).order_by(Course.id).first()
    if course is not None:
        return course

    course = Course(title=DEFAULT_COURSE_TITLE, semester=DEFAULT_COURSE_SEMESTER, status="draft")
    session.add(course)
    session.commit()
    session.refresh(course)
    return course


def create_course(session: Session, title: str, semester: str = DEFAULT_COURSE_SEMESTER) -> Course:
    """创建课程。

    Args:
        session: SQLAlchemy Session。
        title: 课程名称，不能为空。
        semester: 学期文本。

    Returns:
        新建的课程。

    Raises:
        ValueError: 课程名称为空。
        SQLAlchemy 写入异常会继续向外抛出。
    """

    normalized_title = normalize_course_title(title)
    if not normalized_title:
        raise ValueError("课程名称不能为空")

    course = Course(title=normalized_title, semester=semester, status="draft")
    session.add(course)
    session.commit()
    session.refresh(course)
    return course


def rename_course(session: Session, course: Course, title: str) -> Course:
    """修改课程名称，不影响课程下已有课次与草稿数据。

    Args:
        session: SQLAlchemy Session。
        course: 要修改的课程。
        title: 新课程名称，不能为空。

    Returns:
        修改后的课程。

    Raises:
        ValueError: 课程名称为空。
        SQLAlchemy 写入异常会继续向外抛出。
    """

    normalized_title = normalize_course_title(title)
    if not normalized_title:
        raise ValueError("课程名称不能为空")

    course.title = normalized_title
    session.commit()
    session.refresh(course)
    return course


def delete_course(session: Session, course: Course) -> None:
    """删除课程及其 ORM 级联子记录。

    当前模型已配置从 Course 到 CoursePlanUpload、PlannedLesson、Lesson，
    以及 Lesson 到材料、知识主干、导学草稿的 delete-orphan 级联。

    Args:
        session: SQLAlchemy Session。
        course: 要删除的课程。

    Returns:
        None。

    Raises:
        SQLAlchemy 删除异常会继续向外抛出。
    """

    session.delete(course)
    session.commit()
