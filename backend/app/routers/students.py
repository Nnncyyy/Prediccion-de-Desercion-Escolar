"""RF_03 / RF_06 / CU_02 / PT_02 · Expedientes y asignación de tutor."""
from collections.abc import Sequence

from fastapi import APIRouter, HTTPException, Response
from sqlalchemy import func, or_, select

from app.deps import (
    Administrador, Capturista, DB, Inicio, Limite, UsuarioActual, estudiante_visible, estudiantes_visibles,
)
from app.models import Career, Student, User
from app.schemas import Estado, StudentCreate, StudentDeactivate, StudentOut, StudentPatch, StudentTutor
from app.services.audit import aplicar_cambios, guardar

router = APIRouter(prefix='/api/students', tags=['Estudiantes'])


@router.get('', response_model=list[StudentOut])
def listar(response: Response, db: DB, usuario: UsuarioActual, q: str | None = None,
           career_id: int | None = None, status: Estado | None = None, active: bool | None = None,
           tutor_id: int | None = None, skip: Inicio = 0, limit: Limite = 100) -> Sequence[Student]:
    consulta = estudiantes_visibles(usuario)
    if q:
        columnas = (Student.enrollment_number, Student.full_name)
        if db.get_bind().dialect.name == 'sqlite':
            coincidencias = [func.sipde_casefold(c).contains(q.casefold(), autoescape=True) for c in columnas]
        else:
            coincidencias = [c.icontains(q, autoescape=True) for c in columnas]
        consulta = consulta.where(or_(*coincidencias))
    for columna, valor in ((Student.career_id, career_id), (Student.status, status),
                           (Student.active, active), (Student.tutor_id, tutor_id)):
        if valor is not None:
            consulta = consulta.where(columna == valor)
    total = db.scalar(select(func.count()).select_from(consulta.subquery()))
    response.headers['X-Total-Count'] = str(total)
    return db.scalars(consulta.order_by(Student.id.desc()).offset(skip).limit(limit)).all()


def completar_programa(db: DB, alumno: Student) -> None:
    carrera = db.get(Career, alumno.career_id) if alumno.career_id is not None else None
    if alumno.career_id is not None and carrera is None:
        raise HTTPException(404, 'Carrera no encontrada')
    if not alumno.program.strip():
        if carrera is None:
            raise HTTPException(422, 'Indique program o una carrera')
        alumno.program = carrera.name


@router.post('', response_model=StudentOut, status_code=201)
def crear(body: StudentCreate, db: DB, usuario: Capturista) -> Student:
    alumno = Student(**body.model_dump())
    completar_programa(db, alumno)
    guardar(db, usuario, alumno, 'crear', conflicto='Matrícula duplicada')
    return alumno


@router.get('/{student_id}', response_model=StudentOut)
def obtener(student_id: int, db: DB, usuario: UsuarioActual) -> Student:
    return estudiante_visible(db, usuario, student_id)


@router.patch('/{student_id}', response_model=StudentOut)
def editar(student_id: int, body: StudentPatch, db: DB, usuario: Capturista) -> Student:
    alumno = estudiante_visible(db, usuario, student_id)
    aplicar_cambios(alumno, body.model_dump(exclude_unset=True))
    completar_programa(db, alumno)
    guardar(db, usuario, alumno, 'editar', conflicto='Matrícula duplicada')
    return alumno


@router.post('/{student_id}/deactivate', response_model=StudentOut)
def dar_baja(student_id: int, db: DB, usuario: Administrador,
             body: StudentDeactivate | None = None) -> Student:
    alumno = estudiante_visible(db, usuario, student_id)
    baja = body or StudentDeactivate()
    alumno.active = False
    alumno.status = baja.status
    guardar(db, usuario, alumno, 'baja', baja.model_dump(exclude_none=True))
    return alumno


@router.post('/{student_id}/reactivate', response_model=StudentOut)
def reactivar(student_id: int, db: DB, usuario: Administrador) -> Student:
    alumno = estudiante_visible(db, usuario, student_id)
    alumno.active = True
    alumno.status = 'activo'
    guardar(db, usuario, alumno, 'reactivar')
    return alumno


@router.put('/{student_id}/tutor', response_model=StudentOut)
def asignar_tutor(student_id: int, body: StudentTutor, db: DB, usuario: Administrador) -> Student:
    alumno = estudiante_visible(db, usuario, student_id)
    if body.tutor_id is not None:
        tutor = db.get(User, body.tutor_id)
        if tutor is None:
            raise HTTPException(404, 'Usuario no encontrado')
        if tutor.role != 'tutor' or not tutor.active:
            raise HTTPException(422, 'Se requiere un tutor activo')
    alumno.tutor_id = body.tutor_id
    guardar(db, usuario, alumno, 'editar', body.model_dump())
    return alumno
