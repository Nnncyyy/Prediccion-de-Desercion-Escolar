"""INT_03 · controles rápidos propios de selección y tolerancia numérica."""
from copy import deepcopy

from sklearn.metrics import f1_score

from ml.training.evaluate import metric_differences
from ml.training.workflow import select_experiment


def test_seleccion_independiente_test() -> None:
    """INT_03: aplica margen del árbol y desempate de recall sin consultar test."""
    observed = ["Dropout", "Dropout", "No_Dropout", "No_Dropout"]
    score = f1_score(observed, observed, average="macro")
    candidates = [
        {"id": "EXP_02", "model_name": "logreg", "cv": {"f1_macro_mean": score, "recall_dropout_mean": score}},
        {"id": "EXP_06", "model_name": "arbol", "cv": {"f1_macro_mean": score - 0.01, "recall_dropout_mean": score}},
    ]
    assert select_experiment(candidates)["id"] == "EXP_06"
    candidates[1]["cv"]["f1_macro_mean"] -= 0.01
    assert select_experiment(candidates)["id"] == "EXP_02"
    candidates[1]["cv"]["f1_macro_mean"] = score
    candidates.append(deepcopy(candidates[1]))
    candidates[-1]["id"] = "EXP_08"
    candidates[1]["cv"]["recall_dropout_mean"] /= 2
    assert select_experiment(candidates)["id"] == "EXP_08"


def test_tolerancia_de_metricas():
    """INT_03: detecta alteraciones mayores a la tolerancia documentada."""
    observed = ["Dropout", "No_Dropout"]
    score = float(f1_score(observed, observed, average="macro"))
    original = {"f1_macro": score}
    assert not metric_differences(original, deepcopy(original))
    assert metric_differences(original, {"f1_macro": score - 1e-6})
    assert not metric_differences(original, {"f1_macro": score - 1e-10})
