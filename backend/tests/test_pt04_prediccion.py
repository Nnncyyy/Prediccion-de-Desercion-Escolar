"""Integración de inferencias con alumnos, tutorías e historial RN_03."""

import pytest
from sqlalchemy import select

from app import database
from app.models import PredictionLog
from helpers import actors, create, fixture_password_hash, request_json, student_data

PREDICT = '/api/ml/predict'
HISTORY = '/api/ml/predictions'


@pytest.fixture
def student_scope(api_client, actors):
    _, admin = actors['admin']
    tutor_id, _ = actors['tutor']
    own = create(api_client, admin, 'students', **student_data())
    other = create(api_client, admin, 'students', **student_data('PT-A002'))
    request_json(api_client, 'PUT', f'/api/students/{own["id"]}/tutor', 200,
                 headers=admin, json={'tutor_id': tutor_id})
    return own['id'], other['id']


def test_pt04_prediccion_y_alcance_de_historial(api_client, actors, student_scope, real_features, trained_model):
    """PT_04 · CU_04/RF_09 · Predecir con tutor y admin y consultar historiales. Esperado: BD_07 guarda la versión y filtra por asignación."""
    tutor_id, tutor = actors['tutor']
    _, admin = actors['admin']
    own_id, other_id = student_scope
    own = request_json(api_client, 'POST', PREDICT, 200, headers=tutor,
                       json={'student_id': own_id, 'features': real_features})
    other = request_json(api_client, 'POST', PREDICT, 200, headers=admin,
                         json={'student_id': other_id, 'features': real_features})
    without_student = request_json(api_client, 'POST', PREDICT, 200, headers=admin,
                                   json={'features': real_features})

    own_path = f'/api/students/{own_id}/predictions'
    per_student = request_json(api_client, 'GET', own_path, 200, headers=tutor)
    record, = per_student
    assert (record['id'], record['student_id'], record['user_id']) == (own['prediction_id'], own_id, tutor_id)
    assert record['model_version'] == own['modelo']['version'] == trained_model.artifact['version']
    assert per_student == request_json(api_client, 'GET', HISTORY, 200, headers=tutor)
    assert per_student == request_json(api_client, 'GET', HISTORY, 200, headers=admin, params={'student_id': own_id})
    global_history = request_json(api_client, 'GET', HISTORY, 200, headers=admin)
    assert [(row['id'], row['student_id']) for row in global_history] == [
        (without_student['prediction_id'], None), (other['prediction_id'], other_id), (own['prediction_id'], own_id),
    ]
    with database.SessionLocal() as db:
        saved = db.get(PredictionLog, own['prediction_id'])
        assert saved.model_version == trained_model.artifact['version']


@pytest.mark.parametrize('scenario', ['ajeno', 'inexistente', 'features-incompletas'])
def test_pt04_prediccion_rechazada_no_crea_historial(api_client, actors, student_scope, real_features, scenario):
    """PT_04 · CU_04/RF_09 · Rechazar alumno ajeno o ausente y variables incompletas. Esperado: 404 o 422 sin fila BD_07."""
    own_id, other_id = student_scope
    _, tutor = actors['tutor']
    _, admin = actors['admin']
    if scenario == 'features-incompletas':
        real_features.pop('Course')
        response = request_json(api_client, 'POST', PREDICT, 422, headers=tutor,
                                json={'student_id': own_id, 'features': real_features})
        assert [error['campo'] for error in response['detail']['errores']] == ['Course']
    else:
        student_id, headers = (other_id, tutor) if scenario == 'ajeno' else (999999, admin)
        assert request_json(api_client, 'POST', PREDICT, 404, headers=headers,
                            json={'student_id': student_id, 'features': real_features}) == {
            'detail': 'Estudiante no encontrado',
        }
    with database.SessionLocal() as db:
        assert db.scalar(select(PredictionLog.id)) is None
