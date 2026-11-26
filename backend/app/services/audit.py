"""BD_12 / RNF_05 · La mutación del dominio y su bitácora se confirman juntas."""
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import AuditLog, Career, Enrollment, FollowUp, Period, PredictionLog, Student, Subject, User

Registro = Career | Enrollment | FollowUp | Period | PredictionLog | Student | Subject | User
Detalle = str | dict | None


def log_action(db: Session, user: User | None, action: str, entity: str,
               entity_id: int, detail: Detalle = None) -> None:
    db.add(AuditLog(user_id=user.id if user else None, action=action, entity=entity,
                    entity_id=entity_id, detail=detail))


def guardar(db: Session, usuario: User, objeto: Registro, accion: str, detalle: Detalle = None,
            conflicto: str = 'Conflicto de integridad') -> None:
    """RNF_03 · Obtiene el ID antes de registrar la acción y revierte ambos si falla."""
    try:
        db.add(objeto)
        db.flush()
        log_action(db, usuario, accion, objeto.__tablename__, objeto.id, detalle)
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(409, conflicto) from error


def aplicar_cambios(objeto: User | Student | Career | Period | Subject, campos: dict) -> str:
    accion = 'editar'
    if 'active' in campos and campos['active'] != objeto.active:
        accion = 'reactivar' if campos['active'] else 'baja'
    for campo, valor in campos.items():
        setattr(objeto, campo, valor)
    return accion
