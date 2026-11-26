"""RF_01 / RN_04 / RNF_01 · Autenticación y alcance por rol de cada consulta."""
from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Student, User
from app.schemas import Rol

DB = Annotated[Session, Depends(get_db)]
Inicio = Annotated[int, Query(ge=0)]
Limite = Annotated[int, Query(ge=1)]
bearer = HTTPBearer(auto_error=False)
SIN_PERMISO = 'No tiene permiso para esta acción'


def current_user(
    db: DB, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]
) -> User:
    usuario = None
    if credentials:
        try:
            datos = jwt.decode(credentials.credentials, settings.jwt_secret, algorithms=['HS256'])
            usuario = db.get(User, int(datos['sub']))
        except (jwt.PyJWTError, KeyError, TypeError, ValueError, OverflowError):
            pass
    if usuario is None or not usuario.active:
        raise HTTPException(401, 'Sesión inválida', headers={'WWW-Authenticate': 'Bearer'})
    return usuario


UsuarioActual = Annotated[User, Depends(current_user)]


def require_roles(*roles: Rol) -> Callable:
    def verificar(usuario: UsuarioActual) -> User:
        if usuario.role not in roles:
            raise HTTPException(403, SIN_PERMISO)
        return usuario

    return verificar


Administrador = Annotated[User, Depends(require_roles('admin'))]
Capturista = Annotated[User, Depends(require_roles('admin', 'operador'))]
Orientador = Annotated[User, Depends(require_roles('admin', 'tutor'))]


def estudiantes_visibles(usuario: User) -> Select:
    consulta = select(Student)
    if usuario.role == 'tutor':
        consulta = consulta.where(Student.tutor_id == usuario.id)
    return consulta


def estudiante_visible(db: Session, usuario: User, student_id: int) -> Student:
    alumno = db.scalar(estudiantes_visibles(usuario).where(Student.id == student_id))
    if alumno is None:
        raise HTTPException(404, 'Estudiante no encontrado')
    return alumno


async def error_validacion(request: Request, exc: RequestValidationError) -> JSONResponse:
    """RNF_01 · Señala los campos inválidos sin devolver credenciales ni datos personales."""
    mensajes = {
        'missing': 'Campo obligatorio',
        'extra_forbidden': 'Campo no permitido',
        'literal_error': 'Valor fuera del catálogo permitido',
        'string_too_short': 'Texto demasiado corto',
        'string_too_long': 'Texto demasiado largo',
        'json_invalid': 'JSON inválido',
    }
    errores = [
        {'loc': error['loc'], 'msg': mensajes.get(error['type'], 'Valor inválido'), 'type': error['type']}
        for error in exc.errors()
    ]
    return JSONResponse(status_code=422, content={'detail': errores})
