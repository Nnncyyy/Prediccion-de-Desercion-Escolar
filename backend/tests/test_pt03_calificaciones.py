"""Pruebas de validación, conflictos y ciclo de inscripciones."""

import pytest

from helpers import create, request_json, student_data

ENROLLMENTS = '/api/enrollments'


@pytest.fixture
def enrollment_data(api_client, auth_headers):
    student = create(api_client, auth_headers, 'students', **student_data())
    subject = create(api_client, auth_headers, 'subjects', code='MAT', name='Matemáticas')
    period = create(api_client, auth_headers, 'periods', code='PT03-1', name='Periodo de prueba')
    return {'student_id': student['id'], 'subject_id': subject['id'], 'period_id': period['id'], 'grade': 6.0}


@pytest.mark.parametrize('grade', [-0.01, 10.01, 'seis'], ids=['menor-0', 'mayor-10', 'no-numerico'])
def test_pt03_nota_invalida(api_client, auth_headers, enrollment_data, grade):
    """PT_03 · CU_03/RF_05 · Enviar una nota inválida al alta y al editar. Esperado: 422 en grade y ningún cambio."""
    invalid = {**enrollment_data, 'grade': grade}
    created = request_json(api_client, 'POST', ENROLLMENTS, 422, headers=auth_headers, json=invalid)
    assert [entry['loc'] for entry in created['detail']] == [['body', 'grade']]
    student_id = enrollment_data['student_id']
    path = f'/api/students/{student_id}/enrollments'
    assert request_json(api_client, 'GET', path, 200, headers=auth_headers) == []
    valid = create(api_client, auth_headers, 'enrollments', **enrollment_data)
    patched = request_json(api_client, 'PATCH', f'{ENROLLMENTS}/{valid["id"]}', 422,
                           headers=auth_headers, json={'grade': grade})
    assert [entry['loc'] for entry in patched['detail']] == [['body', 'grade']]
    assert request_json(api_client, 'GET', path, 200, headers=auth_headers) == [valid]


@pytest.mark.parametrize(('field', 'detail'), [
    ('student_id', 'Estudiante no encontrado'),
    ('subject_id', 'Materia no encontrada'),
    ('period_id', 'Periodo no encontrado'),
])
def test_pt03_referencia_ausente(api_client, auth_headers, enrollment_data, field, detail):
    """PT_03 · CU_03/RF_05 · Inscribir con una referencia inexistente. Esperado: 404 de la entidad correspondiente."""
    result = request_json(api_client, 'POST', ENROLLMENTS, 404, headers=auth_headers,
                          json={**enrollment_data, field: 999999})
    assert result == {'detail': detail}


def test_pt03_no_inscribe_alumno_inactivo(api_client, auth_headers, enrollment_data):
    """PT_03 · CU_03/RF_05 · Intentar inscribir a un alumno dado de baja. Esperado: 409 y ninguna inscripción."""
    student_path = f'/api/students/{enrollment_data["student_id"]}'
    request_json(api_client, 'POST', f'{student_path}/deactivate', 200, headers=auth_headers)
    assert request_json(api_client, 'POST', ENROLLMENTS, 409, headers=auth_headers,
                        json=enrollment_data) == {'detail': 'El estudiante está inactivo'}
    assert request_json(api_client, 'GET', f'{student_path}/enrollments', 200, headers=auth_headers) == []


def test_pt03_ciclo_de_nota(api_client, auth_headers, enrollment_data):
    """PT_03 · CU_03/RF_05 · Capturar 6.0, editar, retirar la nota y borrar. Esperado: aprobada, cambios persistentes y DELETE 204."""
    created = create(api_client, auth_headers, 'enrollments', **enrollment_data)
    assert created['grade'] == 6.0
    student_path = f'/api/students/{created["student_id"]}'
    assert request_json(api_client, 'GET', f'{student_path}/alert', 200,
                        headers=auth_headers)['failed_subjects'] == 0
    path = f'{ENROLLMENTS}/{created["id"]}'
    for grade in (8.5, None):
        updated = request_json(api_client, 'PATCH', path, 200, headers=auth_headers, json={'grade': grade})
        assert updated == {**created, 'grade': grade, 'updated_at': updated['updated_at']}
        assert request_json(api_client, 'GET', f'{student_path}/enrollments', 200,
                            headers=auth_headers) == [updated]
    response = api_client.delete(path, headers=auth_headers)
    assert response.status_code == 204, response.text
    assert response.content == b''
    assert request_json(api_client, 'GET', f'{student_path}/enrollments', 200, headers=auth_headers) == []
    request_json(api_client, 'DELETE', path, 404, headers=auth_headers)


def test_pt03_periodo_automatico_reutilizado(api_client, auth_headers, enrollment_data):
    """PT_03 · CU_03/RF_05 · Reusar un periodo automático por código y por ID. Esperado: un único periodo y 409 para la misma terna."""
    by_term = {key: value for key, value in enrollment_data.items() if key != 'period_id'}
    term = 'PT03-AUTO'
    original = create(api_client, auth_headers, 'enrollments', **by_term, term=term)
    another = create(api_client, auth_headers, 'subjects', code='HIS', name='Historia')
    second = create(api_client, auth_headers, 'enrollments', **{**by_term, 'subject_id': another['id']}, term=term)
    assert original['period_id'] == second['period_id']
    assert original['term'] == second['period_code'] == term
    periods = request_json(api_client, 'GET', '/api/periods', 200, headers=auth_headers)
    assert [row['id'] for row in periods if row['code'] == term] == [original['period_id']]
    assert request_json(api_client, 'POST', ENROLLMENTS, 409, headers=auth_headers,
                        json={**by_term, 'period_id': original['period_id']}) == {
        'detail': 'Inscripción ya registrada para el periodo',
    }
