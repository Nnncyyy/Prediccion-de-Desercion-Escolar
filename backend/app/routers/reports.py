"""RF_13 / RN_04 / PT_05 · Reportes para administradores y tutores."""
from datetime import date, datetime, time, timezone
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response

from app.deps import DB, Orientador
from app.schemas import Estado, PredictionSummary
from app.services.reports import AlertLevel, StudentReport, exportar_csv, historial, reporte_alumnos, resumen

router = APIRouter(prefix='/api/reports', tags=['Reportes'])


def descarga(nombre: str, contenido: str) -> Response:
    return Response(
        contenido, media_type='text/csv',
        headers={'Content-Disposition': f'attachment; filename="{nombre}.csv"'},
    )


@router.get('/summary')
def resumen_general(db: DB, usuario: Orientador, career_id: int | None = None,
                    period: str | None = None) -> dict:
    return resumen(db, usuario, career_id, period)


@router.get('/students', response_model=list[StudentReport])
def lista_alumnos(db: DB, usuario: Orientador, career_id: int | None = None, status: Estado | None = None,
                  alert_level: AlertLevel | None = None) -> list[StudentReport]:
    return reporte_alumnos(db, usuario, career_id, status, alert_level)


@router.get('/students.csv', response_class=Response)
def csv_alumnos(db: DB, usuario: Orientador, career_id: int | None = None, status: Estado | None = None,
                 alert_level: AlertLevel | None = None) -> Response:
    rows = reporte_alumnos(db, usuario, career_id, status, alert_level)
    return descarga('students', exportar_csv(StudentReport.model_fields, rows))


def limite_utc(value: str | None, hora: time) -> datetime | None:
    if value is None:
        return None
    try:
        if len(value) == 10:
            return datetime.combine(date.fromisoformat(value), hora, tzinfo=timezone.utc)
        instante = datetime.fromisoformat(value)
        if instante.tzinfo is None:
            return instante.replace(tzinfo=timezone.utc)
        return instante.astimezone(timezone.utc)
    except (ValueError, OverflowError) as error:
        raise HTTPException(422, 'Indique una fecha o un instante ISO 8601 válido') from error


@router.get('/predictions.csv', response_class=Response)
def csv_predicciones(db: DB, usuario: Orientador, student_id: int | None = None,
                      desde: Annotated[str | None, Query(alias='from')] = None,
                      hasta: Annotated[str | None, Query(alias='to')] = None) -> Response:
    inicio = limite_utc(desde, time.min)
    fin = limite_utc(hasta, time.max)
    if inicio is not None and fin is not None and inicio > fin:
        raise HTTPException(422, 'La fecha inicial debe ser anterior o igual a la fecha final')
    rows = historial(db, usuario, student_id, inicio, fin)
    return descarga('predictions', exportar_csv(PredictionSummary.model_fields, rows))
