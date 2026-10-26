from app.models import Student

def academic_alert(student: Student, grade_rows: list[float | None]):
    """Reglas preliminares configurables. Nunca retorna probabilidad de deserción."""
    grades = [g for g in grade_rows if g is not None]
    failed = sum(g < 6 for g in grades)  # Aprobar a partir de 6: regla ilustrativa
    avg = round(sum(grades)/len(grades), 2) if grades else None
    reasons = []
    if failed >= 2: reasons.append('Dos o más materias reprobadas')
    if avg is not None and avg < 6: reasons.append('Promedio inferior a 6')
    if student.employed and student.work_hours_weekly >= 30 and failed >= 1:
        reasons.append('Jornada laboral de 30+ horas combinada con reprobación')
    if not grades: level = 'sin_datos'
    elif len(reasons)>=2: level='alta'
    elif reasons or failed == 1: level='media'
    else: level='baja'
    return {'level':level, 'average':avg, 'failed_subjects':failed,'evaluated_subjects':len(grades),'reasons':reasons,'method':'Reglas orientativas; no es una predicción ML'}
