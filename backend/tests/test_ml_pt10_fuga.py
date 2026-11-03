"""PT_10 · RF_08/RNF_06: ausencia de fuga y reproducibilidad de INT_03.

Objetivo: verificar partición estratificada, ajuste solo en train y semilla fija.
Resultado esperado: test disjunto, escalador con medias de train y métricas idénticas.
"""
from copy import deepcopy
import sys

import numpy as np

from ml.common import CONFIG_RECOMENDADA, FEATURES_SEM2, SEED
from ml.training.evaluate import metric_differences
from ml.training.workflow import evaluate_model, fit_search


def test_particion_disjunta_y_estratificada(trained_model):
    model = trained_model
    assert set(model.X_train.index).isdisjoint(model.X_test.index)
    assert set(model.X_train.index) | set(model.X_test.index) == set(model.frame.index)
    assert abs((model.y_train == 'Dropout').mean() - (model.y_test == 'Dropout').mean()) < 0.01


def test_escalador_ajustado_solo_en_train(trained_model):
    preprocess = trained_model.artifact['pipeline'].named_steps['preprocess']
    columns = preprocess.transformers_[0][2]
    scaler = preprocess.named_transformers_['num'].named_steps['scaler']
    np.testing.assert_allclose(scaler.mean_, trained_model.X_train[columns].mean(), rtol=0, atol=1e-12)
    assert not np.allclose(scaler.mean_, trained_model.frame[columns].mean(), rtol=0, atol=1e-12)
    assert scaler.n_samples_seen_ == len(trained_model.X_train)


def test_temprano_excluye_segundo_semestre(trained_model):
    assert trained_model.artifact['feature_set'] == 'temprano'
    assert not set(trained_model.artifact['columns']) & set(FEATURES_SEM2)
    assert not any('2nd sem' in c for c in trained_model.artifact['columns'])


def test_dos_entrenamientos_reproducibles(trained_model):
    model = trained_model
    repeated = fit_search(CONFIG_RECOMENDADA['modelo'], model.X_train, model.y_train)
    metrics, _ = evaluate_model(repeated.best_estimator_, model.X_test, model.y_test,
                                CONFIG_RECOMENDADA['tarea'])
    assert metrics == model.metrics
    assert repeated.best_params_ == model.artifact['best_params']
    assert model.artifact['seed'] == SEED
    assert 'matplotlib' not in sys.modules


def test_evaluacion_detecta_alteracion(trained_model):
    saved = deepcopy(trained_model.metrics)
    assert not metric_differences(saved, trained_model.metrics)
    saved['f1_macro'] += 1e-6
    assert any('f1_macro' in field for field in metric_differences(saved, trained_model.metrics))
