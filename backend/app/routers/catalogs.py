"""RF_04 · Lectura compartida y mantenimiento administrativo de BD_03, BD_06 y BD_09."""
from collections.abc import Sequence
from typing import TypeVar

from fastapi import APIRouter, HTTPException
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.deps import Administrador, DB, UsuarioActual
from app.models import Career, Enrollment, Period, Subject
from app.schemas import (
    CareerCreate, CareerOut, CareerPatch, PeriodCreate, PeriodOut, PeriodPatch,
    SubjectCreate, SubjectOut, SubjectPatch,
)
from app.services.audit import aplicar_cambios, guardar

router = APIRouter(prefix='/api', tags=['Catálogos'])
Catalogo = TypeVar('Catalogo', Career, Period, Subject)


def filas(db: Session, modelo: type[Catalogo], active: bool | None) -> Sequence[Catalogo]:
    consulta = select(modelo).order_by(modelo.name, modelo.id)
    if active is not None:
        consulta = consulta.where(modelo.active == active)
    return db.scalars(consulta).all()


def buscar(db: Session, modelo: type[Catalogo], clave: int) -> Catalogo:
    fila = db.get(modelo, clave)
    if fila is None:
        raise HTTPException(404, 'Registro de catálogo no encontrado')
    return fila


@router.get('/careers', response_model=list[CareerOut])
def carreras(db: DB, usuario: UsuarioActual, active: bool | None = None) -> Sequence[Career]:
    return filas(db, Career, active)


@router.post('/careers', response_model=CareerOut, status_code=201)
def crear_carrera(body: CareerCreate, db: DB, usuario: Administrador) -> Career:
    carrera = Career(**body.model_dump())
    guardar(db, usuario, carrera, 'crear', conflicto='Código o nombre de carrera duplicado')
    return carrera


@router.patch('/careers/{career_id}', response_model=CareerOut)
def editar_carrera(career_id: int, body: CareerPatch, db: DB, usuario: Administrador) -> Career:
    carrera = buscar(db, Career, career_id)
    accion = aplicar_cambios(carrera, body.model_dump(exclude_unset=True))
    guardar(db, usuario, carrera, accion, conflicto='Código o nombre de carrera duplicado')
    return carrera


@router.get('/periods', response_model=list[PeriodOut])
def periodos(db: DB, usuario: UsuarioActual, active: bool | None = None) -> Sequence[Period]:
    return filas(db, Period, active)


def validar_fechas(periodo: Period) -> None:
    if periodo.start_date and periodo.end_date and periodo.end_date < periodo.start_date:
        raise HTTPException(422, 'La fecha final debe ser igual o posterior a la inicial')


@router.post('/periods', response_model=PeriodOut, status_code=201)
def crear_periodo(body: PeriodCreate, db: DB, usuario: Administrador) -> Period:
    periodo = Period(**body.model_dump())
    validar_fechas(periodo)
    guardar(db, usuario, periodo, 'crear', conflicto='Código de periodo duplicado')
    return periodo


@router.patch('/periods/{period_id}', response_model=PeriodOut)
def editar_periodo(period_id: int, body: PeriodPatch, db: DB, usuario: Administrador) -> Period:
    periodo = buscar(db, Period, period_id)
    anterior = periodo.code
    accion = aplicar_cambios(periodo, body.model_dump(exclude_unset=True))
    validar_fechas(periodo)
    if periodo.code != anterior:
        # RF_05 · Mantener term compatible también para inscripciones anteriores.
        try:
            db.flush()
            db.execute(update(Enrollment).where(Enrollment.period_id == period_id).values(term=periodo.code))
        except IntegrityError as error:
            db.rollback()
            raise HTTPException(409, 'Código de periodo o inscripción duplicados') from error
    guardar(db, usuario, periodo, accion)
    return periodo


@router.get('/subjects', response_model=list[SubjectOut])
def materias(db: DB, usuario: UsuarioActual, active: bool | None = None) -> Sequence[Subject]:
    return filas(db, Subject, active)


@router.post('/subjects', response_model=SubjectOut, status_code=201)
def crear_materia(body: SubjectCreate, db: DB, usuario: Administrador) -> Subject:
    materia = Subject(**body.model_dump())
    guardar(db, usuario, materia, 'crear', conflicto='Código de materia duplicado')
    return materia


@router.patch('/subjects/{subject_id}', response_model=SubjectOut)
def editar_materia(subject_id: int, body: SubjectPatch, db: DB, usuario: Administrador) -> Subject:
    materia = buscar(db, Subject, subject_id)
    accion = aplicar_cambios(materia, body.model_dump(exclude_unset=True))
    guardar(db, usuario, materia, accion, conflicto='Código de materia duplicado')
    return materia
