"""INT_02 · Humo de RF_01–RF_05 y RF_09/RF_11 con los actores reales."""
from typing import Any

from fastapi.testclient import TestClient

from app.config import settings


def registrar_cuenta(cliente: TestClient, admin: dict, rol: str) -> tuple[int, dict]:
    datos = {'email': f'{rol}@sipde.test', 'password': 'Temporal123', 'full_name': 'Cuenta de prueba'}
    respuesta = cliente.post('/api/users', headers=admin, json={**datos, 'role': rol})
    assert respuesta.status_code == 201
    login = cliente.post('/api/auth/login', json={'email': datos['email'], 'password': datos['password']})
    assert login.status_code == 200
    return respuesta.json()['id'], {'Authorization': f'Bearer {login.json()["access_token"]}'}


def crear_alumno(cliente: TestClient, cabeceras: dict, matricula: str = 'INT02') -> int:
    datos = {'enrollment_number': matricula, 'full_name': 'Ana Pérez', 'program': 'Computación', 'semester': 1}
    respuesta = cliente.post('/api/students', headers=cabeceras, json=datos)
    assert respuesta.status_code == 201
    return respuesta.json()['id']


def test_login_y_cuenta(api_client: TestClient) -> None:
    """CU_01 / PT_01 · El token identifica al mismo usuario activo."""
    sesion = api_client.post('/api/auth/login', json={
        'email': settings.admin_email, 'password': settings.admin_password,
    })
    assert sesion.status_code == 200
    datos = sesion.json()
    cabeceras = {'Authorization': f'Bearer {datos["access_token"]}'}
    cuenta = api_client.get('/api/auth/me', headers=cabeceras)
    assert cuenta.status_code == 200
    assert cuenta.json()['active'] is True
    assert datos['user'] == {campo: cuenta.json()[campo] for campo in ('id', 'email', 'role', 'full_name')}
    assert datos['role'] == cuenta.json()['role'] == 'admin'
    assert api_client.get('/api/auth/me').status_code == 401


def test_roles_y_asignacion(api_client: TestClient, auth_headers: dict) -> None:
    """RN_04 / PT_02 · ACT_03 captura y ACT_02 solo consulta a sus tutorados."""
    tutor_id, tutor = registrar_cuenta(api_client, auth_headers, 'tutor')
    _, operador = registrar_cuenta(api_client, auth_headers, 'operador')
    alumno = crear_alumno(api_client, operador)
    ajeno = crear_alumno(api_client, operador, 'AJENO')
    ruta = f'/api/students/{alumno}'
    assert api_client.get(ruta, headers=tutor).status_code == 404
    asignacion = api_client.put(f'{ruta}/tutor', headers=auth_headers, json={'tutor_id': tutor_id})
    assert asignacion.status_code == 200
    assert api_client.get(ruta, headers=tutor).json()['tutor_id'] == tutor_id
    assert api_client.get(f'/api/students/{ajeno}', headers=tutor).status_code == 404
    visibles = api_client.get('/api/students', headers=tutor)
    assert [fila['id'] for fila in visibles.json()] == [alumno]
    assert visibles.headers['X-Total-Count'] == '1'
    assert api_client.get('/api/dashboard', headers=tutor).json()['students'] == 1
    rechazo = api_client.post(f'{ruta}/deactivate', headers=operador)
    assert rechazo.status_code == 403
    assert rechazo.json()['detail'] == 'No tiene permiso para esta acción'


def test_baja_y_reactivacion(api_client: TestClient, auth_headers: dict) -> None:
    """RF_03 · La baja es lógica y el alumno sigue visible sin filtros."""
    alumno = crear_alumno(api_client, auth_headers)
    ruta = f'/api/students/{alumno}'
    baja = api_client.post(f'{ruta}/deactivate', headers=auth_headers)
    assert baja.status_code == 200
    assert (baja.json()['active'], baja.json()['status']) == (False, 'baja_temporal')
    assert api_client.get('/api/students', headers=auth_headers).json()[0]['id'] == alumno
    alta = api_client.post(f'{ruta}/reactivate', headers=auth_headers)
    assert alta.status_code == 200
    assert (alta.json()['active'], alta.json()['status']) == (True, 'activo')


def test_periodo_automatico(api_client: TestClient, auth_headers: dict) -> None:
    """RF_05 / CU_03 · Captura por term y lectura de catálogo en la misma transacción."""
    alumno = crear_alumno(api_client, auth_headers)
    materia = api_client.post('/api/subjects', headers=auth_headers, json={'code': 'MAT', 'name': 'Cálculo'})
    assert materia.status_code == 201
    datos = {'student_id': alumno, 'subject_id': materia.json()['id'], 'term': '2026-2', 'grade': 6}
    respuesta = api_client.post('/api/enrollments', headers=auth_headers, json=datos)
    assert respuesta.status_code == 201
    periodo, = api_client.get('/api/periods', headers=auth_headers).json()
    assert periodo['active'] is True
    assert respuesta.json()['period_id'] == periodo['id']
    assert respuesta.json()['term'] == respuesta.json()['period_code'] == periodo['code'] == '2026-2'
    assert respuesta.json()['subject_name'] == 'Cálculo'
    assert api_client.post('/api/enrollments', headers=auth_headers, json=datos).status_code == 409


def test_prediccion_persistida(api_client: TestClient, auth_headers: dict, real_features: dict,
                              trained_model: Any) -> None:
    """RN_03 / PT_07 · El historial y la bitácora identifican la inferencia emitida."""
    alumno = crear_alumno(api_client, auth_headers)
    datos = {'student_id': alumno, 'features': real_features}
    respuesta = api_client.post('/api/ml/predict', headers=auth_headers, json=datos)
    assert respuesta.status_code == 200
    resultado = respuesta.json()
    registro, = api_client.get(f'/api/students/{alumno}/predictions', headers=auth_headers).json()
    assert registro['id'] == resultado['prediction_id']
    assert registro['features'] == real_features
    assert registro['model_version'] == trained_model.artifact['version']
    assert registro['predicted_class'] == resultado['clase_predicha']
    assert registro['probability_dropout'] == resultado['probabilidades']['Dropout']
    assert registro['risk_category'] == resultado['categoria_orientativa']
    assert registro['task'] == resultado['modelo']['task']
    eventos = api_client.get('/api/audit?entity=prediction_logs', headers=auth_headers).json()
    assert [(e['action'], e['entity_id'], e['user_id']) for e in eventos] == [
        ('predecir', registro['id'], registro['user_id']),
    ]
