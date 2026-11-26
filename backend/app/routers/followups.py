"""RF_14 / BD_08 · Seguimiento de tutorías dentro del alcance RN_04."""
from collections.abc import Sequence

from fastapi import APIRouter
from sqlalchemy import select

from app.deps import DB, Orientador, UsuarioActual, estudiante_visible
from app.models import FollowUp
from app.schemas import FollowUpCreate, FollowUpOut
from app.services.audit import guardar

router = APIRouter(prefix='/api/students', tags=['Seguimiento'])


@router.get('/{student_id}/followups', response_model=list[FollowUpOut])
def listar(student_id: int, db: DB, usuario: UsuarioActual) -> Sequence[FollowUp]:
    estudiante_visible(db, usuario, student_id)
    consulta = select(FollowUp).where(FollowUp.student_id == student_id)
    return db.scalars(consulta.order_by(FollowUp.date.desc(), FollowUp.id.desc())).all()


@router.post('/{student_id}/followups', response_model=FollowUpOut, status_code=201)
def crear(student_id: int, body: FollowUpCreate, db: DB, usuario: Orientador) -> FollowUp:
    estudiante_visible(db, usuario, student_id)
    seguimiento = FollowUp(student_id=student_id, tutor_id=usuario.id, **body.model_dump())
    guardar(db, usuario, seguimiento, 'crear')
    return seguimiento
