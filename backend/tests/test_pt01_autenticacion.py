"""Pruebas complementarias de autenticación y gestión de credenciales."""

from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.config import settings
from helpers import PASSWORD, actors, bearer, fixture_password_hash, login, request_json


def test_pt01_vigencia_del_token(api_client, actors):
    """PT_01 · CU_01/RF_01 · Verificar las claims de login. Esperado: Bearer del usuario con vigencia de ocho horas."""
    user_id, _ = actors['operador']
    before = datetime.now(timezone.utc)
    session = login(api_client, 'operador@pt.sipde.test', PASSWORD)
    after = datetime.now(timezone.utc)
    assert session['token_type'] == 'bearer'
    claims = jwt.decode(session['access_token'], settings.jwt_secret, algorithms=['HS256'])
    assert (claims['sub'], claims['role']) == (str(user_id), 'operador')
    assert int((before + timedelta(hours=8)).timestamp()) <= claims['exp']
    assert claims['exp'] <= int((after + timedelta(hours=8)).timestamp())


def test_pt01_login_no_distingue_credenciales_invalidas(api_client):
    """PT_01 · CU_01/RF_01 · Comparar contraseña errónea y cuenta inexistente. Esperado: mismo 401 y mismo mensaje."""
    for email in (settings.admin_email, 'inexistente@pt.sipde.test'):
        body = request_json(api_client, 'POST', '/api/auth/login', 401,
                            json={'email': email, 'password': 'ClaveErronea123'})
        assert body == {'detail': 'Credenciales incorrectas'}


def test_pt01_cuenta_desactivada(api_client, actors):
    """PT_01 · CU_01/RF_01 · Desactivar una cuenta con sesión vigente. Esperado: login y JWT previo rechazados con 401."""
    _, admin = actors['admin']
    user_id, _ = actors['operador']
    session = login(api_client, 'operador@pt.sipde.test', PASSWORD)
    headers = bearer(session['access_token'])
    assert request_json(api_client, 'PATCH', f'/api/users/{user_id}', 200,
                        headers=admin, json={'active': False})['active'] is False
    assert request_json(api_client, 'POST', '/api/auth/login', 401,
                        json={'email': 'operador@pt.sipde.test', 'password': PASSWORD}) == {
        'detail': 'Credenciales incorrectas',
    }
    assert request_json(api_client, 'GET', '/api/auth/me', 401, headers=headers) == {'detail': 'Sesión inválida'}


@pytest.mark.parametrize('kind', ['expirado', 'firma-alterada'])
def test_pt01_jwt_invalido(api_client, actors, kind):
    """PT_01 · CU_01/RF_01 · Presentar un JWT vencido o alterado. Esperado: 401 y desafío Bearer."""
    user_id, headers = actors['admin']
    token = headers['Authorization'].split()[1]
    if kind == 'expirado':
        token = jwt.encode({'sub': str(user_id), 'role': 'admin',
                            'exp': datetime.now(timezone.utc) - timedelta(minutes=1)},
                           settings.jwt_secret, algorithm='HS256')
    else:
        header, payload, signature = token.split('.')
        replacement = 'A' if signature[0] != 'A' else 'B'
        token = '.'.join((header, payload, replacement + signature[1:]))
    response = api_client.get('/api/auth/me', headers=bearer(token))
    assert response.status_code == 401, response.text
    assert response.json() == {'detail': 'Sesión inválida'}
    assert response.headers['WWW-Authenticate'] == 'Bearer'


def test_pt01_cambio_sin_token(api_client):
    """PT_01 · CU_01/RF_01 · Solicitar un cambio de contraseña sin sesión. Esperado: 401."""
    request_json(api_client, 'POST', '/api/auth/change-password', 401,
                 json={'current_password': settings.admin_password, 'new_password': PASSWORD})


@pytest.mark.parametrize(('current', 'new_password', 'expected_status'), [
    pytest.param('ClaveErronea123', 'OtraClaveSegura123', 401, id='actual-incorrecta'),
    pytest.param(PASSWORD, '1234567', 422, id='nueva-corta'),
])
def test_pt01_cambio_rechazado(api_client, actors, current, new_password, expected_status):
    """PT_01 · CU_01/RF_01 · Enviar contraseñas inválidas. Esperado: 401 o 422 y la clave anterior aún funciona."""
    _, headers = actors['operador']
    detail = request_json(api_client, 'POST', '/api/auth/change-password', expected_status,
                          headers=headers, json={'current_password': current, 'new_password': new_password})['detail']
    if expected_status == 401:
        assert detail == 'Contraseña actual incorrecta'
    else:
        assert detail[0]['loc'] == ['body', 'new_password']
    assert login(api_client, 'operador@pt.sipde.test', PASSWORD)['user']['role'] == 'operador'


def test_pt01_cambio_correcto(api_client, actors):
    """PT_01 · CU_01/RF_01 · Cambiar la contraseña y repetir login. Esperado: clave nueva válida y clave anterior rechazada."""
    user_id, headers = actors['tutor']
    new_password = 'SIPDE_Clave_Nueva_01'
    assert request_json(api_client, 'POST', '/api/auth/change-password', 200, headers=headers,
                        json={'current_password': PASSWORD, 'new_password': new_password}) == {
        'message': 'Contraseña actualizada',
    }
    email = 'tutor@pt.sipde.test'
    request_json(api_client, 'POST', '/api/auth/login', 401, json={'email': email, 'password': PASSWORD})
    assert login(api_client, email, new_password)['user']['id'] == user_id
