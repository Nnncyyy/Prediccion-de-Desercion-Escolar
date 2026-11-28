from app.models import Student

RA_01_MIN_APROBATORIA = 6
RA_01_MAX_REPROBADAS = 2
RA_01_HORAS_TRABAJO = 30

def academic_alert(student: Student, grade_rows: list[float | None]):
    """RA_01 / RF_10: reglas orientativas independientes de la probabilidad ML (RN_05).

    ID       | Condición                              | Razón
    RA_01_R1 | Reprobadas >= RA_01_MAX_REPROBADAS       | Dos o más reprobadas
    RA_01_R2 | Promedio redondeado < MIN_APROBATORIA   | Promedio inferior a 6
    RA_01_R3 | Trabaja, horas >= 30 y reprobadas >= 1  | Trabajo y reprobación
    RA_01_N0 | Sin calificaciones                     | sin_datos
    RA_01_N1 | Dos o más razones                      | alta
    RA_01_N2 | Una razón o una reprobada               | media
    RA_01_N3 | Ninguna de las condiciones anteriores | baja

    Una nota < RA_01_MIN_APROBATORIA reprueba; 6.0 aprueba y 30 h activa R3.
    """
    grades = [g for g in grade_rows if g is not None]
    failed = sum(g < RA_01_MIN_APROBATORIA for g in grades)
    avg = round(sum(grades)/len(grades), 2) if grades else None
    reasons = []
    if failed >= RA_01_MAX_REPROBADAS: reasons.append('RA_01_R1: Dos o más materias reprobadas')
    if avg is not None and avg < RA_01_MIN_APROBATORIA: reasons.append('RA_01_R2: Promedio inferior a 6')
    if student.employed and student.work_hours_weekly >= RA_01_HORAS_TRABAJO and failed >= 1:
        reasons.append('RA_01_R3: Jornada laboral de 30+ horas combinada con reprobación')
    if not grades: level = 'sin_datos'
    elif len(reasons)>=2: level='alta'
    elif reasons or failed == 1: level='media'
    else: level='baja'
    return {'level':level, 'average':avg, 'failed_subjects':failed,'evaluated_subjects':len(grades),'reasons':reasons,'method':'Reglas orientativas; no es una predicción ML'}
