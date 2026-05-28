from pathlib import Path

from sqlalchemy import create_engine, inspect, select
from sqlalchemy.orm import Session

from app.db.base import Base, create_database_tables
from app.models.course import Course
from app.models.course_plan import CoursePlanUpload, PlannedLesson
from app.models.lesson import Lesson, create_lesson_from_planned_lesson
from app.services.course_plan.parser import parse_course_plan_xlsx


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_PLAN = PROJECT_ROOT / "data" / "sample-course-plans" / "2025-2026-database-course-plan.xlsx"


def _create_test_engine():
    # 测试只使用 SQLite 内存数据库，不依赖本机 MySQL。
    return create_engine("sqlite+pysqlite:///:memory:", future=True)


def _create_course(session: Session) -> Course:
    course = Course(title="数据库应用与数据分析", semester="2025-2026-2", status="draft")
    session.add(course)
    session.commit()
    session.refresh(course)
    return course


def _create_upload(session: Session, course: Course) -> CoursePlanUpload:
    upload = CoursePlanUpload(
        course_id=course.id,
        original_filename=SAMPLE_PLAN.name,
        file_path=str(SAMPLE_PLAN),
        parsed_status="success",
    )
    session.add(upload)
    session.commit()
    session.refresh(upload)
    return upload


def _save_planned_lessons(session: Session, course: Course, upload: CoursePlanUpload) -> list[PlannedLesson]:
    parsed_lessons = parse_course_plan_xlsx(SAMPLE_PLAN)
    planned_lessons = [
        PlannedLesson(
            course_plan_upload_id=upload.id,
            course_id=course.id,
            **lesson_data,
        )
        for lesson_data in parsed_lessons
    ]
    session.add_all(planned_lessons)
    session.commit()
    return planned_lessons


def test_can_create_database_tables() -> None:
    engine = _create_test_engine()

    create_database_tables(engine)

    table_names = set(inspect(engine).get_table_names())
    assert {"courses", "course_plan_uploads", "planned_lessons", "lessons", "lesson_drafts"}.issubset(table_names)


def test_can_create_course() -> None:
    engine = _create_test_engine()
    create_database_tables(engine)

    with Session(engine) as session:
        course = _create_course(session)

        saved_course = session.get(Course, course.id)
        assert saved_course is not None
        assert saved_course.title == "数据库应用与数据分析"


def test_can_create_course_plan_upload() -> None:
    engine = _create_test_engine()
    create_database_tables(engine)

    with Session(engine) as session:
        course = _create_course(session)
        upload = _create_upload(session, course)

        saved_upload = session.get(CoursePlanUpload, upload.id)
        assert saved_upload is not None
        assert saved_upload.course_id == course.id
        assert saved_upload.parsed_status == "success"


def test_can_save_parser_planned_lessons() -> None:
    engine = _create_test_engine()
    create_database_tables(engine)

    with Session(engine) as session:
        course = _create_course(session)
        upload = _create_upload(session, course)
        planned_lessons = _save_planned_lessons(session, course, upload)

        first_lesson = session.scalar(select(PlannedLesson).order_by(PlannedLesson.id))
        assert len(planned_lessons) > 0
        assert first_lesson is not None
        assert first_lesson.course_id == course.id
        assert first_lesson.course_plan_upload_id == upload.id
        assert first_lesson.status == "pending"


def test_can_save_28_planned_lessons_from_sample_file() -> None:
    engine = _create_test_engine()
    create_database_tables(engine)

    with Session(engine) as session:
        course = _create_course(session)
        upload = _create_upload(session, course)
        _save_planned_lessons(session, course, upload)

        count = len(session.scalars(select(PlannedLesson)).all())
        assert count == 28


def test_confirmed_planned_lesson_can_become_lesson() -> None:
    engine = _create_test_engine()
    create_database_tables(engine)

    with Session(engine) as session:
        course = _create_course(session)
        upload = _create_upload(session, course)
        planned_lessons = _save_planned_lessons(session, course, upload)
        planned_lesson = planned_lessons[0]
        planned_lesson.status = "confirmed"
        session.commit()
        session.refresh(planned_lesson)

        lesson = create_lesson_from_planned_lesson(planned_lesson)
        assert lesson is not None
        session.add(lesson)
        session.commit()
        session.refresh(lesson)

        saved_lesson = session.get(Lesson, lesson.id)
        assert saved_lesson is not None
        assert saved_lesson.planned_lesson_id == planned_lesson.id
        assert saved_lesson.title == planned_lesson.lesson_title


def test_skipped_planned_lesson_does_not_become_lesson() -> None:
    engine = _create_test_engine()
    create_database_tables(engine)

    with Session(engine) as session:
        course = _create_course(session)
        upload = _create_upload(session, course)
        planned_lessons = _save_planned_lessons(session, course, upload)
        planned_lesson = planned_lessons[0]
        planned_lesson.status = "skipped"
        session.commit()
        session.refresh(planned_lesson)

        lesson = create_lesson_from_planned_lesson(planned_lesson)
        if lesson is not None:
            session.add(lesson)
            session.commit()

        lessons = session.scalars(select(Lesson)).all()
        assert lessons == []
