"""Verificación SQL de las restricciones de integridad de SQLite."""

from datetime import date

import pytest
from sqlalchemy import create_engine, insert, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import Base
from app.models import AuditLog, Career, Enrollment, FollowUp, Period, PredictionLog, Student, Subject, User
from helpers import student_data


@pytest.fixture
def db(tmp_path):
    engine = create_engine(f'sqlite:///{tmp_path / "pt06.sqlite"}')
    try:
        Base.metadata.create_all(engine)
        with Session(engine) as session:
            yield session
    finally:
        engine.dispose()


USER = {'email': 'pt06@example.test', 'role': 'tutor', 'password_hash': 'fixture-sin-login'}
CAREER = {'code': 'SIS', 'name': 'Sistemas'}
PERIOD = {'code': 'PT06', 'name': 'Periodo de prueba'}
SUBJECT = {'code': 'MAT', 'name': 'Matemáticas'}
STUDENT = student_data(career_id=1, tutor_id=1)
ENROLLMENT = {'student_id': 1, 'subject_id': 1, 'period_id': 1, 'term': PERIOD['code'], 'grade': 6.0}
PREDICTION = {'student_id': 1, 'user_id': 1, 'predicted_class': 'No_Dropout',
              'risk_category': 'baja', 'probability_dropout': 0.2, 'features': {}}
FOLLOWUP = {'student_id': 1, 'tutor_id': 1, 'note': 'Seguimiento', 'date': date(2026, 11, 24)}


@pytest.fixture
def seeded_db(db):
    for model, data in ((User, USER), (Career, CAREER), (Period, PERIOD), (Subject, SUBJECT),
                        (Student, STUDENT), (Enrollment, ENROLLMENT)):
        db.execute(insert(model), {'id': 1, **data})
    db.commit()
    return db


def test_pt06_pragma_foreign_keys(db):
    """PT_06 · RNF_03 · Verificar la configuración de conexión SQLite. Esperado: PRAGMA foreign_keys devuelve 1."""
    assert db.scalar(text('PRAGMA foreign_keys')) == 1


@pytest.mark.parametrize(('model', 'duplicate'), [
    pytest.param(User, USER, id='correo'),
    pytest.param(Career, {**CAREER, 'name': 'Nombre nuevo'}, id='codigo-carrera'),
    pytest.param(Career, {**CAREER, 'code': 'NUEVO'}, id='nombre-carrera'),
    pytest.param(Period, PERIOD, id='codigo-periodo'),
    pytest.param(Subject, SUBJECT, id='codigo-materia'),
    pytest.param(Student, STUDENT, id='matricula'),
    pytest.param(Enrollment, {**ENROLLMENT, 'grade': 8}, id='alumno-materia-periodo'),
])
def test_pt06_unique(seeded_db, model, duplicate):
    """PT_06 · RNF_03 · Insertar una clave de negocio duplicada por SQL. Esperado: SQLITE_CONSTRAINT_UNIQUE."""
    with pytest.raises(IntegrityError) as error:
        seeded_db.execute(insert(model), duplicate)
    assert error.value.orig.sqlite_errorname == 'SQLITE_CONSTRAINT_UNIQUE'


@pytest.mark.parametrize(('model', 'data', 'field'), [
    pytest.param(Student, {**STUDENT, 'enrollment_number': 'NUEVA'}, 'career_id', id='student-career'),
    pytest.param(Student, {**STUDENT, 'enrollment_number': 'NUEVA'}, 'tutor_id', id='student-tutor'),
    pytest.param(Enrollment, ENROLLMENT, 'student_id', id='enrollment-student'),
    pytest.param(Enrollment, ENROLLMENT, 'subject_id', id='enrollment-subject'),
    pytest.param(Enrollment, {**ENROLLMENT, 'term': 'NUEVO'}, 'period_id', id='enrollment-period'),
    pytest.param(PredictionLog, PREDICTION, 'student_id', id='prediction-student'),
    pytest.param(PredictionLog, PREDICTION, 'user_id', id='prediction-user'),
    pytest.param(FollowUp, FOLLOWUP, 'student_id', id='followup-student'),
    pytest.param(FollowUp, FOLLOWUP, 'tutor_id', id='followup-tutor'),
    pytest.param(AuditLog, {'user_id': 1, 'action': 'crear', 'entity': 'students', 'entity_id': 1},
                 'user_id', id='audit-user'),
])
def test_pt06_fk(seeded_db, model, data, field):
    """PT_06 · RNF_03 · Insertar una referencia inexistente por SQL. Esperado: SQLITE_CONSTRAINT_FOREIGNKEY."""
    with pytest.raises(IntegrityError) as error:
        seeded_db.execute(insert(model), {**data, field: 999999})
    assert error.value.orig.sqlite_errorname == 'SQLITE_CONSTRAINT_FOREIGNKEY'


@pytest.mark.parametrize(('model', 'data', 'field', 'invalid'), [
    pytest.param(Enrollment, {**ENROLLMENT, 'term': 'CHECK'}, 'grade', -0.01, id='grade-min'),
    pytest.param(Enrollment, {**ENROLLMENT, 'term': 'CHECK'}, 'grade', 10.01, id='grade-max'),
    pytest.param(Student, {**STUDENT, 'enrollment_number': 'CHECK'}, 'semester', 0, id='semester-min'),
    pytest.param(Student, {**STUDENT, 'enrollment_number': 'CHECK'}, 'semester', 21, id='semester-max'),
    pytest.param(Student, {**STUDENT, 'enrollment_number': 'CHECK'}, 'work_hours_weekly', -1, id='hours-min'),
    pytest.param(Student, {**STUDENT, 'enrollment_number': 'CHECK'}, 'work_hours_weekly', 101, id='hours-max'),
    pytest.param(User, {**USER, 'email': 'check@example.test'}, 'role', 'invalido', id='role'),
    pytest.param(Student, {**STUDENT, 'enrollment_number': 'CHECK'}, 'status', 'invalido', id='status'),
    pytest.param(PredictionLog, PREDICTION, 'risk_category', 'sin_datos', id='risk-category'),
])
def test_pt06_check(seeded_db, model, data, field, invalid):
    """PT_06 · RNF_03 · Insertar un valor fuera del rango o catálogo por SQL. Esperado: SQLITE_CONSTRAINT_CHECK."""
    with pytest.raises(IntegrityError) as error:
        seeded_db.execute(insert(model), {**data, field: invalid})
    assert error.value.orig.sqlite_errorname == 'SQLITE_CONSTRAINT_CHECK'
