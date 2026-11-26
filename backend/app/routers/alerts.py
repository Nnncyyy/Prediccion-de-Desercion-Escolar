"""RF_10 / CU_05 / RN_05 · Alerta RA_01 independiente del historial ML."""
from fastapi import APIRouter
from sqlalchemy import select

from app.deps import DB, UsuarioActual, estudiante_visible
from app.models import Enrollment
from app.services.risk import academic_alert

router = APIRouter(prefix='/api/students', tags=['Alertas'])


@router.get('/{student_id}/alert')
def alerta(student_id: int, db: DB, usuario: UsuarioActual) -> dict:
    alumno = estudiante_visible(db, usuario, student_id)
    notas = db.scalars(select(Enrollment.grade).where(Enrollment.student_id == student_id))
    return {'student_id': student_id, **academic_alert(alumno, list(notas))}
