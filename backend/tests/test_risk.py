from types import SimpleNamespace
from app.services.risk import academic_alert

def test_no_grades_is_not_low_risk():
    assert academic_alert(SimpleNamespace(employed=False,work_hours_weekly=0),[])['level']=='sin_datos'

def test_failed_and_employed_alert():
    result=academic_alert(SimpleNamespace(employed=True,work_hours_weekly=32),[4,5,7])
    assert result['failed_subjects']==2
    assert result['level']=='alta'
