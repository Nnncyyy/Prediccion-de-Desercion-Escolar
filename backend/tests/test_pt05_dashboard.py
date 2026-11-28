"""Indicadores exactos para el alcance global y el de un tutor."""

from datetime import datetime, timezone

import pytest

from app import database
from app.models import Career, Enrollment, PredictionLog, Student, Subject
from helpers import actors, fixture_password_hash, request_json, student_data


@pytest.fixture
def dashboard_data(actors):
    tutor_id, _ = actors['tutor']
    admin_id, _ = actors['admin']
    with database.SessionLocal() as db:
        career = Career(code='SIS', name='Sistemas')
        subjects = [Subject(code=code, name=code) for code in ('MAT', 'HIS', 'BIO', 'LIBRE')]
        own_high = Student(**student_data('ALTA', employed=True, work_hours_weekly=30), tutor_id=tutor_id)
        own_no_grades = Student(**student_data('PENDIENTE', program='Diseño'), tutor_id=tutor_id)
        own_inactive = Student(**student_data('INACTIVO'), tutor_id=tutor_id, active=False, status='egresado')
        own_high.career = own_inactive.career = career
        other_medium = Student(**student_data('MEDIA', program='Diseño'))
        other_low = Student(**student_data('BAJA'), career=career)
        db.add_all([*subjects, own_high, own_no_grades, own_inactive, other_medium, other_low])
        db.flush()

        for student, subject, grade in [
            (own_high, subjects[0], 4), (own_high, subjects[1], 5), (own_no_grades, subjects[0], None),
            (own_inactive, subjects[1], 2), (other_medium, subjects[0], 5), (other_medium, subjects[2], 9),
            (other_low, subjects[2], 6),
        ]:
            db.add(Enrollment(student_id=student.id, subject_id=subject.id, term='PT05', grade=grade))

        predictions = []
        for student, category, probability, day in [
            (own_high, 'alta', 0.8, 1), (own_high, 'media', 0.5, 2),
            (own_inactive, 'baja', 0.1, 3), (other_medium, 'media', 0.4, 4),
            (None, 'alta', 0.9, 5), (other_low, 'baja', 0.2, 5),
        ]:
            row = PredictionLog(student_id=student.id if student else None, user_id=admin_id, model_version='PT05',
                                task='binaria', predicted_class='Dropout' if probability >= 0.5 else 'No_Dropout',
                                risk_category=category, probability_dropout=probability, features={'dato': 1},
                                created_at=datetime(2026, 1, day, tzinfo=timezone.utc))
            db.add(row)
            predictions.append(row)
        db.flush()
        ids = [row.id for row in predictions]
        db.commit()
    return ids


@pytest.mark.parametrize(('role', 'expected', 'recent_positions'), [
    ('admin', {
        'students': 5, 'subjects': 4, 'enrollments': 7, 'active_students': 4, 'inactive_students': 1,
        'students_by_status': {'activo': 4, 'baja_temporal': 0, 'baja_definitiva': 0, 'egresado': 1},
        'students_by_career': [{'career': 'Diseño', 'count': 2}, {'career': 'Sistemas', 'count': 3}],
        'average_grade': 5.17, 'failed_enrollments': 4,
        'alerts_by_level': {'baja': 1, 'media': 1, 'alta': 1, 'sin_datos': 1},
        'predictions': 6, 'predictions_by_category': {'baja': 2, 'media': 2, 'alta': 2},
    }, [5, 4, 3, 2, 1]),
    ('tutor', {
        'students': 3, 'subjects': 2, 'enrollments': 4, 'active_students': 2, 'inactive_students': 1,
        'students_by_status': {'activo': 2, 'baja_temporal': 0, 'baja_definitiva': 0, 'egresado': 1},
        'students_by_career': [{'career': 'Diseño', 'count': 1}, {'career': 'Sistemas', 'count': 2}],
        'average_grade': 3.67, 'failed_enrollments': 3,
        'alerts_by_level': {'baja': 0, 'media': 0, 'alta': 1, 'sin_datos': 1},
        'predictions': 3, 'predictions_by_category': {'baja': 1, 'media': 1, 'alta': 1},
    }, [2, 1, 0]),
], ids=['admin-global', 'tutor-asignados'])
def test_pt05_dashboard_con_valores_exactos(api_client, actors, dashboard_data, role, expected, recent_positions):
    """PT_05 · CU_05/CU_06/RF_12 · Conciliar indicadores académicos, RA_01 y ML. Esperado: conteos y promedios exactos por rol."""
    _, headers = actors[role]
    result = request_json(api_client, 'GET', '/api/dashboard', 200, headers=headers)
    recent = result.pop('last_predictions')
    assert result == expected
    assert [row['id'] for row in recent] == [dashboard_data[position] for position in recent_positions]
    assert all('features' not in row for row in recent)
