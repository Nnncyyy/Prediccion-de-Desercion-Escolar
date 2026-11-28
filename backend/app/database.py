"""RNF_03 · Sesión por solicitud y claves foráneas en SQLite."""
from collections.abc import Iterator
import sqlite3

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.pool import ConnectionPoolEntry
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


@event.listens_for(Engine, 'connect')
def activar_claves_foraneas(conexion: object, registro: ConnectionPoolEntry) -> None:
    if isinstance(conexion, sqlite3.Connection):
        conexion.execute('PRAGMA foreign_keys=ON').close()
        # RF_03 · La función lower nativa de SQLite solo convierte ASCII.
        conexion.create_function('sipde_casefold', 1, str.casefold, deterministic=True)


opciones = {'check_same_thread': False} if settings.database_url.startswith('sqlite') else {}
engine = create_engine(settings.database_url, connect_args=opciones)
SessionLocal = sessionmaker(bind=engine, autoflush=False)


def get_db() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session
