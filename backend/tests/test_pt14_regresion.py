"""Regresión del recorrido de administración, captura, tutoría y reportes."""

from collections import Counter
import csv
from io import StringIO

from helpers import PASSWORD, account_data, bearer, create, login, request_json, student_data


def read_csv(client, headers, path, params):
    response = client.get(path, headers=headers, params=params)
    assert response.status_code == 200, response.text
    assert response.headers['content-type'].startswith('text/csv')
    assert response.headers['content-disposition'].startswith('attachment;')
    return list(csv.DictReader(StringIO(response.content.decode('utf-8-sig'), newline='')))


def test_pt14_flujo_completo(api_client, auth_headers, real_features, trained_model):
    """PT_14 · CU_01–CU_05/RF_01–RF_06/RF_09–RF_11/RF_13–RF_14/RNF_05 · Ejecutar el recorrido por API. Esperado: captura, alerta, inferencia, reportes y bitácora coherentes."""
    admin = request_json(api_client, 'GET', '/api/auth/me', 200, headers=auth_headers)
    career = create(api_client, auth_headers, 'careers', code='PT14-SIS', name='Sistemas')
    period = create(api_client, auth_headers, 'periods', code='2026-2', name='Segundo semestre',
                    start_date='2026-08-01', end_date='2026-12-15')
    subjects = [
        create(api_client, auth_headers, 'subjects', code=code, name=name, credits=5)
        for code, name in [('MAT', 'Matemáticas'), ('HIS', 'Historia'), ('BIO', 'Biología')]
    ]
    tutor = create(api_client, auth_headers, 'users', **account_data('tutor'))
    operator = create(api_client, auth_headers, 'users', **account_data('operador'))
    operator_headers = bearer(login(api_client, operator['email'], PASSWORD)['access_token'])
    tutor_headers = bearer(login(api_client, tutor['email'], PASSWORD)['access_token'])

    student = create(api_client, operator_headers, 'students',
                     **student_data('PT14-A001', program='', career_id=career['id'],
                                    employed=True, work_hours_weekly=30))
    enrollments = [
        create(api_client, operator_headers, 'enrollments', student_id=student['id'],
               subject_id=subject['id'], period_id=period['id'], grade=grade)
        for subject, grade in zip(subjects, (4.0, 5.0, 6.0), strict=True)
    ]
    student_path = f'/api/students/{student["id"]}'
    assignment = request_json(api_client, 'PUT', f'{student_path}/tutor', 200,
                              headers=auth_headers, json={'tutor_id': tutor['id']})
    assert assignment['tutor_id'] == tutor['id']

    alert = request_json(api_client, 'GET', f'{student_path}/alert', 200, headers=tutor_headers)
    assert (alert['student_id'], alert['level'], alert['average']) == (student['id'], 'alta', 5.0)
    assert (alert['failed_subjects'], alert['evaluated_subjects']) == (2, 3)
    assert [reason.split(':', 1)[0] for reason in alert['reasons']] == ['RA_01_R1', 'RA_01_R2', 'RA_01_R3']
    notes = {'date': '2026-11-24', 'note': 'Se revisaron dos materias reprobadas.', 'agreement': 'Asistir a asesoría'}
    followup = create(api_client, tutor_headers, f'students/{student["id"]}/followups', **notes)
    assert (followup['student_id'], followup['tutor_id']) == (student['id'], tutor['id'])
    assert {key: followup[key] for key in notes} == notes
    prediction = request_json(api_client, 'POST', '/api/ml/predict', 200, headers=tutor_headers,
                              json={'student_id': student['id'], 'features': real_features})

    record, = request_json(api_client, 'GET', '/api/ml/predictions', 200, headers=auth_headers)
    assert (record['id'], record['student_id'], record['user_id']) == (
        prediction['prediction_id'], student['id'], tutor['id'],
    )
    assert record['model_version'] == prediction['modelo']['version'] == trained_model.artifact['version']
    assert record['probability_dropout'] == prediction['probabilidad_desercion']
    assert request_json(api_client, 'GET', f'{student_path}/predictions', 200, headers=auth_headers) == [record]
    assert request_json(api_client, 'GET', f'{student_path}/followups', 200, headers=auth_headers) == [followup]

    summary = request_json(api_client, 'GET', '/api/reports/summary', 200, headers=auth_headers,
                           params={'career_id': career['id'], 'period': period['code']})
    assert (summary['students'], summary['evaluated_enrollments'], summary['failed_enrollments']) == (1, 3, 2)
    assert (summary['average_grade'], summary['failure_rate']) == (5.0, 66.67)
    assert summary['alerts_by_level'] == {'baja': 0, 'media': 0, 'alta': 1, 'sin_datos': 0}
    assert summary['predictions'] == summary['predictions_by_category'][record['risk_category']] == 1
    csv_student, = read_csv(api_client, auth_headers, '/api/reports/students.csv', {'career_id': career['id']})
    assert csv_student['enrollment_number'] == student['enrollment_number']
    assert (csv_student['alert_level'], int(csv_student['failed_subjects'])) == ('alta', 2)
    assert csv_student['risk_category'] == record['risk_category']
    csv_prediction, = read_csv(api_client, auth_headers, '/api/reports/predictions.csv', {'student_id': student['id']})
    assert (int(csv_prediction['id']), int(csv_prediction['user_id'])) == (record['id'], tutor['id'])
    assert csv_prediction['model_version'] == record['model_version']

    events = request_json(api_client, 'GET', '/api/audit', 200, headers=auth_headers)
    expected = Counter([
        ('login', 'users', admin['id'], admin['id']),
        ('crear', 'careers', career['id'], admin['id']),
        ('crear', 'periods', period['id'], admin['id']),
        *(('crear', 'subjects', subject['id'], admin['id']) for subject in subjects),
        ('crear', 'users', tutor['id'], admin['id']),
        ('crear', 'users', operator['id'], admin['id']),
        ('login', 'users', operator['id'], operator['id']),
        ('login', 'users', tutor['id'], tutor['id']),
        ('crear', 'students', student['id'], operator['id']),
        *(('crear', 'enrollments', row['id'], operator['id']) for row in enrollments),
        ('editar', 'students', student['id'], admin['id']),
        ('crear', 'followups', followup['id'], tutor['id']),
        ('predecir', 'prediction_logs', record['id'], tutor['id']),
    ])
    assert Counter((e['action'], e['entity'], e['entity_id'], e['user_id']) for e in events) == expected
    assigned, = [e for e in events if e['entity'] == 'students' and e['action'] == 'editar']
    assert assigned['detail'] == {'tutor_id': tutor['id']}
