"""RF_05 / CU_03 / PT_03 · Inscripciones con periodo textual compatible."""
from collections.abc import Sequence

from fastapi import APIRouter, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as insertar_postgres
from sqlalchemy.dialects.sqlite import insert as insertar_sqlite
from sqlalchemy.orm import Session

from app.deps import Capturista, DB, UsuarioActual, estudiante_visible
from app.models import Enrollment, Period, Subject, User
from app.schemas import EnrollmentCreate, EnrollmentOut, EnrollmentPatch
from app.services.audit import guardar, log_action

router = APIRouter(prefix='/api', tags=['Inscripciones'])
DUPLICADA = 'Inscripción ya registrada para el periodo'


def resolver_periodo(db: Session, usuario: User, term: str | None, period_id: int | None) -> Period:
    if period_id is not None:
        periodo = db.get(Period, period_id, with_for_update=True)
        if periodo is None:
            raise HTTPException(404, 'Periodo no encontrado')
        if term is not None and term != periodo.code:
            raise HTTPException(422, 'term y period_id deben identificar el mismo periodo')
        return periodo
    if term is None:
        raise HTTPException(422, 'Indique term o period_id')

    # BD_06 · Dos inscripciones concurrentes pueden solicitar el mismo código nuevo.
    insertar = insertar_sqlite if db.get_bind().dialect.name == 'sqlite' else insertar_postgres
    sentencia = insertar(Period).values(code=term, name=term, active=True)
    clave = db.scalar(sentencia.on_conflict_do_nothing(index_elements=['code']).returning(Period.id))
    if clave is not None:
        log_action(db, usuario, 'crear', 'periods', clave, 'Alta automática por inscripción')
    return db.scalars(select(Period).where(Period.code == term).with_for_update()).one()


def obtener(db: Session, clave: int) -> Enrollment:
    fila = db.get(Enrollment, clave)
    if fila is None:
        raise HTTPException(404, 'Inscripción no encontrada')
    return fila


@router.post('/enrollments', response_model=EnrollmentOut, status_code=201)
def crear(body: EnrollmentCreate, db: DB, usuario: Capturista) -> Enrollment:
    alumno = estudiante_visible(db, usuario, body.student_id)
    if not alumno.active:
        raise HTTPException(409, 'El estudiante está inactivo')
    if db.get(Subject, body.subject_id) is None:
        raise HTTPException(404, 'Materia no encontrada')
    periodo = resolver_periodo(db, usuario, body.term, body.period_id)
    fila = Enrollment(student_id=alumno.id, subject_id=body.subject_id, term=periodo.code,
                      period_id=periodo.id, grade=body.grade)
    guardar(db, usuario, fila, 'crear', conflicto=DUPLICADA)
    return fila


@router.patch('/enrollments/{enrollment_id}', response_model=EnrollmentOut)
def editar(enrollment_id: int, body: EnrollmentPatch, db: DB, usuario: Capturista) -> Enrollment:
    fila = obtener(db, enrollment_id)
    if 'grade' in body.model_fields_set:
        fila.grade = body.grade
    if body.model_fields_set & {'term', 'period_id'}:
        periodo = resolver_periodo(db, usuario, body.term, body.period_id)
        fila.period_id = periodo.id
        fila.term = periodo.code
    guardar(db, usuario, fila, 'editar', conflicto=DUPLICADA)
    return fila


@router.delete('/enrollments/{enrollment_id}', status_code=204)
def eliminar(enrollment_id: int, db: DB, usuario: Capturista) -> Response:
    fila = obtener(db, enrollment_id)
    log_action(db, usuario, 'baja', 'enrollments', fila.id, {'student_id': fila.student_id})
    db.delete(fila)
    db.commit()
    return Response(status_code=204)


@router.get('/students/{student_id}/enrollments', response_model=list[EnrollmentOut])
def listar(student_id: int, db: DB, usuario: UsuarioActual) -> Sequence[Enrollment]:
    estudiante_visible(db, usuario, student_id)
    consulta = select(Enrollment).where(Enrollment.student_id == student_id)
    return db.scalars(consulta.order_by(Enrollment.id.desc())).all()
