"""RNF_03 / RT_03 · Migraciones del esquema en SQLite y PostgreSQL."""
from alembic import context
from sqlalchemy import create_engine, pool
from sqlalchemy.engine import Connection, make_url

from app import models  # Registra las entidades antes de consultar los metadatos.
from app.config import settings
from app.database import Base

target_metadata = Base.metadata
url = make_url(context.get_x_argument(as_dictionary=True).get('url', settings.database_url))
opciones = {'target_metadata': target_metadata, 'render_as_batch': True}


def ejecutar_sin_conexion() -> None:
    context.configure(url=url, literal_binds=True, **opciones)
    with context.begin_transaction():
        context.run_migrations()


def aplicar(conexion: Connection) -> None:
    context.configure(connection=conexion, **opciones)
    with context.begin_transaction():
        context.run_migrations()


def ejecutar_con_conexion() -> None:
    conexion_existente = context.config.attributes.get('connection')
    if conexion_existente is not None:
        aplicar(conexion_existente)
        return
    motor = create_engine(url, poolclass=pool.NullPool)
    try:
        with motor.connect() as conexion:
            aplicar(conexion)
    finally:
        motor.dispose()


if context.is_offline_mode():
    ejecutar_sin_conexion()
else:
    ejecutar_con_conexion()
