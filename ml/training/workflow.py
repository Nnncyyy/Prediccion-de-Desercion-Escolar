"""ML_02 · búsqueda, evaluación y selección compartidas por los comandos ML."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score, balanced_accuracy_score, brier_score_loss, classification_report,
    confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score,
)
from sklearn.model_selection import GridSearchCV, StratifiedKFold, cross_val_score
from sklearn.pipeline import Pipeline
from threadpoolctl import threadpool_limits

from ml.common import SEED, build_pipeline

PARAM_GRIDS = {
    "logreg": {"classifier__C": [0.01, 0.1, 1, 10]},
    "arbol": {"classifier__max_depth": [3, 4, 5, 6, 8],
              "classifier__min_samples_leaf": [1, 10, 30]},
}


def make_cv() -> StratifiedKFold:
    """ML_02: conserva los mismos pliegues en cada búsqueda de una tarea."""
    return StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)


def fit_search(model_name: str, X: pd.DataFrame, y: pd.Series) -> GridSearchCV:
    """ML_02: busca hiperparámetros exclusivamente con las filas de entrenamiento."""
    search = GridSearchCV(build_pipeline(model_name, X.columns), PARAM_GRIDS[model_name],
                          scoring="f1_macro", cv=make_cv(), n_jobs=1, error_score="raise")
    # Un hilo evita sobrecoste de BLAS y reduce variación entre ejecuciones.
    with threadpool_limits(limits=1):
        search.fit(X, y)
    return search


def score_dropout_recall(estimator: Pipeline, X: pd.DataFrame, y: pd.Series) -> float:
    """ML_02: calcula recall de la etiqueta Dropout también con objetivos textuales."""
    return float(recall_score(y, estimator.predict(X), labels=["Dropout"],
                              average="macro", zero_division=0))


def cv_summary(search: GridSearchCV, X: pd.DataFrame, y: pd.Series) -> dict[str, float]:
    """ML_02: mide recall en CV para desempatar; no consulta la prueba."""
    with threadpool_limits(limits=1):
        recall = cross_val_score(search.best_estimator_, X, y, cv=make_cv(), scoring=score_dropout_recall,
                                 error_score="raise")
    return {
        "f1_macro_mean": float(search.best_score_),
        "f1_macro_std": float(search.cv_results_["std_test_score"][search.best_index_]),
        "recall_dropout_mean": float(recall.mean()),
    }


def evaluate_model(pipeline: Pipeline, X: pd.DataFrame, y: pd.Series,
                   task: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """ML_02: obtiene una sola predicción de prueba y reutiliza sus probabilidades."""
    with threadpool_limits(limits=1):
        predicted = pipeline.predict(X)
        probabilities = pipeline.predict_proba(X)
    classes = pipeline.classes_.tolist()
    dropout_probability = probabilities[:, classes.index("Dropout")]
    observed = (y == "Dropout").to_numpy(dtype=int)
    auc = (roc_auc_score(observed, dropout_probability) if task == "binaria" else
           roc_auc_score(y, probabilities, labels=classes, multi_class="ovr", average="macro"))
    metrics = {
        "accuracy": float(accuracy_score(y, predicted)),
        "balanced_accuracy": float(balanced_accuracy_score(y, predicted)),
        "f1_macro": float(f1_score(y, predicted, average="macro", zero_division=0)),
        "recall_dropout": float(recall_score(y, predicted, labels=["Dropout"], average="macro", zero_division=0)),
        "precision_dropout": float(precision_score(y, predicted, labels=["Dropout"], average="macro", zero_division=0)),
        "f1_dropout": float(f1_score(y, predicted, labels=["Dropout"], average="macro", zero_division=0)),
        "roc_auc": float(auc),
        "brier_dropout": float(brier_score_loss(observed, dropout_probability)),
        "confusion_matrix": confusion_matrix(y, predicted, labels=classes).tolist(),
        "classes": classes,
        "n_test": len(y),
        "classification_report": classification_report(y, predicted, labels=classes,
                                                         output_dict=True, zero_division=0),
    }
    predictions = {"observed_dropout": observed, "dropout_probability": dropout_probability,
                   "predicted": predicted}
    return metrics, predictions


def select_experiment(records: list[dict[str, Any]]) -> dict[str, Any]:
    """ML_02: máximo F1 de CV, empate por recall, árbol a distancia máxima 0.01."""
    def key(record: dict[str, Any]) -> tuple[float, float]:
        return record["cv"]["f1_macro_mean"], record["cv"]["recall_dropout_mean"]

    best = max(records, key=key)
    trees = [record for record in records if record["model_name"] == "arbol"
             and best["cv"]["f1_macro_mean"] - record["cv"]["f1_macro_mean"] <= 0.01 + 1e-12]
    return max(trees, key=key) if trees else best


def classification_text(metrics: dict[str, Any]) -> str:
    """ML_02: presenta el reporte de clasificación en español."""
    lines = ["ML_02 · Reporte de clasificación", "Clase | Precisión | Sensibilidad | F1 | Soporte"]
    for label in metrics["classes"]:
        row = metrics["classification_report"][label]
        lines.append(f"{label} | {row['precision']:.6f} | {row['recall']:.6f} | "
                     f"{row['f1-score']:.6f} | {int(row['support'])}")
    lines.append(f"F1-macro: {metrics['f1_macro']:.9f}; exactitud: {metrics['accuracy']:.9f}; "
                 f"exactitud balanceada: {metrics['balanced_accuracy']:.9f}")
    lines.append(f"Recall de Dropout: {metrics['recall_dropout']:.9f}; "
                 f"precisión de Dropout: {metrics['precision_dropout']:.9f}; "
                 f"ROC-AUC: {metrics['roc_auc']:.9f}; Brier: {metrics['brier_dropout']:.9f}")
    return "\n".join(lines)
