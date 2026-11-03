"""RA_01 · RF_10: reglas académicas y bordes del servicio INT_03.

Objetivo: comprobar cada razón, niveles y compatibilidad del resultado.
Resultado esperado: 6.0 aprueba, 30 h activa R3 y sin notas retorna sin_datos.
"""
from types import SimpleNamespace
from app.services.risk import academic_alert

def test_no_grades_is_not_low_risk():
    assert academic_alert(SimpleNamespace(employed=False,work_hours_weekly=0),[])['level']=='sin_datos'

def test_failed_and_employed_alert():
    result=academic_alert(SimpleNamespace(employed=True,work_hours_weekly=32),[4,5,7])
    assert result['failed_subjects']==2
    assert result['level']=='alta'


def student(employed=False, hours=0):
    """RA_01: construye únicamente los atributos usados por las reglas."""
    return SimpleNamespace(employed=employed, work_hours_weekly=hours)


def reason_ids(result):
    """RA_01: obtiene los identificadores sin depender del texto descriptivo."""
    return [reason.split(':', 1)[0] for reason in result['reasons']]


def test_ra_01_r1_dos_reprobadas():
    result = academic_alert(student(), [5, 5, 10])
    assert reason_ids(result) == ['RA_01_R1']
    assert result['level'] == 'media'


def test_ra_01_r2_promedio_inferior():
    result = academic_alert(student(), [5])
    assert reason_ids(result) == ['RA_01_R2']
    assert result['average'] == 5


def test_ra_01_r3_exactamente_30_horas():
    result = academic_alert(student(True, 30), [5, 9])
    assert reason_ids(result) == ['RA_01_R3']
    assert result['level'] == 'media'


def test_ra_01_29_horas_no_activa_r3():
    result = academic_alert(student(True, 29), [5, 9])
    assert result['reasons'] == []
    assert result['level'] == 'media'


def test_ra_01_sin_empleo_no_activa_r3():
    assert academic_alert(student(False, 30), [5, 9])['reasons'] == []


def test_ra_01_sin_reprobadas_no_activa_r3():
    assert academic_alert(student(True, 30), [6, 8])['reasons'] == []


def test_ra_01_nota_y_promedio_exactamente_6():
    result = academic_alert(student(), [6.0])
    assert result['failed_subjects'] == 0
    assert result['average'] == 6.0
    assert result['level'] == 'baja'
    assert result['reasons'] == []
    assert academic_alert(student(), [5, 7])['reasons'] == []


def test_ra_01_sin_notas_y_nulos():
    for grades in ([], [None], [None, None]):
        result = academic_alert(student(True, 30), grades)
        assert result == {'level': 'sin_datos', 'average': None, 'failed_subjects': 0,
                          'evaluated_subjects': 0, 'reasons': [],
                          'method': 'Reglas orientativas; no es una predicción ML'}


def test_ra_01_nulos_excluidos_y_dos_razones_alta():
    result = academic_alert(student(), [None, 4, 5])
    assert reason_ids(result) == ['RA_01_R1', 'RA_01_R2']
    assert result['evaluated_subjects'] == 2
    assert result['level'] == 'alta'
    assert result['method'] == 'Reglas orientativas; no es una predicción ML'
