"""RF_13 / RN_04 / PT_05 · Indicadores y exportaciones con alcance por tutor."""
from collections import defaultdict
from collections.abc import Iterable
import csv
from datetime import datetime
from io import StringIO
from typing import Literal, get_args

from pydantic import BaseModel
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.deps import estudiantes_visibles
from app.models import Enrollment, PredictionLog, Student, User
from app.schemas import Categoria, Estado, PredictionSummary
from app.services.risk import RA_01_MIN_APROBATORIA, academic_alert

AlertLevel = Literal['baja', 'media', 'alta', 'sin_datos']


class StudentReport(BaseModel):
    enrollment_number: str
    full_name: str
    career: str
    semester: int
    status: Estado
    employed: bool
    work_hours_weekly: int
    average_grade: float
    failed_subjects: int
    alert_level: AlertLevel
    probability_dropout: float | None
    risk_category: Categoria | None
    prediction_at: datetime | None


def exportar_csv(columns: Iterable[str], rows: Iterable[BaseModel]) -> str:
    def celda(value: object) -> object:
        if isinstance(value, str) and (
            value.startswith(('\t', '\r', '\n')) or value.lstrip().startswith(('=', '+', '-', '@'))
        ):
            return "'" + value
        return value

    headers = tuple(columns)
    stream = StringIO(newline='')
    stream.write('\ufeff')
    writer = csv.writer(stream)
    writer.writerow(headers)
    for row in rows:
        data = row.model_dump(mode='json')
        writer.writerow(celda(data[column]) for column in headers)
    return stream.getvalue()


def alcance(usuario: User, career_id: int | None, status: Estado | None = None) -> Select:
    consulta = estudiantes_visibles(usuario)
    if career_id is not None:
        consulta = consulta.where(Student.career_id == career_id)
    if status is not None:
        consulta = consulta.where(Student.status == status)
    return consulta


def ids_alumnos(alumnos: Select) -> Select:
    return alumnos.with_only_columns(Student.id)


def notas_por_alumno(db: Session, alumnos: Select, period: str | None = None) -> dict[int, list[float]]:
    consulta = select(Enrollment.student_id, Enrollment.grade).where(
        Enrollment.student_id.in_(ids_alumnos(alumnos)), Enrollment.grade.is_not(None),
    )
    if period is not None:
        # BD_06 · term conserva el código también en inscripciones anteriores sin period_id.
        consulta = consulta.where(Enrollment.term == period)
    notas = defaultdict(list)
    for alumno_id, nota in db.execute(consulta):
        notas[alumno_id].append(nota)
    return notas


def indicadores_notas(notas: list[float]) -> dict:
    evaluadas = len(notas)
    reprobadas = sum(nota < RA_01_MIN_APROBATORIA for nota in notas)
    return {
        'evaluated_enrollments': evaluadas,
        'failed_enrollments': reprobadas,
        'average_grade': round(sum(notas) / evaluadas, 2) if evaluadas else 0,
        'failure_rate': round(100 * reprobadas / evaluadas, 2) if evaluadas else 0,
    }


def indicadores_ml(db: Session, alumnos: Select, incluir_globales: bool) -> dict:
    consulta = select(
        PredictionLog.risk_category, func.count(), func.sum(PredictionLog.probability_dropout),
    ).group_by(PredictionLog.risk_category)
    if not incluir_globales:
        consulta = consulta.where(PredictionLog.student_id.in_(ids_alumnos(alumnos)))
    categorias = dict.fromkeys(get_args(Categoria), 0)
    suma = 0.0
    for categoria, cantidad, probabilidades in db.execute(consulta):
        categorias[categoria] = cantidad
        suma += probabilidades
    total = sum(categorias.values())
    return {
        'predictions': total,
        'predictions_by_category': categorias,
        'average_probability_dropout': suma / total if total else 0,
    }


def resumen(db: Session, usuario: User, career_id: int | None, period: str | None) -> dict:
    alumnos = alcance(usuario, career_id)
    notas = notas_por_alumno(db, alumnos, period)
    estados = dict.fromkeys(get_args(Estado), 0)
    alertas = dict.fromkeys(get_args(AlertLevel), 0)
    alumnos_por_carrera = defaultdict(int)
    notas_por_carrera = defaultdict(list)
    altas_por_carrera = defaultdict(int)
    for alumno in db.scalars(alumnos):
        carrera = alumno.career_name or alumno.program
        calificaciones = notas.get(alumno.id, [])
        estados[alumno.status] += 1
        alumnos_por_carrera[carrera] += 1
        notas_por_carrera[carrera].extend(calificaciones)
        if alumno.active:
            alerta = academic_alert(alumno, calificaciones)['level']
            alertas[alerta] += 1
            altas_por_carrera[carrera] += int(alerta == 'alta')
    general = indicadores_notas([nota for lista in notas_por_carrera.values() for nota in lista])
    por_carrera = []
    for carrera in sorted(alumnos_por_carrera):
        indicadores = indicadores_notas(notas_por_carrera[carrera])
        por_carrera.append({
            'career': carrera,
            'students': alumnos_por_carrera[carrera],
            'average_grade': indicadores['average_grade'],
            'failure_rate': indicadores['failure_rate'],
            'alerts_alta': altas_por_carrera[carrera],
        })
    return {
        'students': sum(estados.values()),
        'active_students': sum(alertas.values()),
        'students_by_status': estados,
        **general,
        'failure_rate_denominator': general['evaluated_enrollments'],
        'alerts_by_level': alertas,
        **indicadores_ml(db, alumnos, usuario.role == 'admin' and career_id is None),
        'by_career': por_carrera,
    }


def ultimas_predicciones(db: Session, alumnos: Select) -> dict[int, PredictionSummary]:
    columns = tuple(PredictionSummary.model_fields)
    orden = PredictionLog.created_at.desc(), PredictionLog.id.desc()
    predicciones = select(
        *(getattr(PredictionLog, column) for column in columns),
        func.row_number().over(partition_by=PredictionLog.student_id, order_by=orden).label('posicion'),
    ).where(PredictionLog.student_id.in_(ids_alumnos(alumnos))).subquery()
    consulta = select(*(predicciones.c[column] for column in columns)).where(predicciones.c.posicion == 1)
    return {row['student_id']: PredictionSummary.model_validate(row) for row in db.execute(consulta).mappings()}


def reporte_alumnos(db: Session, usuario: User, career_id: int | None, status: Estado | None,
                    alert_level: AlertLevel | None) -> list[StudentReport]:
    alumnos = alcance(usuario, career_id, status)
    notas = notas_por_alumno(db, alumnos)
    predicciones = ultimas_predicciones(db, alumnos)
    resultados = []
    for alumno in db.scalars(alumnos.order_by(Student.enrollment_number)):
        alerta = academic_alert(alumno, notas.get(alumno.id, []))
        if alert_level is not None and alerta['level'] != alert_level:
            continue
        prediccion = predicciones.get(alumno.id)
        resultados.append(StudentReport(
            enrollment_number=alumno.enrollment_number,
            full_name=alumno.full_name,
            career=alumno.career_name or alumno.program,
            semester=alumno.semester,
            status=alumno.status,
            employed=alumno.employed,
            work_hours_weekly=alumno.work_hours_weekly,
            average_grade=alerta['average'] if alerta['average'] is not None else 0,
            failed_subjects=alerta['failed_subjects'],
            alert_level=alerta['level'],
            probability_dropout=prediccion.probability_dropout if prediccion else None,
            risk_category=prediccion.risk_category if prediccion else None,
            prediction_at=prediccion.created_at if prediccion else None,
        ))
    return resultados


def historial(db: Session, usuario: User, student_id: int | None,
              desde: datetime | None, hasta: datetime | None) -> Iterable[PredictionSummary]:
    consulta = select(*(getattr(PredictionLog, column) for column in PredictionSummary.model_fields))
    if usuario.role == 'tutor':
        consulta = consulta.where(PredictionLog.student_id.in_(ids_alumnos(estudiantes_visibles(usuario))))
    if student_id is not None:
        consulta = consulta.where(PredictionLog.student_id == student_id)
    if desde is not None:
        consulta = consulta.where(PredictionLog.created_at >= desde)
    if hasta is not None:
        consulta = consulta.where(PredictionLog.created_at <= hasta)
    consulta = consulta.order_by(PredictionLog.created_at.desc(), PredictionLog.id.desc())
    return (PredictionSummary.model_validate(row) for row in db.execute(consulta).mappings())
