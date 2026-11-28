"""ML_02 · entrena y versiona un pipeline compatible con el backend de SIPDE."""
from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import joblib
import pandas as pd
import sklearn
from sklearn.model_selection import GridSearchCV

from ml.common import (
    ARTIFACTS_DIR, CLASSES, CONFIG_RECOMENDADA, DATA_PATH, FEATURE_SETS, LIMITATIONS, ML_DIR, SEED,
    SpanishArgumentParser,
    dataset_sha256, load_dataset, make_target, split_train_test, variable_schema, write_json,
)
from ml.training.workflow import classification_text, cv_summary, evaluate_model, fit_search

DEFAULT_MODEL_PATH = ARTIFACTS_DIR / "dropout_model.joblib"


def validate_version(value: str) -> str:
    """ML_02: restringe la versión para usarla también en nombres de archivo."""
    if not re.fullmatch(r"[0-9][A-Za-z0-9_.-]*", value):
        raise argparse.ArgumentTypeError("ML_02: versión inválida; usa dígitos, letras, puntos, guiones o guiones bajos.")
    return value


def parse_args() -> argparse.Namespace:
    """ML_02: conserva --csv/--out y agrega configuración reproducible."""
    parser = SpanishArgumentParser(description="ML_02 · Entrenamiento reproducible de SIPDE / INT_03")
    parser.add_argument("--csv", type=Path, default=DATA_PATH, help="CSV local con el esquema ML_01")
    parser.add_argument("--out", type=Path, default=DEFAULT_MODEL_PATH, help="Ruta del artefacto joblib")
    parser.add_argument("--modelo", choices=["logreg", "arbol"], default=CONFIG_RECOMENDADA["modelo"])
    parser.add_argument("--conjunto", choices=list(FEATURE_SETS), default=CONFIG_RECOMENDADA["conjunto"])
    parser.add_argument("--tarea", choices=["binaria", "multiclase"], default=CONFIG_RECOMENDADA["tarea"])
    parser.add_argument("--version", type=validate_version, default="1.0.0", help="Versión del modelo")
    return parser.parse_args()


def training_data_summary(frame: pd.DataFrame, X_train: pd.DataFrame,
                          X_test: pd.DataFrame, y_train: pd.Series, y_test: pd.Series) -> dict:
    """ML_02: registra tamaños y clases reales de las particiones."""
    return {
        "procedencia": "UCI / Instituto Politécnico de Portalegre, Portugal; 2008–2019",
        "filas_csv": len(frame), "columnas_csv": frame.shape[1],
        "variables_utilizadas": X_train.shape[1], "filas_train": len(X_train), "filas_test": len(X_test),
        "clases_train": {str(k): int(v) for k, v in y_train.value_counts().items()},
        "clases_test": {str(k): int(v) for k, v in y_test.value_counts().items()},
        "particion": "80/20 estratificada por objetivo; el estimador guardado se ajusta solo en train",
    }


def save_artifact(args: argparse.Namespace, frame: pd.DataFrame, search: GridSearchCV,
                  metrics: dict, cv: dict, data_summary: dict) -> None:
    """ML_02: guarda estimador y metadatos; no reajusta sobre el CSV completo."""
    pipeline = search.best_estimator_
    columns = FEATURE_SETS[args.conjunto].copy()
    artifact = {
        "pipeline": pipeline, "columns": columns,
        # PT_08 exige números JSON; los códigos del CSV también son numéricos.
        "numeric_columns": [c for c in columns if pd.api.types.is_numeric_dtype(frame[c])],
        "model_name": args.modelo, "version": args.version, "task": args.tarea,
        "feature_set": args.conjunto, "classes": pipeline.classes_.tolist(), "metrics": metrics,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "dataset_sha256": dataset_sha256(args.csv), "dataset_path": Path(os.path.relpath(args.csv.resolve(), ML_DIR.parent)).as_posix(),
        "sklearn_version": sklearn.__version__, "pandas_version": pd.__version__, "seed": SEED,
        "best_params": search.best_params_, "cv": cv, "training_data": data_summary,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, args.out)
    schema = {
        "id": "ML_02", "version": args.version, "model_name": args.modelo, "task": args.tarea,
        "feature_set": args.conjunto, "classes": artifact["classes"],
        "dataset_sha256": artifact["dataset_sha256"],
        "nota": "Rangos y códigos observados en el CSV local; no son un mapeo de códigos UCI ni límites universales. "
                "numeric_columns del artefacto conserva tipos de transporte del backend; "
                "el pipeline trata los códigos nominales con codificación de categorías.",
        "columns": variable_schema(frame, columns),
    }
    write_json(args.out.parent / "feature_schema.json", schema)
    card = {key: value for key, value in artifact.items() if key not in ("pipeline", "numeric_columns")}
    card.update({
        "id": "ML_02", "uso_previsto": "Apoyo experimental a tutorías mediante probabilidad de deserción observada; "
        "requiere validación local antes de uso operativo y revisión humana.",
        "horizonte": "Cierre del primer semestre" if args.conjunto == "temprano" else "Cierre del segundo semestre",
        "limitaciones": LIMITATIONS,
        "calibracion": "Se reporta Brier sin reajuste de calibración; los pesos balanceados pueden afectar probabilidades.",
        "criterio_seleccion": "F1-macro en CV estratificada solo sobre train; configuración según ML_00 y ML_02.",
        "variables_sensibles": [c for c in ("Gender", "Nacionality") if c in columns],
    })
    write_json(args.out.parent / "model_card.json", card)


def export_examples(args: argparse.Namespace, frame: pd.DataFrame, pipeline) -> None:
    """ACE_03: exporta una fila real de test por estado original, sin fabricar valores."""
    columns = FEATURE_SETS[args.conjunto]
    _, X_test, _, _ = split_train_test(frame[columns], make_target(frame["Target"], args.tarea))
    examples = []
    for real_class in CLASSES:
        index = next(i for i in X_test.index if frame.loc[i, "Target"] == real_class)
        row = X_test.loc[[index]]
        probabilities = {str(label): float(value) for label, value in
                         zip(pipeline.classes_, pipeline.predict_proba(row)[0])}
        examples.append({
            "id": f"ACE_03_{real_class}", "indice_csv": int(index),
            "features": row.iloc[0].to_dict(), "clase_real": real_class,
            "clase_objetivo": str(make_target(frame.loc[[index], "Target"], args.tarea).iloc[0]),
            "clase_predicha": str(pipeline.predict(row)[0]),
            "probabilidades": probabilities, "probabilidad_desercion": probabilities["Dropout"],
        })
    write_json(args.out.parent / "ejemplos_prediccion.json", {
        "id": "ACE_03", "version": args.version, "feature_set": args.conjunto,
        "task": args.tarea, "dataset_sha256": dataset_sha256(args.csv),
        "nota": "Filas reales de la partición test; indice_csv es el índice de datos desde cero, sin encabezado. "
                "Enrolled y Graduate se agrupan en No_Dropout para la tarea binaria.",
        "ejemplos": examples,
    })


def main() -> None:
    """ML_02: ejecuta búsqueda y prueba una vez, y persiste exactamente ese estimador."""
    args = parse_args()
    frame = load_dataset(args.csv)
    X = frame[FEATURE_SETS[args.conjunto]]
    y = make_target(frame["Target"], args.tarea)
    X_train, X_test, y_train, y_test = split_train_test(X, y)
    search = fit_search(args.modelo, X_train, y_train)
    cv = cv_summary(search, X_train, y_train)
    metrics, _ = evaluate_model(search.best_estimator_, X_test, y_test, args.tarea)
    data_summary = training_data_summary(frame, X_train, X_test, y_train, y_test)
    save_artifact(args, frame, search, metrics, cv, data_summary)
    export_examples(args, frame, search.best_estimator_)
    print(classification_text(metrics))
    print(f"ML_02: clases={metrics['classes']}; matriz de confusión={metrics['confusion_matrix']}")
    print(f"ML_02: hiperparámetros={search.best_params_}; CV={cv}")
    print(f"ML_02: artefacto {args.version} guardado en {args.out}")


if __name__ == "__main__":
    main()
