"""Pruebas de expedientes, filtros, paginación y tutorías."""

from datetime import datetime

import pytest

from helpers import actors, create, fixture_password_hash, request_json, student_data

STUDENTS = '/api/students'


@pytest.mark.parametrize('program', ['', 'Plan personalizado'], ids=['copia-carrera', 'programa-explicito'])
def test_pt02_alta_con_todos_los_campos(api_client, auth_headers, program):
    """PT_02 · CU_02/RF_03 · Crear un expediente completo. Esperado: 201, estado inicial y programa explícito o copiado."""
    career = create(api_client, auth_headers, 'careers', code='ISC', name='Ingeniería en Sistemas')
    data = student_data(program=program, career_id=career['id'], semester=4, employed=True, work_hours_weekly=32)
    student = create(api_client, auth_headers, 'students', **data)
    expected = {**data, 'program': program or career['name'], 'career_name': career['name'],
                'active': True, 'status': 'activo', 'tutor_id': None}
    assert {key: student[key] for key in expected} == expected
    assert student['id'] > 0
    for key in ('created_at', 'updated_at'):
        assert datetime.fromisoformat(student[key]).tzinfo is not None


def test_pt02_matricula_duplicada_alta(api_client, auth_headers):
    """PT_02 · CU_02/RF_03 · Reutilizar la matrícula en otro alta. Esperado: 409 y un solo expediente."""
    first = create(api_client, auth_headers, 'students', **student_data())
    assert request_json(api_client, 'POST', STUDENTS, 409, headers=auth_headers,
                        json=student_data(full_name='Otra persona')) == {'detail': 'Matrícula duplicada'}
    assert request_json(api_client, 'GET', STUDENTS, 200, headers=auth_headers) == [first]


def test_pt02_edicion_parcial(api_client, auth_headers):
    """PT_02 · CU_02/RF_03 · Actualizar solo los datos laborales. Esperado: 200, demás campos conservados y cambios persistidos."""
    student = create(api_client, auth_headers, 'students', **student_data())
    path = f'{STUDENTS}/{student["id"]}'
    changes = {'employed': True, 'work_hours_weekly': 28}
    edited = request_json(api_client, 'PATCH', path, 200, headers=auth_headers, json=changes)
    assert edited == {**student, **changes, 'updated_at': edited['updated_at']}
    assert edited == request_json(api_client, 'GET', path, 200, headers=auth_headers)


def test_pt02_matricula_duplicada_edicion(api_client, auth_headers):
    """PT_02 · CU_02/RF_03 · Cambiar la matrícula a una ocupada. Esperado: 409 y edición revertida."""
    first = create(api_client, auth_headers, 'students', **student_data())
    second = create(api_client, auth_headers, 'students', **student_data('PT-A002'))
    path = f'{STUDENTS}/{second["id"]}'
    request_json(api_client, 'PATCH', path, 409, headers=auth_headers,
                 json={'enrollment_number': first['enrollment_number'], 'semester': 5})
    assert request_json(api_client, 'GET', path, 200, headers=auth_headers) == second


@pytest.fixture
def search_students(api_client, auth_headers):
    systems = create(api_client, auth_headers, 'careers', code='ISC', name='Sistemas')
    design = create(api_client, auth_headers, 'careers', code='DIS', name='Diseño')
    rows = {}
    for key, data in {
        'accent': student_data('ÁB%01', full_name='Ángela García', career_id=systems['id']),
        'plain': student_data('ABX01', full_name='Angela Garcia', career_id=systems['id']),
        'other': student_data('OTRO', full_name='María Pérez', career_id=design['id']),
        'inactive': student_data('BAJA', full_name='Luis López', career_id=systems['id']),
    }.items():
        rows[key] = create(api_client, auth_headers, 'students', **data)
    request_json(api_client, 'POST', f'{STUDENTS}/{rows["inactive"]["id"]}/deactivate', 200,
                 headers=auth_headers, json={'status': 'baja_definitiva'})
    return systems['id'], rows


@pytest.mark.parametrize(('query', 'matches'), [
    ('ÁNGELA', ['accent']), ('garcía', ['accent']), ('GARCIA', ['plain']),
    ('áb%', ['accent']), ('abx01', ['plain']), ('%', ['accent']), ('_', []),
])
def test_pt02_busqueda_literal(api_client, auth_headers, search_students, query, matches):
    """PT_02 · CU_02/RF_03 · Buscar por nombre o matrícula en SQLite. Esperado: sin distinguir mayúsculas, conservando tildes y comodines literales."""
    _, rows = search_students
    response = api_client.get(STUDENTS, headers=auth_headers, params={'q': query})
    assert response.status_code == 200, response.text
    assert [student['id'] for student in response.json()] == [rows[key]['id'] for key in matches]
    assert response.headers['X-Total-Count'] == str(len(matches))


@pytest.mark.parametrize(('filters', 'matches'), [
    ({'career': True}, ['inactive', 'plain', 'accent']),
    ({'status': 'activo'}, ['other', 'plain', 'accent']),
    ({'active': False}, ['inactive']),
    ({'career': True, 'status': 'activo', 'active': True, 'skip': 1, 'limit': 1}, ['plain', 'accent']),
    ({'career': True, 'skip': 3, 'limit': 1}, ['inactive', 'plain', 'accent']),
])
def test_pt02_filtros_y_paginacion(api_client, auth_headers, search_students, filters, matches):
    """PT_02 · CU_02/RF_03 · Filtrar y paginar expedientes. Esperado: orden por ID descendente y X-Total-Count previo a paginar."""
    career_id, rows = search_students
    params = filters.copy()
    if params.pop('career', False):
        params['career_id'] = career_id
    response = api_client.get(STUDENTS, headers=auth_headers, params=params)
    assert response.status_code == 200, response.text
    skip, limit = params.get('skip', 0), params.get('limit', 100)
    assert [row['id'] for row in response.json()] == [rows[key]['id'] for key in matches[skip:skip + limit]]
    assert response.headers['X-Total-Count'] == str(len(matches))


@pytest.mark.parametrize('status', ['baja_definitiva', 'egresado'])
def test_pt02_baja_explicita(api_client, auth_headers, status):
    """PT_02 · CU_02/RF_03 · Inactivar con un estado explícito y reactivar. Esperado: estado y flags correctos con motivo en bitácora."""
    student = create(api_client, auth_headers, 'students', **student_data())
    path = f'{STUDENTS}/{student["id"]}'
    data = {'status': status, 'reason': 'Solicitud de prueba'}
    inactive = request_json(api_client, 'POST', f'{path}/deactivate', 200, headers=auth_headers, json=data)
    assert (inactive['status'], inactive['active']) == (status, False)
    active = request_json(api_client, 'POST', f'{path}/reactivate', 200, headers=auth_headers)
    assert (active['status'], active['active']) == ('activo', True)
    assert request_json(api_client, 'GET', path, 200, headers=auth_headers) == active
    audit = request_json(api_client, 'GET', '/api/audit', 200, headers=auth_headers, params={'entity': 'students'})
    assert [(event['action'], event['entity_id']) for event in audit] == [
        ('reactivar', student['id']), ('baja', student['id']), ('crear', student['id']),
    ]
    assert audit[1]['detail'] == data


def test_pt02_retirar_tutor(api_client, actors):
    """PT_02 · CU_02/RF_03 · Asignar y retirar un tutor. Esperado: tutor_id persiste y el tutor pierde acceso al retirarlo."""
    _, admin = actors['admin']
    tutor_id, tutor = actors['tutor']
    student = create(api_client, admin, 'students', **student_data())
    path = f'{STUDENTS}/{student["id"]}'
    assert request_json(api_client, 'PUT', f'{path}/tutor', 200,
                        headers=admin, json={'tutor_id': tutor_id})['tutor_id'] == tutor_id
    request_json(api_client, 'GET', path, 200, headers=tutor)
    assert request_json(api_client, 'PUT', f'{path}/tutor', 200,
                        headers=admin, json={'tutor_id': None})['tutor_id'] is None
    assert request_json(api_client, 'GET', path, 200, headers=admin)['tutor_id'] is None
    request_json(api_client, 'GET', path, 404, headers=tutor)


def test_pt02_asignar_cuenta_que_no_es_tutor(api_client, actors):
    """PT_02 · CU_02/RF_03 · Intentar asignar un operador como tutor. Esperado: 422 y expediente sin asignación."""
    _, admin = actors['admin']
    operator_id, _ = actors['operador']
    student = create(api_client, admin, 'students', **student_data())
    path = f'{STUDENTS}/{student["id"]}'
    assert request_json(api_client, 'PUT', f'{path}/tutor', 422,
                        headers=admin, json={'tutor_id': operator_id}) == {'detail': 'Se requiere un tutor activo'}
    assert request_json(api_client, 'GET', path, 200, headers=admin)['tutor_id'] is None
