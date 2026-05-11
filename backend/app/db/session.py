"""数据库连接与 Session 工厂。"""

from __future__ import annotations

import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


DEFAULT_DATABASE_URL = "sqlite:///./app.db"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)


def _connect_args(database_url: str) -> dict[str, object]:
    """根据数据库类型返回连接参数。"""

    if database_url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


def get_engine(database_url: str | None = None) -> Engine:
    """创建 SQLAlchemy Engine。

    Args:
        database_url: 数据库连接串；为空时读取环境变量 DATABASE_URL，否则使用本地 SQLite 默认值。

    Returns:
        SQLAlchemy Engine。

    Raises:
        SQLAlchemy 底层连接串解析异常会继续向外抛出。
    """

    url = database_url or DATABASE_URL
    return create_engine(url, connect_args=_connect_args(url), future=True)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """基于 Engine 创建 Session 工厂。"""

    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


engine = get_engine()
SessionLocal = create_session_factory(engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI 依赖形式的数据库 Session 生成器。"""

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
