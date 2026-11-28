"""INT_02 · Ensamblaje de routers y arranque de la aplicación SIPDE."""
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.config import settings
from app.database import Base, SessionLocal, engine
from app.deps import error_validacion
from app.models import User
from app.routers import (
    alerts, audit, auth, catalogs, dashboard, enrollments, followups, health,
    imports, ml, reports, students, users,
)
from app.security import hash_password


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """RF_01 / RNF_01 · Validar configuración y crear únicamente la cuenta inicial."""
    if not settings.jwt_secret or settings.jwt_secret.startswith('CAMBIAR') or len(settings.jwt_secret) < 24:
        raise RuntimeError('Configura JWT_SECRET seguro en backend/.env')
    if not settings.admin_email or not settings.admin_password or settings.admin_password.startswith('CAMBIAR'):
        raise RuntimeError('Configura ADMIN_EMAIL y ADMIN_PASSWORD en backend/.env')
    if len(settings.admin_password) < 8:
        raise RuntimeError('ADMIN_PASSWORD debe tener al menos 8 caracteres')
    if settings.auto_create_tables:
        Base.metadata.create_all(engine)
    with SessionLocal() as db:
        if not db.scalar(select(User.id).where(User.email == settings.admin_email)):
            cuenta = User(email=settings.admin_email, full_name='Administrador', role='admin',
                          password_hash=hash_password(settings.admin_password))
            db.add(cuenta)
            db.commit()
    yield


app = FastAPI(title='SIPDE API', version='0.1.0', lifespan=lifespan,
              exception_handlers={RequestValidationError: error_validacion})
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origen.strip() for origen in settings.cors_origins.split(',')],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
    expose_headers=['X-Total-Count'],
)
for modulo in (health, auth, users, students, catalogs, enrollments, alerts, followups,
               dashboard, ml, audit, imports, reports):
    app.include_router(modulo.router)
