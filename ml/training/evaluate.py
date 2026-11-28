"""ML_02 · PT_10: reproduce la evaluación del artefacto sin volver a entrenar."""
from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import joblib

from ml.common import (
    METRICS_DIR, ML_DIR, SEED, SpanishArgumentParser, dataset_sha256, load_dataset, make_target,
    split_train_test, write_json,
)
from ml.training.train import DEFAULT_MODEL_PATH, validate_version
from ml.training.workflow import classification_text, evaluate_model

TOLERANCE = 1e-9


def metric_differences(saved: Any, actual: Any, path: str = "metrics") -> list[str]:
    """PT_10: compara también clases, matrices, soportes y métricas por clase."""
    if isinstance(saved, dict) and isinstance(actual, dict):
        differences = []
        if saved.keys() != actual.keys():
            differences.append(f"{path}: llaves diferentes")
        for key in saved.keys() & actual.keys():
            differences.extend(metric_differences(saved[key], actual[key], f"{path}.{key}"))
        return differences
    if isinstance(saved, list) and isinstance(actual, list):
        if len(saved) != len(actual):
            return [f"{path}: longitud diferente"]
        return [difference for i, (left, right) in enumerate(zip(saved, actual))
                for difference in metric_differences(left, right, f"{path}[{i}]")]
    if isinstance(saved, (int, float)) and isinstance(actual, (int, float)):
        return [] if math.isclose(saved, actual, abs_tol=TOLERANCE, rel_tol=0) else [f"{path}: {saved} != {actual}"]
    return [] if saved == actual else [f"{path}: {saved!r} != {actual!r}"]


def main() -> int:
    """PT_10: falla si cambian bytes del CSV, semilla o cualquier métrica guardada."""
    parser = SpanishArgumentParser(description="ML_02 · PT_10 · Verificación reproducible del artefacto")
    parser.add_argument("--artifact", type=Path, default=DEFAULT_MODEL_PATH, help="Artefacto joblib local confiable")
    parser.add_argument("--csv", type=Path, help="CSV; por defecto usa la ruta registrada en el artefacto")
    args = parser.parse_args()
    artifact = joblib.load(args.artifact)
    version = validate_version(artifact["version"])
    csv_path = args.csv or Path(artifact["dataset_path"])
    if args.csv is None and not csv_path.is_absolute():
        csv_path = ML_DIR.parent / csv_path
    frame = load_dataset(csv_path)
    X = frame[artifact["columns"]]
    y = make_target(frame["Target"], artifact["task"])
    _, X_test, _, y_test = split_train_test(X, y)
    metrics, _ = evaluate_model(artifact["pipeline"], X_test, y_test, artifact["task"])
    differences = metric_differences(artifact["metrics"], metrics)
    if artifact["dataset_sha256"] != dataset_sha256(csv_path):
        differences.append("ML_01: SHA-256 del CSV diferente al entrenamiento")
    if artifact["seed"] != SEED:
        differences.append("ML_02: la semilla registrada no coincide con el protocolo")
    result = {"id": "PT_10", "version": version, "metrics": metrics,
              "dataset_sha256": dataset_sha256(csv_path), "tolerance": TOLERANCE,
              "matches_saved_metrics": not differences, "differences": differences}
    output = METRICS_DIR / f"evaluacion_{version}.json"
    write_json(output, result)
    print(classification_text(metrics))
    print(f"PT_10: coincidencia={not differences}; tolerancia={TOLERANCE}; salida={output}")
    for difference in differences:
        print(difference, file=sys.stderr)
    return 1 if differences else 0


if __name__ == "__main__":
    raise SystemExit(main())
