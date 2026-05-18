"""SQLAlchemy 声明式基类与建表入口。"""

from __future__ import annotations

from sqlalchemy import Engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """所有 ORM 模型的声明式基类。"""


def create_database_tables(engine: Engine) -> None:
    """使用 SQLAlchemy create_all 创建当前已声明的数据表。

    Args:
        engine: SQLAlchemy Engine，测试中可传入 SQLite 内存数据库。

    Returns:
        None。

    Raises:
        SQLAlchemy 底层建表异常会继续向外抛出。
    """

    # 必须先导入模型模块，确保表定义已注册到 Base.metadata。
    from app.models import course, course_plan, knowledge_outline, lesson  # noqa: F401

    Base.metadata.create_all(bind=engine)
