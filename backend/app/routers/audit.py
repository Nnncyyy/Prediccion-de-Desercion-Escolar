"""RNF_05 / BD_12 · Bitácora de consulta exclusiva de ACT_01."""
from collections.abc import Sequence

from fastapi import APIRouter
from sqlalchemy import select

from app.deps import Administrador, DB, Inicio, Limite
from app.models import AuditLog
from app.schemas import AuditOut

router = APIRouter(prefix='/api/audit', tags=['Auditoría'])


@router.get('', response_model=list[AuditOut])
def listar(db: DB, usuario: Administrador, entity: str | None = None, user_id: int | None = None,
           skip: Inicio = 0, limit: Limite = 100) -> Sequence[AuditLog]:
    consulta = select(AuditLog)
    if entity is not None:
        consulta = consulta.where(AuditLog.entity == entity)
    if user_id is not None:
        consulta = consulta.where(AuditLog.user_id == user_id)
    return db.scalars(consulta.order_by(AuditLog.id.desc()).offset(skip).limit(limit)).all()
