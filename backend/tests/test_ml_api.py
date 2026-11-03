"""INT_03 · RF_09 / PT_08 y PT_07 parcial: contrato e integración FastAPI.

Objetivo: autenticar al admin temporal y consultar modelo, esquema y predicción.
Resultado esperado: 200 autenticado, 401/403 sin token, 422 inválido y 503 sin artefactos.
"""
from datetime import datetime, timedelta
import os

import joblib
import pytest

from app.services import ml


def test_contrato_autenticado(api_client, auth_headers, real_features, trained_model):
    response = api_client.get('/api/ml/model', headers=auth_headers)
    assert response.status_code == 200
    assert set(response.json()) == set(ml.MODEL_INFO_KEYS)
    assert response.json()['version'] == trained_model.artifact['version']
    assert response.json()['feature_set'] == 'temprano'
    response = api_client.get('/api/ml/schema', headers=auth_headers)
    assert response.status_code == 200
    assert [c['nombre'] for c in response.json()['columns']] == trained_model.artifact['columns']
    response = api_client.post('/api/ml/predict', headers=auth_headers, json={'features': real_features})
    assert response.status_code == 200
    body = response.json()
    assert {'clase_predicha', 'probabilidades', 'probabilidad_desercion', 'categoria_orientativa',
            'modelo', 'fecha_prediccion', 'nota', 'predicted_class', 'probabilities', 'model_name'} <= body.keys()
    assert body['modelo']['version'] == trained_model.artifact['version']
    assert datetime.fromisoformat(body['fecha_prediccion']).utcoffset() == timedelta(0)
    assert body['probabilidad_desercion'] == body['probabilidades']['Dropout']
    # RN_03 / RF_11: INT_03 no escribe historial; la conexión corresponde a INT_02.
    from sqlalchemy import func, select
    from app.database import SessionLocal
    from app.models import PredictionLog
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(PredictionLog)) == 0


@pytest.mark.parametrize(('method', 'path'), [
    ('get', '/api/ml/model'), ('get', '/api/ml/schema'), ('post', '/api/ml/predict'),
])
def test_sin_token(api_client, real_features, method, path):
    kwargs = {'json': {'features': real_features}} if method == 'post' else {}
    assert getattr(api_client, method)(path, **kwargs).status_code in (401, 403)


def test_error_422_estructurado(api_client, auth_headers, real_features):
    real_features.pop('Course')
    response = api_client.post('/api/ml/predict', headers=auth_headers, json={'features': real_features})
    assert response.status_code == 422
    assert response.json()['detail']['errores'][0]['campo'] == 'Course'


def test_modelo_y_esquema_ausentes(api_client, auth_headers, real_features, tmp_path, monkeypatch):
    monkeypatch.setattr(ml.settings, 'model_path', str(tmp_path / 'ausente.joblib'))
    for path in ('/api/ml/model', '/api/ml/schema'):
        response = api_client.get(path, headers=auth_headers)
        assert response.status_code == 503
        assert ml.TRAIN_COMMAND in response.json()['detail']
    response = api_client.post('/api/ml/predict', headers=auth_headers, json={'features': real_features})
    assert response.status_code == 503
    assert ml.TRAIN_COMMAND in response.json()['detail']


def test_cache_recarga_al_cambiar_mtime(tmp_path, monkeypatch):
    """PT_08: la caché reutiliza el archivo y detecta su sustitución sin reiniciar."""
    path = tmp_path / 'modelo.joblib'
    joblib.dump({'model_name': 'primero'}, path)
    monkeypatch.setattr(ml.settings, 'model_path', str(path))
    original_load = ml.joblib.load
    loaded = []

    def counted_load(filename):
        loaded.append(filename)
        return original_load(filename)

    monkeypatch.setattr(ml.joblib, 'load', counted_load)
    assert ml.get_model_info()['model_name'] == 'primero'
    assert ml.get_model_info()['version'] is None
    assert len(loaded) == 1
    previous = path.stat()
    joblib.dump({'model_name': 'segundo'}, path)
    os.utime(path, ns=(previous.st_atime_ns, previous.st_mtime_ns + 1_000_000_000))
    assert ml.get_model_info()['model_name'] == 'segundo'
    assert len(loaded) == 2


def test_ruta_relativa_desde_raiz(trained_model, monkeypatch):
    monkeypatch.setattr(ml, 'BASE_DIR', trained_model.path.parent)
    monkeypatch.setattr(ml.settings, 'model_path', trained_model.path.name)
    assert ml.get_model_info()['version'] == trained_model.artifact['version']
    assert ml.get_feature_schema()['feature_set'] == 'temprano'
