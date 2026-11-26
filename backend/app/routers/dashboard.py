"""RF_12 / CU_06 / PT_06 · Indicadores académicos y ML con el alcance del usuario."""
from collections import Counter, defaultdict

from fastapi import APIRouter
from sqlalchemy import func, select
from sqlalchemy.orm import Session, defer

from app.deps import DB, UsuarioActual, estudiantes_visibles
from app.models import Enrollment, PredictionLog, Student, Subject, User
from app.schemas import PredictionSummary
from app.services.risk import RA_01_MIN_APROBATORIA, academic_alert

router = APIRouter(prefix='/api/dashboard', tags=['Dashboard'])


def indicadores_ml(db: Session, usuario: User) -> dict:
    resumen = select(PredictionLog.risk_category, func.count()).group_by(PredictionLog.risk_category)
    recientes = select(PredictionLog).options(defer(PredictionLog.features))
    if usuario.role == 'tutor':
        propios = select(Student.id).where(Student.tutor_id == usuario.id)
        resumen = resumen.where(PredictionLog.student_id.in_(propios))
        recientes = recientes.where(PredictionLog.student_id.in_(propios))
    categorias = dict.fromkeys(('baja', 'media', 'alta'), 0)
    categorias.update(db.execute(resumen).all())
    ultimas = db.scalars(recientes.order_by(PredictionLog.created_at.desc(), PredictionLog.id.desc()).limit(5))
    return {
        'predictions': sum(categorias.values()),
        'predictions_by_category': categorias,
        'last_predictions': [PredictionSummary.model_validate(fila) for fila in ultimas],
    }


@router.get('')
def dashboard(db: DB, usuario: UsuarioActual) -> dict:
    alumnos = db.scalars(estudiantes_visibles(usuario)).all()
    consulta = select(Enrollment.student_id, Enrollment.subject_id, Enrollment.grade)
    if usuario.role == 'tutor':
        consulta = consulta.join(Student).where(Student.tutor_id == usuario.id)
    notas: dict[int, list[float]] = defaultdict(list)
    materias = set()
    inscripciones = 0
    reprobadas = 0
    for alumno_id, materia_id, nota in db.execute(consulta):
        materias.add(materia_id)
        inscripciones += 1
        if nota is not None:
            notas[alumno_id].append(nota)
            reprobadas += int(nota < RA_01_MIN_APROBATORIA)

    estados = dict.fromkeys(('activo', 'baja_temporal', 'baja_definitiva', 'egresado'), 0)
    alertas = dict.fromkeys(('baja', 'media', 'alta', 'sin_datos'), 0)
    carreras: Counter[str] = Counter()
    activos = 0
    for alumno in alumnos:
        estados[alumno.status] += 1
        carreras[alumno.career_name or alumno.program] += 1
        if alumno.active:
            activos += 1
            alerta = academic_alert(alumno, notas.get(alumno.id, []))
            alertas[alerta['level']] += 1

    evaluadas = sum(map(len, notas.values()))
    total_materias = len(materias) if usuario.role == 'tutor' else db.scalar(select(func.count(Subject.id)))
    return {
        'students': len(alumnos),
        'subjects': total_materias,
        'enrollments': inscripciones,
        'active_students': activos,
        'inactive_students': len(alumnos) - activos,
        'students_by_status': estados,
        'students_by_career': [{'career': nombre, 'count': carreras[nombre]} for nombre in sorted(carreras)],
        'average_grade': round(sum(map(sum, notas.values())) / evaluadas, 2) if evaluadas else None,
        'failed_enrollments': reprobadas,
        'alerts_by_level': alertas,
        **indicadores_ml(db, usuario),
    }
