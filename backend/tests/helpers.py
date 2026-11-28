"""Fábricas de datos sintéticos y solicitudes para las pruebas del backend."""

import pytest
from sqlalchemy import select

from app import database
from app.config import settings
from app.models import User
from app.security import create_token, hash_password

PASSWORD = 'SIPDE_Pruebas_123'


def request_json(client, method, path, status, **kwargs):
    response = client.request(method, path, **kwargs)
    assert response.status_code == status, response.text
    return response.json()


def create(client, headers, resource, **data):
    return request_json(client, 'POST', f'/api/{resource}', 201, headers=headers, json=data)


def student_data(number='PT-A001', **changes):
    return {
        'enrollment_number': number,
        'full_name': 'Ana García',
        'program': 'Sistemas',
        'semester': 2,
        **changes,
    }


def account_data(role):
    return {
        'email': f'{role}@pt.sipde.test',
        'full_name': f'Cuenta {role}',
        'role': role,
        'password': PASSWORD,
    }


def bearer(token):
    return {'Authorization': f'Bearer {token}'}


def login(client, email, password):
    return request_json(client, 'POST', '/api/auth/login', 200,
                        json={'email': email, 'password': password})


@pytest.fixture(scope='session')
def fixture_password_hash():
    return hash_password(PASSWORD)


@pytest.fixture
def actors(api_client, fixture_password_hash):
    """Prepara los tres roles en la BD temporal y emite JWT con el firmante de la API."""
    with database.SessionLocal() as db:
        admin = db.scalars(select(User).filter_by(email=settings.admin_email)).one()
        users = [admin]
        for role in ('operador', 'tutor'):
            data = account_data(role)
            data.pop('password')
            users.append(User(**data, password_hash=fixture_password_hash))
        db.add_all(users)
        db.flush()
        result = {user.role: (user.id, bearer(create_token(user))) for user in users}
        db.commit()
    return result
