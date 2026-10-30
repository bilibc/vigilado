from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import ajustes

if ajustes.database_url.startswith("sqlite:///"):
    Path(ajustes.database_url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)

motor = create_engine(ajustes.database_url,
                      connect_args={"check_same_thread": False} if ajustes.database_url.startswith("sqlite") else {},
                      pool_pre_ping=True)
Sesion = sessionmaker(bind=motor, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def obtener_db():
    db = Sesion()
    try:
        yield db
    finally:
        db.close()
