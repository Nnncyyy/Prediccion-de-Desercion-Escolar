"""PT_07 / PT_03 / PT_05 · Integración HTTP de RF_07 y RF_13."""
import csv
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path

import pytest

from app import database
from app.models import PredictionLog

DATA = Path(__file__).parent / 'data'
STUDENTS = '/api/import/students'
ENROLLMENTS = '/api/import/enrollments'
SUMMARY = '/api/reports/summary'
REPORT = '/api/reports/students'
HISTORY = '/api/reports/predictions.csv'
STUDENT_COLUMNS = [
    'enrollment_number', 'full_name', 'career', 'semester', 'status', 'employed', 'work_hours_weekly',
    'average_grade', 'failed_subjects', 'alert_level', 'probability_dropout', 'risk_category', 'prediction_at',
]


def upload(client, headers, path, content, **params):
    return client.post(path, headers=headers, params=params, files={'file': ('datos.csv', content, 'text/csv')})


def create(client, headers, path, **data):
    response = client.post(f'/api/{path}', headers=headers, json=data)
    assert response.status_code == 201, response.text
    return response.json()


def account(client, headers, role, email):
    password = 'Clave_segura_123'
    user = create(client, headers, 'users', email=email, full_name='Cuenta de prueba', role=role, password=password)
    login = client.post('/api/auth/login', json={'email': email, 'password': password})
    assert login.status_code == 200, login.text
    return user, {'Authorization': f'Bearer {login.json()["access_token"]}'}


def stored_students(client, headers):
    response = client.get('/api/students', headers=headers)
    assert response.status_code == 200, response.text
    return {row['enrollment_number']: row for row in response.json()}


def read_csv(response):
    assert response.status_code == 200, response.text
    assert response.headers['content-type'].startswith('text/csv')
    assert response.headers['content-disposition'].startswith('attachment;')
    return csv.DictReader(StringIO(response.content.decode('utf-8-sig'), newline=''))


def test_importa_y_actualiza_alumnos_con_bitacora(api_client, auth_headers):
    """PT_07 · RF_07 / RNF_05. Confirma altas y actualizaciones sin duplicados."""
    content = (DATA / 'students.csv').read_bytes()
    response = upload(api_client, auth_headers, STUDENTS, content)
    assert response.status_code == 200, response.text
    assert response.json() == {
        'dry_run': False, 'applied': True, 'total_rows': 2, 'created': 2, 'updated': 0, 'errors': [],
    }
    reimport = upload(api_client, auth_headers, STUDENTS, content.replace(b',2,Sistemas', b',3,Sistemas'))
    assert reimport.json() == {**response.json(), 'created': 0, 'updated': 2}
    students = stored_students(api_client, auth_headers)
    assert len(students) == 2
    assert students['A001']['semester'] == 3
    assert students['A002']['employed'] is True
    audit = api_client.get('/api/audit', headers=auth_headers, params={'entity': 'students'}).json()
    assert [event['action'] for event in audit] == ['importar', 'importar']
    assert audit[0]['detail'] == reimport.json()


def test_dry_run_no_guarda_ni_modifica(api_client, auth_headers):
    """PT_07 · RF_07 / RNF_03. La simulación conserva expedientes y bitácora."""
    student = create(api_client, auth_headers, 'students',
                     enrollment_number='A001', full_name='Ana García', semester=1, program='Sistemas')
    response = upload(api_client, auth_headers, STUDENTS, (DATA / 'students.csv').read_bytes(), dry_run='true')
    assert response.status_code == 200, response.text
    assert response.json() == {
        'dry_run': True, 'applied': False, 'total_rows': 2, 'created': 1, 'updated': 1, 'errors': [],
    }
    assert stored_students(api_client, auth_headers) == {'A001': student}
    audit = api_client.get('/api/audit', headers=auth_headers, params={'entity': 'students'}).json()
    assert [event['action'] for event in audit] == ['crear']


def test_fila_invalida_revierte_lote(api_client, auth_headers):
    """PT_07 · RF_07 / RNF_03. Identifica la línea de la fila rechazada."""
    response = upload(api_client, auth_headers, STUDENTS, (DATA / 'students-invalid.csv').read_bytes())
    assert response.status_code == 200, response.text
    result = response.json()
    assert result['applied'] is False
    assert result['total_rows'] == 2
    assert result['created'] == 1
    assert [(error['row'], error['field']) for error in result['errors']] == [(3, 'semester')]
    assert stored_students(api_client, auth_headers) == {}


def test_columnas_faltantes(api_client, auth_headers):
    """PT_07 · RF_07. Enumera las columnas obligatorias faltantes."""
    response = upload(api_client, auth_headers, STUDENTS, 'enrollment_number\nA001\n')
    assert response.status_code == 422
    assert response.json()['detail']['missing_columns'] == ['full_name', 'semester']


def test_bom_y_punto_y_coma(api_client, auth_headers):
    """PT_07 · RF_07. Lee BOM, encabezados normalizados y nombres entrecomillados."""
    content = '\ufeff Enrollment_Number ; FULL_NAME ; semester ; program ; employed\r\nA001;"García; Ana";2;Sistemas;SÍ\r\n'
    response = upload(api_client, auth_headers, STUDENTS, content.encode('utf-8'))
    assert response.status_code == 200, response.text
    assert response.json()['created'] == 1
    student = stored_students(api_client, auth_headers)['A001']
    assert student['full_name'] == 'García; Ana'
    assert student['employed'] is True


def test_linea_fisica_despues_de_campo_multilinea(api_client, auth_headers):
    """PT_07 · RF_07. Cuenta saltos dentro de campos y conserva la línea del error."""
    content = (
        'enrollment_number;full_name;semester;program\r'
        'A001;"Ana\rGarcía";2;Sistemas\r'
        '\r'
        'A002;Luis Pérez;0;Sistemas\r'
    )
    response = upload(api_client, auth_headers, STUDENTS, content)
    assert response.status_code == 200, response.text
    result = response.json()
    assert (result['total_rows'], result['created'], result['applied']) == (2, 1, False)
    assert [(error['row'], error['field']) for error in result['errors']] == [(5, 'semester')]


@pytest.mark.parametrize('size, rows', [(2 * 1024 * 1024 + 1, 0), (0, 5001)])
def test_limites_csv(api_client, auth_headers, size, rows):
    """PT_07 · RF_07. Rechaza el exceso de bytes o filas con 413."""
    content = b'x' * size if size else b'enrollment_number,full_name,semester,program\n' + b'A001,Ana,2,Sistemas\n' * rows
    assert upload(api_client, auth_headers, STUDENTS, content).status_code == 413
    assert stored_students(api_client, auth_headers) == {}


def test_importa_carrera_tutor_y_estatus(api_client, auth_headers):
    """PT_07 · RF_07. Resuelve catálogos, asigna tutor y sincroniza la baja."""
    career = create(api_client, auth_headers, 'careers', code='SIS', name='Sistemas')
    tutor, tutor_headers = account(api_client, auth_headers, 'tutor', 'tutora@example.test')
    content = (
        'enrollment_number,full_name,semester,career_code,tutor_email,status\n'
        'A001,Ana García,2,SIS,tutora@example.test,baja_temporal\n'
    )
    response = upload(api_client, auth_headers, STUDENTS, content)
    assert response.json()['applied'] is True
    student = stored_students(api_client, auth_headers)['A001']
    assert (student['career_id'], student['program'], student['tutor_id']) == (career['id'], 'Sistemas', tutor['id'])
    assert (student['status'], student['active']) == ('baja_temporal', False)
    assert upload(api_client, tutor_headers, STUDENTS, content).status_code == 403
    assert api_client.get('/api/import/templates/students', headers=tutor_headers).status_code == 403
    minimal = 'enrollment_number,full_name,semester\nA001,Ana García,3\n'
    assert upload(api_client, auth_headers, STUDENTS, minimal).json()['updated'] == 1
    assert stored_students(api_client, auth_headers)['A001']['tutor_id'] == tutor['id']


def test_importa_inscripciones_y_actualiza_nota(api_client, auth_headers):
    """PT_07 / PT_03 · RF_07. Crea el periodo y actualiza calificaciones en el mismo registro."""
    upload(api_client, auth_headers, STUDENTS, (DATA / 'students.csv').read_bytes())
    create(api_client, auth_headers, 'subjects', code='MAT', name='Matemáticas')
    content = (DATA / 'enrollments.csv').read_bytes()
    sim = upload(api_client, auth_headers, ENROLLMENTS, content, dry_run='true')
    assert sim.json()['created'] == 2 and not sim.json()['applied']
    assert api_client.get('/api/periods', headers=auth_headers).json() == []
    load = upload(api_client, auth_headers, ENROLLMENTS, content)
    assert load.json()['created'] == 2 and load.json()['applied']
    original = api_client.get('/api/periods', headers=auth_headers).json()
    assert original[0]['code'] == '2027-1'
    reload = upload(api_client, auth_headers, ENROLLMENTS, content.replace(b'5.5', b'9.5'))
    assert reload.json()['updated'] == 2 and reload.json()['applied']
    assert api_client.get('/api/periods', headers=auth_headers).json() == original
    student = stored_students(api_client, auth_headers)['A001']
    enrollments = api_client.get(f'/api/students/{student["id"]}/enrollments', headers=auth_headers).json()
    assert len(enrollments) == 1
    assert enrollments[0]['grade'] == 9.5


def test_materia_inexistente_revierte_periodo_e_inscripciones(api_client, auth_headers):
    """PT_07 / PT_03 · RF_07 / RNF_03. Una materia ausente invalida el lote."""
    upload(api_client, auth_headers, STUDENTS, (DATA / 'students.csv').read_bytes())
    create(api_client, auth_headers, 'subjects', code='MAT', name='Matemáticas')
    content = (DATA / 'enrollments.csv').read_bytes().replace(b'A002,MAT,', b'A002,XXX,')
    response = upload(api_client, auth_headers, ENROLLMENTS, content)
    assert response.status_code == 200, response.text
    assert response.json() == {
        'dry_run': False, 'applied': False, 'total_rows': 2, 'created': 1, 'updated': 0,
        'errors': [{'row': 3, 'field': 'subject_code', 'message': 'Materia no encontrada'}],
    }
    assert api_client.get('/api/periods', headers=auth_headers).json() == []
    student = stored_students(api_client, auth_headers)['A001']
    assert api_client.get(f'/api/students/{student["id"]}/enrollments', headers=auth_headers).json() == []


@pytest.mark.parametrize('kind', ['students', 'enrollments'])
def test_plantilla_descargable(api_client, auth_headers, kind):
    """PT_07 · RF_07. Ofrece encabezados y dos filas en una descarga CSV."""
    response = api_client.get(f'/api/import/templates/{kind}', headers=auth_headers)
    rows = read_csv(response)
    assert f'plantilla-{kind}.csv' in response.headers['content-disposition']
    assert rows.fieldnames == {
        'students': ['enrollment_number', 'full_name', 'semester', 'career_code', 'program',
                     'employed', 'work_hours_weekly', 'status', 'tutor_email'],
        'enrollments': ['enrollment_number', 'subject_code', 'term', 'grade'],
    }[kind]
    assert len(list(rows)) == 2


@pytest.fixture
def report_data(api_client, auth_headers):
    tutor, tutor_headers = account(api_client, auth_headers, 'tutor', 'tutor@example.test')
    career = create(api_client, auth_headers, 'careers', code='SIS', name='Sistemas')
    upload(api_client, auth_headers, STUDENTS, (DATA / 'students.csv').read_bytes())
    students = stored_students(api_client, auth_headers)
    ana, luis = students['A001'], students['A002']
    assert api_client.put(f'/api/students/{ana["id"]}/tutor', headers=auth_headers,
                          json={'tutor_id': tutor['id']}).status_code == 200
    assert api_client.patch(f'/api/students/{ana["id"]}', headers=auth_headers,
                            json={'career_id': career['id']}).status_code == 200
    create(api_client, auth_headers, 'subjects', code='MAT', name='Matemáticas')
    other = create(api_client, auth_headers, 'subjects', code='HIS', name='Historia')
    upload(api_client, auth_headers, ENROLLMENTS, (DATA / 'enrollments.csv').read_bytes())
    create(api_client, auth_headers, 'enrollments',
           student_id=ana['id'], subject_id=other['id'], term='2027-1', grade=5)
    create(api_client, auth_headers, 'enrollments', student_id=ana['id'], subject_id=other['id'], term='2027-2')
    create(api_client, auth_headers, 'enrollments',
           student_id=luis['id'], subject_id=other['id'], term='2027-2', grade=6)
    with database.SessionLocal() as db:
        for student, category, probability, day in [
            (ana, 'media', 0.4, 1), (ana, 'alta', 0.8, 2), (ana, 'alta', 0.9, 2), (luis, 'baja', 0.1, 2),
        ]:
            db.add(PredictionLog(
                student_id=student['id'], user_id=tutor['id'], model_version='1.0', task='binaria',
                predicted_class='Dropout', risk_category=category, probability_dropout=probability,
                features={'variable': 1}, created_at=datetime(2027, 1, day, 18, tzinfo=timezone.utc),
            ))
        db.commit()
    return {'tutor_headers': tutor_headers, 'career': career, 'ana': ana, 'luis': luis}


def test_resumen_con_datos_y_filtros(api_client, auth_headers, report_data):
    """PT_05 · RF_13. Usa solo notas evaluadas y aplica carrera y código de periodo."""
    response = api_client.get(SUMMARY, headers=auth_headers, params={'period': '2027-1'})
    assert response.status_code == 200, response.text
    data = response.json()
    assert data['students'] == data['active_students'] == data['students_by_status']['activo'] == 2
    assert data['evaluated_enrollments'] == data['failure_rate_denominator'] == 3
    assert data['failed_enrollments'] == 2
    assert data['average_grade'] == 6.33
    assert data['failure_rate'] == 66.67
    assert data['alerts_by_level'] == {'baja': 1, 'media': 0, 'alta': 1, 'sin_datos': 0}
    assert data['predictions_by_category'] == {'baja': 1, 'media': 1, 'alta': 2}
    assert data['average_probability_dropout'] == pytest.approx(0.55)
    assert data['by_career'] == [
        {'career': 'Sistemas', 'students': 2, 'average_grade': 6.33, 'failure_rate': 66.67, 'alerts_alta': 1},
    ]
    filtered = api_client.get(SUMMARY, headers=auth_headers,
                              params={'career_id': report_data['career']['id'], 'period': '2027-2'}).json()
    assert filtered['students'] == 1
    assert filtered['failure_rate_denominator'] == filtered['average_grade'] == 0
    assert filtered['alerts_by_level']['sin_datos'] == 1
    assert filtered['predictions'] == 3
    next_period = api_client.get(SUMMARY, headers=auth_headers, params={'period': '2027-2'}).json()
    assert next_period['average_grade'] == 6
    assert next_period['failure_rate'] == 0


def test_reportes_vacios(api_client, auth_headers):
    """PT_05 · RF_13. Entrega ceros y listas vacías sin expedientes."""
    response = api_client.get(SUMMARY, headers=auth_headers)
    assert response.status_code == 200, response.text
    data = response.json()
    for field in ('students', 'active_students', 'average_grade', 'failure_rate', 'failure_rate_denominator',
                  'evaluated_enrollments', 'average_probability_dropout', 'predictions'):
        assert data[field] == 0
    assert data['by_career'] == []
    assert api_client.get(REPORT, headers=auth_headers).json() == []
    assert list(read_csv(api_client.get(HISTORY, headers=auth_headers))) == []


def test_csv_bom_y_filtro_alerta(api_client, auth_headers, report_data):
    """PT_05 · RF_13. Comparte filtros entre JSON y CSV y usa la predicción más reciente."""
    params = {'alert_level': 'alta', 'career_id': report_data['career']['id'], 'status': 'activo'}
    response = api_client.get(f'{REPORT}.csv', headers=auth_headers, params=params)
    assert response.content.startswith(b'\xef\xbb\xbf')
    rows = read_csv(response)
    assert rows.fieldnames == STUDENT_COLUMNS
    csv_data = list(rows)
    assert [row['enrollment_number'] for row in csv_data] == ['A001']
    assert csv_data[0]['full_name'] == 'Ana García'
    json_data = api_client.get(REPORT, headers=auth_headers, params=params).json()
    assert [row['enrollment_number'] for row in json_data] == ['A001']
    assert json_data[0]['alert_level'] == 'alta'
    assert json_data[0]['probability_dropout'] == 0.9
    assert json_data[0]['risk_category'] == 'alta'
    assert api_client.get(REPORT, headers=auth_headers, params={**params, 'status': 'egresado'}).json() == []


def test_tutor_solo_ve_alumnos_asignados(api_client, auth_headers, report_data):
    """PT_05 · RF_13 / RN_04. Todos los reportes respetan las asignaciones vigentes."""
    headers = report_data['tutor_headers']
    summary = api_client.get(SUMMARY, headers=headers).json()
    assert summary['students'] == 1
    assert summary['evaluated_enrollments'] == 2
    assert summary['predictions'] == 3
    students = api_client.get(REPORT, headers=headers).json()
    assert [row['enrollment_number'] for row in students] == ['A001']
    assert len(list(read_csv(api_client.get(f'{REPORT}.csv', headers=headers)))) == 1
    rows = list(read_csv(api_client.get(HISTORY, headers=headers)))
    assert len(rows) == 3
    assert {int(row['student_id']) for row in rows} == {report_data['ana']['id']}
    excluded = api_client.get(HISTORY, headers=headers, params={'student_id': report_data['luis']['id']})
    assert list(read_csv(excluded)) == []


def test_historial_csv_filtra_fechas_y_omite_features(api_client, auth_headers, report_data):
    """PT_05 · RF_13. Respeta las fechas UTC inclusivas y ordena empates por ID."""
    params = {'student_id': report_data['ana']['id'], 'from': '2027-01-02', 'to': '2027-01-02'}
    rows = read_csv(api_client.get(HISTORY, headers=auth_headers, params=params))
    assert 'features' not in rows.fieldnames
    assert [float(row['probability_dropout']) for row in rows] == [0.9, 0.8]
    midnight = {**params, 'to': '2027-01-02T00:00:00Z'}
    assert list(read_csv(api_client.get(HISTORY, headers=auth_headers, params=midnight))) == []
    offset = {**params, 'from': '2027-01-02T12:00:00-06:00', 'to': '2027-01-02T18:00:00Z'}
    assert len(list(read_csv(api_client.get(HISTORY, headers=auth_headers, params=offset)))) == 2
    assert api_client.get(HISTORY, headers=auth_headers, params={**params, 'to': '2027-01-01'}).status_code == 422


def test_operador_sin_acceso_a_importaciones_ni_reportes(api_client, auth_headers):
    """PT_07 / PT_05 · RF_07 / RF_13 / RN_04. El operador recibe 403 en las siete rutas."""
    _, headers = account(api_client, auth_headers, 'operador', 'operador@example.test')
    for path in (STUDENTS, ENROLLMENTS):
        assert upload(api_client, headers, path, b'csv').status_code == 403
    for path in ('/api/import/templates/students', SUMMARY, REPORT, f'{REPORT}.csv', HISTORY):
        assert api_client.get(path, headers=headers).status_code == 403
