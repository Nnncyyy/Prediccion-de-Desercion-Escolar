"""Matriz HTTP de permisos para las operaciones publicadas por SIPDE."""

import pytest

from app import database
from app.config import settings
from app.main import app
from app.models import Career, Enrollment, Period, Student, Subject
from helpers import PASSWORD, account_data, actors, create, fixture_password_hash, request_json, student_data

# El orden de las expectativas es admin, operador y tutor (ACT_01, ACT_03 y ACT_02).
ROLES = ('admin', 'operador', 'tutor')
PUBLIC = [
    ('GET', '/api/health'),
    ('POST', '/api/auth/login'),
]
MATRIX = [
    ('GET', '/api/health', (200, 200, 200)),
    ('POST', '/api/auth/login', (200, 200, 200)),
    ('GET', '/api/auth/me', (200, 200, 200)),
    ('POST', '/api/auth/change-password', (200, 200, 200)),
    ('GET', '/api/users', (200, 403, 403)),
    ('POST', '/api/users', (201, 403, 403)),
    ('PATCH', '/api/users/{user_id}', (200, 403, 403)),
    ('GET', '/api/careers', (200, 200, 200)),
    ('POST', '/api/careers', (201, 403, 403)),
    ('PATCH', '/api/careers/{career_id}', (200, 403, 403)),
    ('GET', '/api/periods', (200, 200, 200)),
    ('POST', '/api/periods', (201, 403, 403)),
    ('PATCH', '/api/periods/{period_id}', (200, 403, 403)),
    ('GET', '/api/subjects', (200, 200, 200)),
    ('POST', '/api/subjects', (201, 403, 403)),
    ('PATCH', '/api/subjects/{subject_id}', (200, 403, 403)),
    ('GET', '/api/students', (200, 200, 200)),
    ('POST', '/api/students', (201, 201, 403)),
    ('GET', '/api/students/{student_id}', (200, 200, 200)),
    ('PATCH', '/api/students/{student_id}', (200, 200, 403)),
    ('POST', '/api/students/{student_id}/deactivate', (200, 403, 403)),
    ('POST', '/api/students/{student_id}/reactivate', (200, 403, 403)),
    ('PUT', '/api/students/{student_id}/tutor', (200, 403, 403)),
    ('GET', '/api/students/{student_id}/enrollments', (200, 200, 200)),
    ('POST', '/api/enrollments', (201, 201, 403)),
    ('PATCH', '/api/enrollments/{enrollment_id}', (200, 200, 403)),
    ('DELETE', '/api/enrollments/{enrollment_id}', (204, 204, 403)),
    ('GET', '/api/students/{student_id}/alert', (200, 200, 200)),
    ('GET', '/api/students/{student_id}/followups', (200, 200, 200)),
    ('POST', '/api/students/{student_id}/followups', (201, 403, 201)),
    ('GET', '/api/ml/model', (200, 200, 200)),
    ('GET', '/api/ml/schema', (200, 200, 200)),
    ('POST', '/api/ml/predict', (200, 403, 200)),
    ('GET', '/api/ml/predictions', (200, 403, 200)),
    ('GET', '/api/students/{student_id}/predictions', (200, 403, 200)),
    ('GET', '/api/dashboard', (200, 200, 200)),
    ('GET', '/api/audit', (200, 403, 403)),
    # RF_07 y RF_13 se rigen por el contrato HTTP.
    ('POST', '/api/import/students', (200, 403, 403)),
    ('POST', '/api/import/enrollments', (200, 403, 403)),
    ('GET', '/api/import/templates/{kind}', (200, 403, 403)),
    ('GET', '/api/reports/summary', (200, 403, 200)),
    ('GET', '/api/reports/students', (200, 403, 200)),
    ('GET', '/api/reports/students.csv', (200, 403, 200)),
    ('GET', '/api/reports/predictions.csv', (200, 403, 200)),
]
UNASSIGNED = [
    ('GET', '/api/students/{student_id}', (200, 200, 404)),
    ('GET', '/api/students/{student_id}/enrollments', (200, 200, 404)),
    ('GET', '/api/students/{student_id}/alert', (200, 200, 404)),
    ('GET', '/api/students/{student_id}/followups', (200, 200, 404)),
    ('POST', '/api/students/{student_id}/followups', (201, 403, 404)),
    ('POST', '/api/ml/predict', (200, 403, 404)),
    ('GET', '/api/ml/predictions', (200, 403, 404)),
    ('GET', '/api/students/{student_id}/predictions', (200, 403, 404)),
]


@pytest.fixture
def matrix_data(actors):
    with database.SessionLocal() as db:
        career = Career(code='ISC', name='Sistemas')
        period = Period(code='PT07', name='Periodo base')
        subject = Subject(code='MAT', name='Matemáticas')
        own = Student(**student_data(), tutor_id=actors['tutor'][0], career=career)
        other = Student(**student_data('PT-A002'))
        db.add_all([career, period, subject, own, other])
        db.flush()
        enrollment = Enrollment(student_id=own.id, subject_id=subject.id, period_id=period.id,
                                term=period.code, grade=6.0)
        db.add(enrollment)
        db.flush()
        fields = {
            'user_id': actors['operador'][0], 'career_id': career.id, 'period_id': period.id,
            'subject_id': subject.id, 'student_id': own.id, 'enrollment_id': enrollment.id, 'kind': 'students',
        }
        other_id = other.id
        db.commit()
    return fields, other_id


def matrix_request(client, actors, matrix_data, real_features, role, method, path, status, unassigned=False):
    fields, other_id = matrix_data
    fields = {**fields, 'student_id': other_id} if unassigned else fields
    password = settings.admin_password if role in ('publico', 'admin') else PASSWORD
    email = settings.admin_email if role in ('publico', 'admin') else account_data(role)['email']
    bodies = {
        ('POST', '/api/auth/login'): {'email': email, 'password': password},
        ('POST', '/api/auth/change-password'): {'current_password': password, 'new_password': 'ClaveRenovada07'},
        ('POST', '/api/users'): {**account_data('tutor'), 'email': 'nuevo@pt.sipde.test'},
        ('PATCH', '/api/users/{user_id}'): {'active': False},
        ('POST', '/api/careers'): {'code': 'OTRA', 'name': 'Otra carrera'},
        ('PATCH', '/api/careers/{career_id}'): {'active': False},
        ('POST', '/api/periods'): {'code': 'PT07-2', 'name': 'Nuevo periodo'},
        ('PATCH', '/api/periods/{period_id}'): {'active': False},
        ('POST', '/api/subjects'): {'code': 'OTRA', 'name': 'Otra materia'},
        ('PATCH', '/api/subjects/{subject_id}'): {'active': False},
        ('POST', '/api/students'): student_data('PT-A003'),
        ('PATCH', '/api/students/{student_id}'): {'semester': 3},
        ('POST', '/api/students/{student_id}/deactivate'): {'status': 'baja_temporal'},
        ('PUT', '/api/students/{student_id}/tutor'): {'tutor_id': actors['tutor'][0]},
        ('POST', '/api/enrollments'): {'student_id': fields['student_id'], 'subject_id': fields['subject_id'],
                                     'term': 'PT07-2', 'grade': 6},
        ('PATCH', '/api/enrollments/{enrollment_id}'): {'grade': 8},
        ('POST', '/api/students/{student_id}/followups'): {'date': '2026-11-24', 'note': 'Seguimiento de prueba'},
        ('POST', '/api/ml/predict'): {'student_id': fields['student_id'], 'features': real_features},
    }
    csv_files = {
        '/api/import/students': 'enrollment_number,full_name,semester,program\nNUEVA,Ana,2,Sistemas\n',
        '/api/import/enrollments': 'enrollment_number,subject_code,term,grade\nPT-A001,MAT,PT07,7\n',
    }
    headers = {} if role == 'publico' else actors[role][1]
    kwargs = {}
    if path in csv_files:
        kwargs = {'files': {'file': ('prueba.csv', csv_files[path], 'text/csv')}, 'params': {'dry_run': 'true'}}
    if (method, path) == ('GET', '/api/ml/predictions') and unassigned:
        kwargs['params'] = {'student_id': other_id}
    if (method, path) in bodies:
        kwargs['json'] = bodies[method, path]
    response = client.request(method, path.format(**fields), headers=headers, **kwargs)
    assert response.status_code == status, response.text
    assert b'password_hash' not in response.content
    return response


def test_pt07_inventario_de_operaciones():
    """PT_07 · RN_04/RNF_01 · Comparar matriz y OpenAPI. Esperado: cada operación de /api tiene una sola fila en la matriz."""
    documented = [(method, path) for method, path, _ in MATRIX]
    published = {(method.upper(), path) for path, operations in app.openapi()['paths'].items()
                 if path.startswith('/api/') for method in operations}
    assert len(documented) == len(set(documented))
    assert set(documented) == published


@pytest.mark.parametrize(('method', 'path', 'role', 'status'), [
    pytest.param(method, path, role, status, id=f'{method}-{path}-{role}')
    for method, path, statuses in MATRIX
    for role, status in zip(ROLES, statuses, strict=True)
])
def test_pt07_matriz_api(api_client, actors, matrix_data, real_features, method, path, role, status):
    """PT_07 · RN_04/RNF_01 · Ejecutar cada operación como cada rol. Esperado: código de la matriz y ningún password_hash."""
    response = matrix_request(api_client, actors, matrix_data, real_features, role, method, path, status)
    if (method, path) == ('GET', '/api/students'):
        fields, other_id = matrix_data
        expected = [fields['student_id']] if role == 'tutor' else [other_id, fields['student_id']]
        assert [row['id'] for row in response.json()] == expected
        assert response.headers['X-Total-Count'] == str(len(expected))
    if path == '/api/dashboard':
        assert response.json()['students'] == (1 if role == 'tutor' else 2)


@pytest.mark.parametrize(('method', 'path', 'role', 'status'), [
    pytest.param(method, path, role, status, id=f'{method}-{path}-{role}')
    for method, path, statuses in UNASSIGNED
    for role, status in zip(ROLES, statuses, strict=True)
])
def test_pt07_matriz_alumno_ajeno(api_client, actors, matrix_data, real_features, method, path, role, status):
    """PT_07 · RN_04/RNF_01 · Acceder a un alumno ajeno a la tutoría. Esperado: 404 para tutor y el permiso de los otros roles."""
    matrix_request(api_client, actors, matrix_data, real_features, role, method, path, status, unassigned=True)


@pytest.mark.parametrize(('method', 'path'), PUBLIC)
def test_pt07_rutas_publicas(api_client, actors, matrix_data, real_features, method, path):
    """PT_07 · RN_04/RNF_01 · Usar las rutas públicas sin JWT. Esperado: 200 y ningún password_hash."""
    matrix_request(api_client, actors, matrix_data, real_features, 'publico', method, path, 200)


def test_pt07_ultimo_admin_no_se_desactiva(api_client, actors):
    """PT_07 · RN_04/RNF_01 · Desactivar al único administrador. Esperado: 409 y la cuenta permanece activa."""
    admin_id, headers = actors['admin']
    request_json(api_client, 'PATCH', f'/api/users/{admin_id}', 409, headers=headers, json={'active': False})
    current = request_json(api_client, 'GET', '/api/auth/me', 200, headers=headers)
    assert (current['id'], current['role'], current['active']) == (admin_id, 'admin', True)


def test_pt07_admin_no_retira_su_rol_si_hay_otro(api_client, actors):
    """PT_07 · RN_04/RNF_01 · Degradar la cuenta propia aunque exista otro administrador. Esperado: 409 y ambos roles intactos."""
    admin_id, headers = actors['admin']
    second = create(api_client, headers, 'users', **account_data('admin'))
    request_json(api_client, 'PATCH', f'/api/users/{admin_id}', 409, headers=headers, json={'role': 'operador'})
    accounts = request_json(api_client, 'GET', '/api/users', 200, headers=headers)
    assert {row['id'] for row in accounts if row['role'] == 'admin' and row['active']} == {admin_id, second['id']}
