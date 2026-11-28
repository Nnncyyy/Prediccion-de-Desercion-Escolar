"""INT_02 · Estado público del servicio SIPDE."""
from fastapi import APIRouter

router = APIRouter(prefix='/api/health', tags=['Servicio'])


@router.get('')
def salud() -> dict[str, str]:
    return {'status': 'ok', 'service': 'SIPDE'}
