from pathlib import Path

from openpyxl import Workbook
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.base import create_database_tables
from app.models.course import Course
from app.models.course_plan import CoursePlanUpload, PlannedLesson
from app.models.lesson import Lesson
from app.services.course_plan.import_service import (
    confirm_planned_lessons,
    create_lessons_from_confirmed_planned_lessons,
    import_course_plan,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_PLAN = PROJECT_ROOT / "data" / "sample-course-plans" / "2025-2026-database-course-plan.xlsx"


def _create_test_engine():
    # 测试只使用 SQLite 内存数据库，不依赖真实 MySQL，也不会生成运行时数据库文件。
    return create_engine("sqlite+pysqlite:///:memory:", future=True)


def _create_course(session: Session) -> Course:
    course = Course(title="数据库应用与数据分析", semester="2025-2026-2", status="draft")
    session.add(course)
    session.commit()
    session.refresh(course)
    return course


def _create_invalid_course_plan(path: Path) -> None:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.append(["*周次", "*课次", "学时", "教学用具"])
    worksheet.append(["1", "1", "2", "机房"])
    workbook.save(path)


def test_import_course_plan_creates_upload_and_28_planned_lessons() -> None:
    engine = _create_test_engine()
    create_database_tables(engine)

    with Session(engine) as session:
        course = _create_course(session)

        result = import_course_plan(session, course, SAMPLE_PLAN, SAMPLE_PLAN.name)

        upload = result["upload"]
        planned_lessons = session.scalars(select(PlannedLesson)).all()
        assert isinstance(upload, CoursePlanUpload)
        assert result["parsed_status"] == "success"
        assert upload.parsed_status == "success"
        assert result["planned_lesson_count"] == 28
        assert len(planned_lessons) == 28


def test_imported_planned_lessons_are_linked_to_upload_and_course() -> None:
    engine = _create_test_engine()
    create_database_tables(engine)

    with Session(engine) as session:
        course = _create_course(session)
        result = import_course_plan(session, course, SAMPLE_PLAN, SAMPLE_PLAN.name)
        upload = result["upload"]

        planned_lesson = session.scalar(select(PlannedLesson).order_by(PlannedLesson.id))
        assert planned_lesson is not None
        assert planned_lesson.course_plan_upload_id == upload.id
        assert planned_lesson.course_id == course.id
        assert planned_lesson.course_plan_upload.id == upload.id
        assert planned_lesson.course.id == course.id


def test_can_confirm_part_of_planned_lessons() -> None:
    engine = _create_test_engine()
    create_database_tables(engine)

    with Session(engine) as session:
        course = _create_course(session)
        import_course_plan(session, course, SAMPLE_PLAN, SAMPLE_PLAN.name)
        planned_lessons = session.scalars(select(PlannedLesson).order_by(PlannedLesson.id).limit(3)).all()
        planned_lesson_ids = [lesson.id for lesson in planned_lessons]

        confirmed_lessons = confirm_planned_lessons(session, planned_lesson_ids[:2])

        statuses = {
            lesson.id: session.get(PlannedLesson, lesson.id).status  # type: ignore[union-attr]
            for lesson in planned_lessons
        }
        assert len(confirmed_lessons) == 2
        assert statuses[planned_lesson_ids[0]] == "confirmed"
        assert statuses[planned_lesson_ids[1]] == "confirmed"
        assert statuses[planned_lesson_ids[2]] == "pending"


def test_confirmed_planned_lessons_create_lessons_but_skipped_do_not() -> None:
    engine = _create_test_engine()
    create_database_tables(engine)

    with Session(engine) as session:
        course = _create_course(session)
        import_course_plan(session, course, SAMPLE_PLAN, SAMPLE_PLAN.name)
        planned_lessons = session.scalars(select(PlannedLesson).order_by(PlannedLesson.id).limit(3)).all()
        first, second, third = planned_lessons
        first.status = "confirmed"
        second.status = "skipped"
        third.status = "pending"
        session.commit()

        created_lessons = create_lessons_from_confirmed_planned_lessons(
            session,
            [first.id, second.id, third.id],
        )

        saved_lessons = session.scalars(select(Lesson)).all()
        assert len(created_lessons) == 1
        assert len(saved_lessons) == 1
        assert saved_lessons[0].planned_lesson_id == first.id


def test_create_lessons_from_confirmed_planned_lessons_is_idempotent() -> None:
    engine = _create_test_engine()
    create_database_tables(engine)

    with Session(engine) as session:
        course = _create_course(session)
        import_course_plan(session, course, SAMPLE_PLAN, SAMPLE_PLAN.name)
        planned_lesson = session.scalar(select(PlannedLesson).order_by(PlannedLesson.id))
        assert planned_lesson is not None
        planned_lesson.status = "confirmed"
        session.commit()

        first_result = create_lessons_from_confirmed_planned_lessons(session, [planned_lesson.id])
        second_result = create_lessons_from_confirmed_planned_lessons(session, [planned_lesson.id])

        saved_lessons = session.scalars(select(Lesson)).all()
        assert len(first_result) == 1
        assert second_result == []
        assert len(saved_lessons) == 1


def test_import_course_plan_records_failed_status_when_parse_fails(tmp_path: Path) -> None:
    engine = _create_test_engine()
    create_database_tables(engine)
    invalid_plan = tmp_path / "invalid-course-plan.xlsx"
    _create_invalid_course_plan(invalid_plan)

    with Session(engine) as session:
        course = _create_course(session)

        result = import_course_plan(session, course, invalid_plan, invalid_plan.name)

        upload = result["upload"]
        planned_lessons = session.scalars(select(PlannedLesson)).all()
        assert result["parsed_status"] == "failed"
        assert result["planned_lesson_count"] == 0
        assert upload.parsed_status == "failed"
        assert upload.error_message is not None
        assert "缺少必要字段" in upload.error_message
        assert planned_lessons == []
