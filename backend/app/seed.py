"""RNF_03 / RNF_06 / PT_13 · DATOS FICTICIOS DE DEMOSTRACIÓN de SIPDE."""
import argparse
from datetime import date, datetime
import json
import os
from pathlib import Path
import random
import secrets

from alembic import command
from alembic.config import Config
from dotenv import dotenv_values
from fastapi import HTTPException
from sqlalchemy import create_engine, func, select
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import Session

from app.config import settings
from app.database import Base
from app.models import AuditLog, Career, Enrollment, FollowUp, Period, PredictionLog, Student, Subject, User
from app.security import hash_password, verify_password
from app.services import ml
from app.services.audit import log_action

MARCA = 'DATOS FICTICIOS DE DEMOSTRACIÓN'
BACKEND = Path(__file__).resolve().parents[1]
CARRERAS = (
    ('ISC', 'Ingeniería en Sistemas Computacionales'),
    ('IIA', 'Ingeniería en Inteligencia Artificial'),
    ('LCD', 'Licenciatura en Ciencia de Datos'),
)
# Nombres de los mapas curriculares de ESCOM; claves locales para la demostración.
MATERIAS = (
    ('CAL', 'Cálculo'), ('MD', 'Matemáticas Discretas'), ('FP', 'Fundamentos de Programación'),
    ('AED', 'Algoritmos y Estructuras de Datos'), ('AL', 'Álgebra Lineal'),
    ('PROB', 'Probabilidad'), ('EST', 'Estadística'), ('BD', 'Bases de Datos'),
    ('ADA', 'Análisis y Diseño de Algoritmos'), ('MN', 'Métodos Numéricos'),
    ('DWA', 'Desarrollo de Aplicaciones Web'), ('AM', 'Aprendizaje Automático'),
)
CUENTAS = (
    ('tutor1@sipde.local', 'Tutora Lucía Ortega', 'tutor'),
    ('tutor2@sipde.local', 'Tutor Daniel Flores', 'tutor'),
    ('operador@sipde.local', 'Operadora Inés Ríos', 'operador'),
)
NOMBRES = (
    'Ana Sofía', 'Diego', 'Ximena', 'José Luis', 'Fernanda', 'Emiliano', 'Valeria', 'Mateo',
    'Guadalupe', 'Santiago', 'Mariana', 'Juan Pablo', 'Camila', 'Ángel', 'Alejandra', 'Andrés',
    'Natalia', 'Ricardo', 'Renata', 'Eduardo',
)
APELLIDOS = (
    'Hernández Cruz', 'García Bautista', 'Martínez Luna', 'López Reyes', 'González Ríos',
    'Pérez Mendoza', 'Rodríguez Ortiz', 'Sánchez Vargas', 'Ramírez Morales', 'Torres Castillo',
)


def obtener_o_crear(db: Session, modelo, claves: dict, **campos):
    registro = db.scalar(select(modelo).filter_by(**claves))
    if registro is None:
        registro = modelo(**claves, **campos)
        db.add(registro)
        db.flush()
    return registro


def cargar_cuentas(db: Session) -> tuple[User, list[User], str | None, list[str]]:
    admin = db.scalar(select(User).filter_by(email=settings.admin_email))
    if admin is None:
        admin = User(
            email=settings.admin_email, full_name=f'Administrador · {MARCA}',
            role='admin', active=True, password_hash=hash_password(settings.admin_password),
        )
        db.add(admin)
    if admin.role != 'admin' or not admin.active:
        raise ValueError('La cuenta indicada por ADMIN_EMAIL debe ser una administradora activa.')

    clave = os.getenv('SEED_PASSWORD', dotenv_values(BACKEND / '.env').get('SEED_PASSWORD'))
    nuevas = []
    tutores = []
    for correo, nombre, rol in CUENTAS:
        usuario = db.scalar(select(User).filter_by(email=correo))
        if usuario is None:
            clave = clave or secrets.token_urlsafe(24)
            usuario = User(
                email=correo, full_name=f'{nombre} · {MARCA}', role=rol,
                password_hash=hash_password(clave),
            )
            db.add(usuario)
            nuevas.append(correo)
        if usuario.role != rol:
            raise ValueError(f'La cuenta {correo} tiene un rol distinto al previsto para la demostración.')
        if rol == 'tutor':
            tutores.append(usuario)
    db.flush()
    return admin, tutores, clave, nuevas


def cargar_catalogos(db: Session) -> tuple[list[Career], list[Period], list[Subject]]:
    carreras = [obtener_o_crear(db, Career, {'code': clave}, name=nombre) for clave, nombre in CARRERAS]
    periodos = []
    for anio in (2025, 2026):
        for semestre, inicio, fin in ((1, date(anio, 2, 1), date(anio, 6, 30)),
                                       (2, date(anio, 8, 1), date(anio, 12, 15))):
            clave = f'{anio}-{semestre}'
            periodos.append(obtener_o_crear(
                db, Period, {'code': clave}, name=f'{clave} · {MARCA}',
                start_date=inicio, end_date=fin, active=clave == '2026-2',
            ))
    materias = [
        obtener_o_crear(db, Subject, {'code': f'DEMO-{clave}'}, name=nombre)
        for clave, nombre in MATERIAS
    ]
    return carreras, periodos, materias


def cargar_alumnos(db: Session, carreras: list[Career], periodos: list[Period],
                   materias: list[Subject], tutores: list[User]) -> list[Student]:
    azar = random.Random(2026)
    alumnos = []
    for indice in range(40):
        carrera = carreras[indice % len(carreras)]
        tutor = tutores[indice % len(tutores)]
        nombre = f'{NOMBRES[indice % len(NOMBRES)]} {APELLIDOS[(indice + indice // 20) % len(APELLIDOS)]}'
        estado = {37: 'baja_temporal', 38: 'baja_temporal', 39: 'baja_definitiva'}.get(indice, 'activo')
        horas = azar.choice((12, 24, 32, 40)) if indice % 3 == 0 else 0
        alumno = obtener_o_crear(
            db, Student, {'enrollment_number': f'DEMO-{indice + 1:04d}'},
            full_name=nombre, program=carrera.code, career_id=carrera.id, tutor_id=tutor.id,
            semester=azar.randint(1, 8), employed=horas > 0, work_hours_weekly=horas,
            active=estado == 'activo', status=estado,
        )
        alumnos.append(alumno)

        # RA_01: notas aprobadas, una reprobada, todas reprobadas o ninguna nota.
        notas = [round(azar.uniform(7, 10), 1) for _ in range(4)]
        caso = indice % 4
        if caso == 1:
            notas[0] = 5.0
        elif caso == 2:
            notas = [4.0, 4.5, 5.0, 5.5]
        elif caso == 3:
            notas = [None] * 4
        for posicion, (materia, nota) in enumerate(zip(azar.sample(materias, 4), notas)):
            periodo = periodos[(indice + posicion // 2) % len(periodos)]
            obtener_o_crear(
                db, Enrollment, {'student_id': alumno.id, 'subject_id': materia.id, 'term': periodo.code},
                period_id=periodo.id, grade=nota,
            )
        if indice % 4 in (1, 2):
            obtener_o_crear(
                db, FollowUp, {'student_id': alumno.id, 'date': date(2026, 9, 15),
                               'note': f'{MARCA} · Revisión de hábitos de estudio y carga académica.'},
                tutor_id=tutor.id, agreement='Preparar un horario de estudio y revisarlo en dos semanas.',
            )
    return alumnos


def filas_demostracion(total: int = 15) -> list[dict]:
    """RNF_06 · Filas reales del conjunto de prueba (nunca de entrenamiento) para las predicciones demo.

    Se alternan alumnos que en el dataset desertaron, siguen inscritos o egresaron, para que la
    demostración muestre categorías de riesgo baja, media y alta. Los alumnos de la BD siguen
    siendo ficticios; solo el vector de variables proviene del dataset UCI.
    """
    import sys
    raiz = Path(__file__).resolve().parents[2]
    if str(raiz) not in sys.path:
        sys.path.insert(0, str(raiz))
    from ml.common import CONFIG_RECOMENDADA, FEATURE_SETS, load_dataset, make_target, split_train_test

    datos = load_dataset()
    columnas = FEATURE_SETS[CONFIG_RECOMENDADA['conjunto']]
    _, X_test, _, _ = split_train_test(datos[columnas], make_target(datos.Target, CONFIG_RECOMENDADA['tarea']))
    clases = datos.loc[X_test.index, 'Target']
    grupos = [list(clases[clases == clase].index) for clase in ('Dropout', 'Enrolled', 'Graduate')]
    filas: list[dict] = []
    for posicion in range(total):
        grupo = grupos[posicion % 3]
        indice = grupo[posicion // 3]
        fila = X_test.loc[indice].to_dict()
        filas.append({clave: (valor.item() if hasattr(valor, 'item') else valor) for clave, valor in fila.items()})
    return filas


def cargar_predicciones(db: Session, alumnos: list[Student], admin: User) -> None:
    ruta_modelo = ml.BASE_DIR / settings.model_path
    ruta_ejemplos = ruta_modelo.with_name('ejemplos_prediccion.json')
    try:
        ml.get_model_info()
        ejemplos = json.loads(ruta_ejemplos.read_text(encoding='utf-8'))['ejemplos']
    except FileNotFoundError:
        print('Aviso RNF_06: faltan los ejemplos ACE_03; se omiten las predicciones.')
        return
    except HTTPException as error:
        if error.status_code != 503:
            raise
        print(f'Aviso RNF_06: {error.detail} Se omiten las predicciones.')
        return
    try:
        filas = filas_demostracion()
    except (ImportError, OSError, KeyError, IndexError) as error:
        print(f'Aviso RNF_06: no se pudieron leer filas del dataset ({error}); se usan los ejemplos ACE_03.')
        filas = [ejemplo['features'] for ejemplo in ejemplos]
    if not filas:
        print('Aviso RNF_06: no hay filas de ejemplo ACE_03; se omiten las predicciones.')
        return

    ya_generados = set(db.scalars(
        select(PredictionLog.student_id)
        .join(AuditLog, AuditLog.entity_id == PredictionLog.id)
        .where(AuditLog.entity == PredictionLog.__tablename__, AuditLog.action == 'predecir',
               AuditLog.detail['origen'].as_string() == MARCA)
    ))
    for indice, alumno in enumerate(alumnos[:15]):
        if alumno.id in ya_generados:
            continue
        variables = filas[indice % len(filas)]
        resultado = ml.predict(variables)
        prediccion = PredictionLog(
            student_id=alumno.id, user_id=admin.id, model_version=resultado['modelo']['version'],
            task=resultado['modelo']['task'], created_at=datetime.fromisoformat(resultado['fecha_prediccion']),
            features=variables, predicted_class=resultado['clase_predicha'],
            probability_dropout=resultado['probabilidades']['Dropout'],
            risk_category=resultado['categoria_orientativa'],
        )
        db.add(prediccion)
        db.flush()
        log_action(db, admin, 'predecir', prediccion.__tablename__, prediccion.id, {'origen': MARCA})


def reiniciar_sqlite(url: URL) -> None:
    """Elimina la BD SQLite anterior, incluso si su esquema quedó obsoleto."""
    if url.get_backend_name() != 'sqlite':
        raise ValueError('--reset solo se admite en SQLite.')
    if url.query.get('uri', '').lower() in ('true', '1'):
        raise ValueError('--reset requiere una ruta SQLite directa, sin modo URI.')
    if url.database not in ('', None, ':memory:'):
        ruta = Path(url.database)
        ruta.unlink(missing_ok=True)
        for sufijo in ('-wal', '-shm', '-journal'):
            ruta.with_name(ruta.name + sufijo).unlink(missing_ok=True)


def sembrar(*, reset: bool = False) -> None:
    """Carga la demostración en una transacción y muestra los conteos de la BD."""
    url = make_url(settings.database_url)
    if reset and url.get_backend_name() != 'sqlite':
        raise ValueError('--reset solo se admite en SQLite.')
    if (not settings.admin_email or len(settings.admin_password) < 8
            or settings.admin_password.startswith('CAMBIAR')):
        raise ValueError('Configura ADMIN_EMAIL y ADMIN_PASSWORD en backend/.env antes de sembrar.')
    if settings.admin_email in {correo for correo, _, _ in CUENTAS}:
        raise ValueError('ADMIN_EMAIL debe ser distinto de las cuentas de tutor y operador de demostración.')
    if reset:
        reiniciar_sqlite(url)

    motor = create_engine(url)
    try:
        if reset:
            config = Config(str(BACKEND / 'alembic.ini'))
            with motor.connect() as conexion:
                config.attributes['connection'] = conexion
                command.upgrade(config, 'head')
        elif url.get_backend_name() == 'sqlite' and settings.auto_create_tables:
            Base.metadata.create_all(motor)

        print(MARCA)
        with Session(motor) as db:
            with db.begin():
                admin, tutores, clave, nuevas = cargar_cuentas(db)
                alumnos = cargar_alumnos(db, *cargar_catalogos(db), tutores)
                cargar_predicciones(db, alumnos, admin)
                clave_admin_valida = verify_password(settings.admin_password, admin.password_hash)
                conteos = {tabla.name: db.scalar(select(func.count()).select_from(tabla))
                           for tabla in Base.metadata.sorted_tables}
    finally:
        motor.dispose()

    print('Totales por tabla:')
    for tabla, cantidad in conteos.items():
        print(f'  {tabla}: {cantidad}')
    print('Cuentas de demostración:')
    print(f'  Administrador: {settings.admin_email}')
    if clave_admin_valida:
        print(f'  ADMIN_PASSWORD={settings.admin_password}')
    else:
        print('  El administrador conserva su contraseña actual.')
    for correo, _, rol in CUENTAS:
        print(f'  {rol}: {correo}')
    if nuevas:
        print(f'  SEED_PASSWORD={clave} (cuentas nuevas: {", ".join(nuevas)})')
    else:
        print('  Los tutores y el operador conservan sus contraseñas actuales.')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reset', action='store_true', help='Borra y recrea la BD SQLite antes de sembrar.')
    argumentos = parser.parse_args()
    try:
        sembrar(reset=argumentos.reset)
    except ValueError as error:
        parser.exit(1, f'{error}\n')


if __name__ == '__main__':
    main()
