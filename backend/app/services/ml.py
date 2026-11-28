"""INT_03 · RF_09: inferencia validada, independiente de RA_01 y sin persistencia."""
from datetime import datetime, timezone
from functools import lru_cache
import json
import math
from numbers import Real
from pathlib import Path

import joblib
import pandas as pd
from fastapi import HTTPException

from app.config import settings

BASE_DIR = Path(__file__).resolve().parents[3]
MODEL_INFO_KEYS = (
    'model_name', 'version', 'task', 'feature_set', 'classes', 'metrics',
    'trained_at', 'dataset_sha256', 'sklearn_version',
)
NOTA_RN_01 = (
    'RN_01: Es una estimación estadística, no un diagnóstico. '
    'RN_05: Es independiente de las alertas por reglas RA_01; requiere revisión humana.'
)
TRAIN_COMMAND = 'python ml/training/train.py'


def _model_path() -> Path:
    """INT_03: resuelve MODEL_PATH desde la raíz del repositorio."""
    path = Path(settings.model_path)
    return (BASE_DIR / path).resolve() if not path.is_absolute() else path.resolve()


@lru_cache(maxsize=4)
def _load_artifact(path: Path, mtime_ns: int, size: int) -> dict:
    """INT_03: carga solo joblib locales confiables; la firma invalida la caché."""
    return joblib.load(path)


def _get_artifact() -> dict:
    """RF_09: reutiliza el modelo mientras no cambien ruta, mtime o tamaño."""
    path = _model_path()
    try:
        stat = path.stat()
        return _load_artifact(path, stat.st_mtime_ns, stat.st_size)
    except FileNotFoundError:
        raise HTTPException(503, f'INT_03: Modelo no entrenado. Desde la raíz ejecuta: {TRAIN_COMMAND}') from None


def get_model_info() -> dict:
    """RF_09: expone metadatos; artefactos antiguos pueden carecer de ellos."""
    artifact = _get_artifact()
    return {key: artifact.get(key) for key in MODEL_INFO_KEYS}


def get_feature_schema() -> dict:
    """PT_08: obtiene el esquema que acompaña al artefacto configurado."""
    path = _model_path().with_name('feature_schema.json')
    try:
        return json.loads(path.read_text(encoding='utf-8-sig'))
    except FileNotFoundError:
        raise HTTPException(503, f'INT_03: Falta feature_schema.json. Desde la raíz ejecuta: {TRAIN_COMMAND}') from None


def _normalize_name(name: str) -> str:
    """PT_08: elimina BOM y espacios exteriores de los encabezados."""
    return name.replace('\ufeff', '').strip()


def _received(value):
    """PT_08: representa también valores no finitos en errores JSON válidos."""
    if isinstance(value, Real) and not math.isfinite(value):
        return str(value)
    return value


def validate_features(features: dict) -> dict:
    """PT_08: rechaza faltantes, sobrantes, duplicados normalizados y valores inválidos."""
    schema = get_feature_schema()
    columns = {column['nombre']: column for column in schema['columns']}
    normalized, errors = {}, []

    def error(field, problem, expected, received):
        errors.append({'campo': field, 'problema': problem,
                       'esperado': expected, 'recibido': _received(received)})

    for original, value in features.items():
        name = _normalize_name(original)
        if name in normalized:
            error(name, 'PT_08: Nombre duplicado después de normalizar', 'Un solo valor por campo', value)
        normalized[name] = value
        if name not in columns:
            error(name, 'PT_08: Campo sobrante', 'Solo columnas de GET /api/ml/schema', value)
    for name, metadata in columns.items():
        if name not in normalized:
            error(name, 'PT_08: Campo faltante', 'Valor numérico obligatorio', None)
            continue
        value = normalized[name]
        if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value):
            error(name, 'PT_08: Tipo inválido', 'Número finito, sin booleanos ni nulos', value)
            continue
        if metadata['tipo'] == 'nominal':
            codes = metadata['valores_permitidos']
            if value not in codes:
                error(name, 'PT_08: Código nominal no permitido', codes, value)
        elif not metadata['min'] <= value <= metadata['max']:
            error(name, 'PT_08: Valor fuera de rango',
                  {'min': metadata['min'], 'max': metadata['max']}, value)
    if errors:
        raise HTTPException(422, detail={
            'mensaje': 'PT_08: Entrada inválida para el esquema ML.', 'errores': errors,
        })
    return normalized


def predict(features: dict) -> dict:
    """RF_09 / RN_01 / RN_05: devuelve probabilidades alineadas por model.classes_."""
    artifact = _get_artifact()
    validated = validate_features(features)
    columns = artifact['columns']
    if set(columns) != set(validated):
        raise HTTPException(503, f'INT_03: Modelo y esquema incompatibles. Ejecuta: {TRAIN_COMMAND}')
    row = pd.DataFrame([{column: validated[column] for column in columns}])
    model = artifact['pipeline']
    probabilities = {str(label): float(value) for label, value in
                     zip(model.classes_, model.predict_proba(row)[0])}
    dropout_probability = probabilities['Dropout']
    if dropout_probability >= settings.ml_umbral_alto:
        category = 'alta'
    elif dropout_probability >= settings.ml_umbral_medio:
        category = 'media'
    else:
        category = 'baja'
    predicted = str(model.predict(row)[0])
    return {
        'clase_predicha': predicted, 'probabilidades': probabilities,
        'probabilidad_desercion': dropout_probability, 'categoria_orientativa': category,
        'modelo': {key: artifact.get(key) for key in ('model_name', 'version', 'task')},
        'fecha_prediccion': datetime.now(timezone.utc).isoformat(), 'nota': NOTA_RN_01,
        'predicted_class': predicted, 'probabilities': probabilities,
        'model_name': artifact.get('model_name'), 'note': NOTA_RN_01,
    }
