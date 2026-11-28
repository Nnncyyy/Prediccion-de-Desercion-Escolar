"""PT_09 · RF_08: desempeño mínimo en la prueba reservada del modelo INT_03.

Objetivo: comprobar F1-macro, recall de Dropout y matriz de confusión real.
Resultado esperado: métricas sobre los mínimos fijados y matriz consistente con test.
"""
import numpy as np

# PT_09: ejecución EXP_02 (SEED=42, scikit-learn 1.9.1):
# F1-macro observado 0.8238642224065571; recall Dropout observado 0.7746478873239436.
# Mínimos fijados redondeando hacia abajo a múltiplos de 0.05, sin consultar durante la prueba.
PT_09_MIN_F1_MACRO = 0.80
PT_09_MIN_RECALL_DROPOUT = 0.75


def test_desempeno_minimo(trained_model):
    metrics = trained_model.metrics
    assert metrics['f1_macro'] >= PT_09_MIN_F1_MACRO
    assert metrics['recall_dropout'] >= PT_09_MIN_RECALL_DROPOUT


def test_matriz_de_confusion(trained_model):
    metrics = trained_model.metrics
    matrix = np.asarray(metrics['confusion_matrix'])
    classes = trained_model.artifact['pipeline'].classes_.tolist()
    assert metrics['classes'] == classes
    assert matrix.shape == (len(classes), len(classes))
    assert matrix.sum() == len(trained_model.y_test) == metrics['n_test']
    assert matrix.sum(axis=1).tolist() == [int((trained_model.y_test == c).sum()) for c in classes]
