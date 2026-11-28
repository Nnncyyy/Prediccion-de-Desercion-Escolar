"""RF_01 / CU_01 / PT_01 · Sesiones y credenciales de la cuenta activa."""
from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.deps import DB, UsuarioActual
from app.models import User
from app.schemas import LoginInput, LoginOut, PasswordChange, UserOut
from app.security import create_token, hash_password, verify_password
from app.services.audit import guardar, log_action

router = APIRouter(prefix='/api/auth', tags=['Autenticación'])


@router.post('/login', response_model=LoginOut)
def login(body: LoginInput, db: DB) -> dict:
    usuario = db.scalar(select(User).where(User.email == body.email))
    if not usuario or not usuario.active or not verify_password(body.password, usuario.password_hash):
        raise HTTPException(401, 'Credenciales incorrectas')
    log_action(db, usuario, 'login', 'users', usuario.id)
    db.commit()
    return {'access_token': create_token(usuario), 'token_type': 'bearer',
            'role': usuario.role, 'user': usuario}


@router.get('/me', response_model=UserOut)
def mi_cuenta(usuario: UsuarioActual) -> User:
    return usuario


@router.post('/change-password')
def cambiar_contrasena(body: PasswordChange, db: DB, usuario: UsuarioActual) -> dict[str, str]:
    if not verify_password(body.current_password, usuario.password_hash):
        raise HTTPException(401, 'Contraseña actual incorrecta')
    usuario.password_hash = hash_password(body.new_password)
    guardar(db, usuario, usuario, 'editar', 'Cambio de contraseña')
    return {'message': 'Contraseña actualizada'}
