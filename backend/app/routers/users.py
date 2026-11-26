"""RF_02 / RN_04 · Administración de BD_01 reservada a ACT_01."""
from collections.abc import Sequence

from fastapi import APIRouter, HTTPException
from sqlalchemy import select, text

from app.deps import Administrador, DB, SIN_PERMISO
from app.models import User
from app.schemas import UserCreate, UserOut, UserPatch
from app.security import hash_password
from app.services.audit import aplicar_cambios, guardar

router = APIRouter(prefix='/api/users', tags=['Usuarios'])


@router.get('', response_model=list[UserOut])
def listar(db: DB, usuario: Administrador) -> Sequence[User]:
    return db.scalars(select(User).order_by(User.id)).all()


@router.post('', response_model=UserOut, status_code=201)
def crear(body: UserCreate, db: DB, usuario: Administrador) -> User:
    cuenta = User(**body.model_dump(exclude={'password'}), password_hash=hash_password(body.password))
    guardar(db, usuario, cuenta, 'crear', conflicto='Correo duplicado')
    return cuenta


@router.patch('/{user_id}', response_model=UserOut)
def editar(user_id: int, body: UserPatch, db: DB, usuario: Administrador) -> User:
    # RN_04 · Serializar las bajas concurrentes antes de verificar la sesión del admin.
    if db.get_bind().dialect.name == 'sqlite':
        db.execute(text('BEGIN IMMEDIATE'))
    admins = db.scalars(select(User.id).where(User.role == 'admin', User.active.is_(True))
                        .order_by(User.id).with_for_update()).all()
    if usuario.id not in admins:
        raise HTTPException(403, SIN_PERMISO)
    cuenta = db.get(User, user_id, populate_existing=True)
    if cuenta is None:
        raise HTTPException(404, 'Usuario no encontrado')
    campos = body.model_dump(exclude_unset=True)
    retirar = campos.get('role', cuenta.role) != 'admin' or not campos.get('active', cuenta.active)
    if cuenta.id in admins and retirar and (cuenta.id == usuario.id or len(admins) == 1):
        raise HTTPException(409, 'Debe conservar su propia cuenta administradora activa')
    if 'password' in campos:
        campos['password_hash'] = hash_password(campos.pop('password'))
    accion = aplicar_cambios(cuenta, campos)
    guardar(db, usuario, cuenta, accion)
    return cuenta
