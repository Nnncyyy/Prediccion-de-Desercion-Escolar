"""PT_13 · Instalación limpia, esquema inicial y datos de demostración."""
from pathlib import Path
import re

from alembic import command
from alembic.config import Config
from dotenv import dotenv_values
import pytest
from sqlalchemy import CheckConstraint, create_engine, func, inspect, select, text, UniqueConstraint
from sqlalchemy.orm import Session

from app import seed
from app.config import Settings, settings
from app.database import Base
from app.models import Student, User
from app.security import verify_password
from app.services.risk import academic_alert
from scripts.generar_env import generar_env

BACKEND = Path(__file__).resolve().parents[1]


def test_pt13_migracion_coincide_con_modelos(tmp_path, monkeypatch):
    url = f'sqlite:///{tmp_path / "instalacion.sqlite"}'
    monkeypatch.setenv('DATABASE_URL', url)
    monkeypatch.setattr(settings, 'database_url', Settings().database_url)
    command.upgrade(Config(str(BACKEND / 'alembic.ini')), 'head')

    motor = create_engine(url)
    try:
        inspector = inspect(motor)
        assert set(inspector.get_table_names()) - {'alembic_version'} == set(Base.metadata.tables)
        for tabla in Base.metadata.sorted_tables:
            columnas = inspector.get_columns(tabla.name)
            assert [(c['name'], c['nullable']) for c in columnas] == [
                (c.name, c.nullable) for c in tabla.columns
            ]
            assert inspector.get_pk_constraint(tabla.name)['constrained_columns'] == list(tabla.primary_key.columns.keys())
            assert {c['sqltext'] for c in inspector.get_check_constraints(tabla.name)} == {
                str(c.sqltext) for c in tabla.constraints if isinstance(c, CheckConstraint)
            }
            assert {tuple(c['column_names']) for c in inspector.get_unique_constraints(tabla.name)} == {
                tuple(c.columns.keys()) for c in tabla.constraints if isinstance(c, UniqueConstraint)
            }
            assert {(tuple(c['constrained_columns']), c['referred_table'], tuple(c['referred_columns']))
                    for c in inspector.get_foreign_keys(tabla.name)} == {
                (tuple(c.column_keys), c.referred_table.name, tuple(e.column.name for e in c.elements))
                for c in tabla.foreign_key_constraints
            }
            assert {(i['name'], tuple(i['column_names']), i['unique']) for i in inspector.get_indexes(tabla.name)} == {
                (i.name, tuple(i.columns.keys()), i.unique) for i in tabla.indexes
            }
    finally:
        motor.dispose()


def test_pt13_seed_idempotente(tmp_path, monkeypatch, capsys, trained_model):
    url = f'sqlite:///{tmp_path / "demostracion.sqlite"}'
    monkeypatch.setattr(settings, 'database_url', url)
    monkeypatch.setattr(settings, 'auto_create_tables', True)
    monkeypatch.setattr(settings, 'admin_email', 'pt13@example.test')
    monkeypatch.setattr(settings, 'admin_password', 'PT13_ADMIN_DE_PRUEBA')
    # Una variable vacía anula el .env e induce la generación de una contraseña aleatoria.
    monkeypatch.setenv('SEED_PASSWORD', '')
    motor = create_engine(url)

    def conteos():
        with Session(motor) as db:
            return {t.name: db.scalar(select(func.count()).select_from(t))
                    for t in Base.metadata.sorted_tables}

    try:
        seed.sembrar()
        primera_salida = capsys.readouterr().out
        clave = re.search(r'SEED_PASSWORD=(\S+)', primera_salida)[1]
        assert primera_salida.count(clave) == 1
        primero = conteos()
        seed.sembrar()
        assert clave not in capsys.readouterr().out
        assert conteos() == primero == {
            'users': 4, 'careers': 3, 'periods': 4, 'subjects': 12, 'students': 40,
            'enrollments': 160, 'followups': 20, 'prediction_logs': 15, 'audit_logs': 15,
        }
        with Session(motor) as db:
            tutor = db.scalar(select(User).filter_by(email='tutor1@sipde.local'))
            assert verify_password(clave, tutor.password_hash)
            assert {academic_alert(alumno, [i.grade for i in alumno.enrollments])['level']
                    for alumno in db.scalars(select(Student).filter_by(active=True))} == {
                'baja', 'media', 'alta', 'sin_datos',
            }
    finally:
        motor.dispose()


def test_pt13_reset_recrea_solo_sqlite_y_permite_modelo_ausente(tmp_path, monkeypatch, capsys):
    ruta = tmp_path / 'obsoleta.sqlite'
    url = f'sqlite:///{ruta}'
    monkeypatch.setattr(settings, 'database_url', url)
    monkeypatch.setattr(settings, 'auto_create_tables', False)
    monkeypatch.setattr(settings, 'admin_email', 'pt13@example.test')
    monkeypatch.setattr(settings, 'admin_password', 'PT13_ADMIN_DE_PRUEBA')
    monkeypatch.setattr(settings, 'model_path', str(tmp_path / 'ausente.joblib'))
    monkeypatch.setenv('SEED_PASSWORD', 'PT13_DEMO_DE_PRUEBA')
    motor = create_engine(url)
    try:
        with motor.begin() as conexion:
            conexion.execute(text('CREATE TABLE students (id INTEGER PRIMARY KEY)'))
        motor.dispose()
        seed.sembrar(reset=True)
        assert 'Se omiten las predicciones' in capsys.readouterr().out
        with motor.connect() as conexion:
            assert conexion.scalar(text('SELECT version_num FROM alembic_version')) == '0001_esquema_inicial'
            assert conexion.scalar(text('SELECT count(*) FROM students')) == 40
            assert conexion.scalar(text('SELECT count(*) FROM prediction_logs')) == 0
    finally:
        motor.dispose()
    monkeypatch.setattr(settings, 'database_url', 'postgresql+psycopg://sipde@localhost/sipde')
    with pytest.raises(ValueError, match='solo se admite en SQLite'):
        seed.sembrar(reset=True)


def test_pt13_genera_env_valido(tmp_path, monkeypatch):
    plantilla = BACKEND.parent / '.env.example'
    destino = tmp_path / '.env'
    for clave in dotenv_values(plantilla):
        monkeypatch.delenv(clave, raising=False)
    valores = generar_env(plantilla, destino)
    configuracion = Settings(_env_file=destino)
    assert len(configuracion.jwt_secret) >= 24 and not configuracion.jwt_secret.startswith('CAMBIAR')
    assert len(configuracion.admin_password) >= 8 and not configuracion.admin_password.startswith('CAMBIAR')
    assert configuracion.admin_email == 'admin@sipde.local'
    assert configuracion.database_url == 'sqlite:///./sipde.db'
    assert configuracion.auto_create_tables is True
    assert not dotenv_values(destino)['POSTGRES_PASSWORD'].startswith('CAMBIAR')
    with pytest.raises(FileExistsError):
        generar_env(plantilla, destino)
    assert dotenv_values(destino) == valores
    assert generar_env(plantilla, destino, forzar=True)['JWT_SECRET'] != valores['JWT_SECRET']
