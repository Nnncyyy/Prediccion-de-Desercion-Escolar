"""PT_08 · RF_09: esquema e integridad de entrada del servicio INT_03.

Objetivo: aceptar filas reales y rechazar datos incompletos o fuera del contrato.
Resultado esperado: columnas alineadas, probabilidades válidas y errores 422 por campo.
"""
import json
import math

import numpy as np
import pytest
from fastapi import HTTPException

from app.services import ml
from ml.common import CLASSES, CONFIG_RECOMENDADA, FEATURE_SETS


def test_columnas_artifacto_esquema_y_horizonte(trained_model):
    columns = trained_model.artifact['columns']
    assert columns == [row['nombre'] for row in ml.get_feature_schema()['columns']]
    assert columns == FEATURE_SETS[CONFIG_RECOMENDADA['conjunto']]
    assert all('\ufeff' not in column and column == column.strip() for column in columns)


def test_prediccion_real_y_compatibilidad(real_features):
    result = ml.predict(real_features)
    assert sum(result['probabilidades'].values()) == pytest.approx(1, abs=1e-6)
    assert all(0 <= p <= 1 for p in result['probabilidades'].values())
    assert result['probabilidad_desercion'] == result['probabilidades']['Dropout']
    assert result['predicted_class'] == result['clase_predicha']
    assert result['probabilities'] == result['probabilidades']
    assert result['model_name'] == result['modelo']['model_name']
    assert 'RN_01' in result['nota'] and 'RN_05' in result['nota']


def assert_invalid(features, field):
    """PT_08: exige el detalle estructurado y la identificación del campo inválido."""
    with pytest.raises(HTTPException) as caught:
        ml.predict(features)
    assert caught.value.status_code == 422
    detail = caught.value.detail
    assert detail['mensaje']
    assert any(error['campo'] == field for error in detail['errores'])
    assert all(set(error) == {'campo', 'problema', 'esperado', 'recibido'} for error in detail['errores'])
    json.dumps(detail, allow_nan=False)


def test_faltante(real_features):
    field = next(iter(real_features))
    real_features.pop(field)
    assert_invalid(real_features, field)


def test_sobrante(real_features):
    real_features['Target'] = 'Dropout'
    assert_invalid(real_features, 'Target')


def test_fuera_de_rango(real_features):
    column = next(c for c in ml.get_feature_schema()['columns'] if c['tipo'] == 'numérica')
    real_features[column['nombre']] = column['max'] + 1
    assert_invalid(real_features, column['nombre'])


def test_codigo_nominal_no_visto(real_features):
    column = next(c for c in ml.get_feature_schema()['columns'] if c['tipo'] == 'nominal')
    real_features[column['nombre']] = max(column['valores_permitidos']) + 1
    assert_invalid(real_features, column['nombre'])


@pytest.mark.parametrize('value', [None, True, '18', 'texto', math.nan, math.inf, -math.inf])
def test_tipo_numerico_finito(real_features, value):
    real_features['Age at enrollment'] = value
    assert_invalid(real_features, 'Age at enrollment')


def test_bom_y_espacios_se_aceptan(real_features):
    baseline = ml.predict(real_features)
    normalized = {f' \ufeff{key} \ufeff ': value for key, value in real_features.items()}
    assert ml.predict(normalized)['probabilidades'] == baseline['probabilidades']


def test_duplicado_normalizado(real_features):
    real_features[' \ufeffAge at enrollment '] = real_features['Age at enrollment']
    assert_invalid(real_features, 'Age at enrollment')


def test_ejemplos_demo_son_filas_reales_de_test(trained_model):
    data = json.loads(trained_model.path.with_name('ejemplos_prediccion.json').read_text())
    assert {example['clase_real'] for example in data['ejemplos']} == set(CLASSES)
    for example in data['ejemplos']:
        index = example['indice_csv']
        assert index in trained_model.X_test.index
        assert example['features'] == trained_model.X_test.loc[index].to_dict()
        assert example['clase_real'] == trained_model.frame.loc[index, 'Target']
        result = ml.predict(example['features'])
        assert result['probabilidades'] == example['probabilidades']
        assert result['probabilidad_desercion'] == example['probabilidad_desercion']


@pytest.mark.parametrize(('probability', 'category'), [(0, 'baja'), (0.329, 'baja'),
    (0.33, 'media'), (0.659, 'media'), (0.66, 'alta'), (1, 'alta')])
def test_alineacion_clases_y_bordes_orientativos(real_features, trained_model, monkeypatch, probability, category):
    """PT_08 / AUD_09: el orden invertido de classes_ no invierte Dropout."""
    class Model:
        classes_ = np.array(['No_Dropout', 'Dropout'])

        def predict_proba(self, row):
            return np.array([[1 - probability, probability]])

        def predict(self, row):
            return np.array(['Dropout' if probability >= 0.5 else 'No_Dropout'])

    artifact = {**trained_model.artifact, 'pipeline': Model()}
    monkeypatch.setattr(ml, '_get_artifact', lambda: artifact)
    monkeypatch.setattr(ml.settings, 'ml_umbral_medio', 0.33)
    monkeypatch.setattr(ml.settings, 'ml_umbral_alto', 0.66)
    result = ml.predict(real_features)
    assert result['probabilidad_desercion'] == probability
    assert result['categoria_orientativa'] == category
