"""RF_09 / RF_11 / CU_04 · Inferencia de BD_11 e historial BD_07 según RN_03."""
from collections.abc import Sequence
from datetime import datetime

from fastapi import APIRouter
from sqlalchemy import select

from app.deps import DB, Inicio, Limite, Orientador, UsuarioActual, estudiante_visible
from app.models import PredictionLog, Student
from app.schemas import MLPredictInput, PredictionOut
from app.services import ml
from app.services.audit import guardar

router = APIRouter(prefix='/api', tags=['Predicciones'])


@router.get('/ml/model')
def modelo(usuario: UsuarioActual) -> dict:
    return ml.get_model_info()


@router.get('/ml/schema')
def esquema(usuario: UsuarioActual) -> dict:
    return ml.get_feature_schema()


@router.post('/ml/predict')
def predecir(body: MLPredictInput, db: DB, usuario: Orientador) -> dict:
    if body.student_id is not None:
        estudiante_visible(db, usuario, body.student_id)
    resultado = ml.predict(body.features)
    fecha = datetime.fromisoformat(resultado['fecha_prediccion'])
    registro = PredictionLog(
        student_id=body.student_id, user_id=usuario.id, model_version=resultado['modelo']['version'],
        task=resultado['modelo']['task'], created_at=fecha, features=body.features,
        predicted_class=resultado['clase_predicha'], probability_dropout=resultado['probabilidades']['Dropout'],
        risk_category=resultado['categoria_orientativa'],
    )
    guardar(db, usuario, registro, 'predecir')
    return {**resultado, 'prediction_id': registro.id, 'created_at': fecha.isoformat()}


@router.get('/students/{student_id}/predictions', response_model=list[PredictionOut])
@router.get('/ml/predictions', response_model=list[PredictionOut])
def historial(db: DB, usuario: Orientador, student_id: int | None = None,
              skip: Inicio = 0, limit: Limite = 100) -> Sequence[PredictionLog]:
    consulta = select(PredictionLog)
    if student_id is not None:
        estudiante_visible(db, usuario, student_id)
        consulta = consulta.where(PredictionLog.student_id == student_id)
    elif usuario.role == 'tutor':
        consulta = consulta.join(Student).where(Student.tutor_id == usuario.id)
    consulta = consulta.order_by(PredictionLog.created_at.desc(), PredictionLog.id.desc())
    return db.scalars(consulta.offset(skip).limit(limit)).all()
