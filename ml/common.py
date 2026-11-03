"""INT_03 · utilidades compartidas de ML_01 y ML_02, sin fuga de información."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier

SEED = 42
np.random.seed(SEED)
ML_DIR = Path(__file__).resolve().parent
DATA_PATH = ML_DIR / "data" / "dataset.csv"
ARTIFACTS_DIR = ML_DIR / "artifacts"
REPORTS_DIR = ML_DIR / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"
METRICS_DIR = REPORTS_DIR / "metrics"
CONFIG_RECOMENDADA = {"modelo": "logreg", "conjunto": "temprano", "tarea": "binaria"}

FEATURES_INSCRIPCION = [
    "Marital status", "Application mode", "Application order", "Course",
    "Daytime/evening attendance", "Previous qualification", "Nacionality",
    "Mother's qualification", "Father's qualification", "Mother's occupation",
    "Father's occupation", "Displaced", "Educational special needs", "Debtor",
    "Tuition fees up to date", "Gender", "Scholarship holder", "Age at enrollment",
    "International",
]
FEATURES_SEM1 = [
    "Curricular units 1st sem (credited)", "Curricular units 1st sem (enrolled)",
    "Curricular units 1st sem (evaluations)", "Curricular units 1st sem (approved)",
    "Curricular units 1st sem (grade)", "Curricular units 1st sem (without evaluations)",
]
FEATURES_SEM2 = [
    "Curricular units 2nd sem (credited)", "Curricular units 2nd sem (enrolled)",
    "Curricular units 2nd sem (evaluations)", "Curricular units 2nd sem (approved)",
    "Curricular units 2nd sem (grade)", "Curricular units 2nd sem (without evaluations)",
]
FEATURES_MACRO = ["Unemployment rate", "Inflation rate", "GDP"]
ALL_FEATURES = FEATURES_INSCRIPCION + FEATURES_SEM1 + FEATURES_SEM2 + FEATURES_MACRO
FEATURE_SETS = {
    "temprano": FEATURES_INSCRIPCION + FEATURES_SEM1 + FEATURES_MACRO,
    "completo": ALL_FEATURES,
}
CATEGORICAL_CODES = [
    "Marital status", "Application mode", "Course", "Previous qualification",
    "Nacionality", "Mother's qualification", "Father's qualification",
    "Mother's occupation", "Father's occupation",
]
BINARY_COLUMNS = [
    "Daytime/evening attendance", "Displaced", "Educational special needs", "Debtor",
    "Tuition fees up to date", "Gender", "Scholarship holder", "International",
]
CLASSES = ["Dropout", "Enrolled", "Graduate"]
CLASS_LABELS = {"Dropout": "Deserción", "Enrolled": "En curso", "Graduate": "Graduación",
                "No_Dropout": "Sin deserción observada"}

# VAR_01…VAR_34 siguen el orden del CSV local; se conserva Nacionality.
DESCRIPTIONS = dict(zip(ALL_FEATURES, [
    "Estado civil", "Modalidad de acceso", "Orden de preferencia de la solicitud",
    "Carrera cursada", "Asistencia diurna o nocturna", "Titulación previa",
    "Nacionalidad", "Escolaridad materna", "Escolaridad paterna", "Ocupación materna",
    "Ocupación paterna", "Desplazamiento del domicilio habitual", "Necesidades educativas especiales",
    "Existencia de adeudos", "Colegiatura al corriente", "Género registrado",
    "Beneficiario de beca", "Edad al inscribirse", "Condición de estudiante internacional",
    "Unidades reconocidas, primer semestre", "Unidades inscritas, primer semestre",
    "Evaluaciones realizadas, primer semestre", "Unidades aprobadas, primer semestre",
    "Promedio de unidades aprobadas, primer semestre", "Unidades sin evaluación, primer semestre",
    "Unidades reconocidas, segundo semestre", "Unidades inscritas, segundo semestre",
    "Evaluaciones realizadas, segundo semestre", "Unidades aprobadas, segundo semestre",
    "Promedio de unidades aprobadas, segundo semestre", "Unidades sin evaluación, segundo semestre",
    "Tasa de desempleo", "Tasa de inflación", "Variación del producto interno bruto",
], strict=True))
VARIABLE_IDS = {column: f"VAR_{i:02d}" for i, column in enumerate(ALL_FEATURES, 1)}
LIMITATIONS = (
    "Datos del Instituto Politécnico de Portalegre, Portugal, de 2008–2019; no representan ESCOM. "
    "No hay horas de trabajo ni calificaciones por materia. El segundo semestre implica predicción tardía. "
    "Enrolled indica continuidad de estudios al observar el objetivo, no riesgo intermedio; "
    "No_Dropout tampoco garantiza graduación futura. Gender y Nacionality son variables sensibles: "
    "su inclusión puede reproducir sesgos y requiere evaluación por subgrupos y validación local antes de uso real. "
    "Estas probabilidades no son un diagnóstico ni justifican decisiones punitivas. "
    "Los estados de beca, deuda y colegiatura se agrupan con inscripción según el diseño solicitado, "
    "pero el CSV no incluye sus fechas de captura: debe verificarse su disponibilidad histórica."
)


class SpanishArgumentParser(argparse.ArgumentParser):
    """INT_03: presenta también la ayuda estándar de los comandos en español."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(add_help=False, **kwargs)
        self.add_argument("-h", "--help", action="help", help="Muestra esta ayuda y termina")

    def format_help(self) -> str:
        """INT_03: traduce los encabezados que agrega argparse."""
        return super().format_help().replace("usage:", "uso:").replace("options:", "Opciones:")


def load_dataset(path: str | Path = DATA_PATH) -> pd.DataFrame:
    """ML_01: valida el esquema local y rechaza objetivos ausentes o desconocidos."""
    frame = pd.read_csv(path, encoding="utf-8-sig")
    frame.columns = frame.columns.str.strip()
    expected = ALL_FEATURES + ["Target"]
    missing = sorted(set(expected) - set(frame.columns))
    extra = sorted(set(frame.columns) - set(expected))
    if missing or extra or frame.columns.duplicated().any():
        raise ValueError(f"ML_01: esquema inválido. Faltantes: {missing}; adicionales: {extra}; "
                         f"nombres duplicados: {frame.columns[frame.columns.duplicated()].tolist()}.")
    if frame.empty or frame["Target"].isna().any() or not frame["Target"].isin(CLASSES).all():
        raise ValueError("ML_01: Target debe contener únicamente Dropout, Enrolled y Graduate, sin nulos.")
    if set(frame["Target"]) != set(CLASSES):
        raise ValueError("ML_01: se requieren las tres clases en el dataset.")
    for column in ALL_FEATURES:
        if not pd.api.types.is_numeric_dtype(frame[column]):
            raise ValueError(f"ML_01: la variable {column!r} debe ser numérica.")
        if np.isinf(frame[column].to_numpy(dtype=float)).any():
            raise ValueError(f"ML_01: la variable {column!r} contiene valores infinitos.")
    return frame.loc[:, expected]


def make_target(y: pd.Series, task: str) -> pd.Series:
    """ML_02: Enrolled es un estado observado, no una escala de riesgo intermedio.

    La tarea binaria agrupa Enrolled y Graduate como ausencia de deserción observada;
    no supone que toda persona todavía inscrita terminará sus estudios.
    """
    if task == "multiclase":
        return y.copy()
    if task == "binaria":
        return y.where(y == "Dropout", "No_Dropout")
    raise ValueError(f"ML_02: tarea desconocida: {task!r}.")


def build_preprocessor(columns: Sequence[str]) -> ColumnTransformer:
    """ML_02: ajusta imputación, escalado y categorías dentro de cada partición."""
    categorical = [column for column in columns if column in CATEGORICAL_CODES]
    numeric = [column for column in columns if column not in CATEGORICAL_CODES]
    return ColumnTransformer([
        ("num", Pipeline([("imputer", SimpleImputer(strategy="median")),
                           ("scaler", StandardScaler())]), numeric),
        ("cat", Pipeline([("imputer", SimpleImputer(strategy="most_frequent")),
                           ("encoder", OneHotEncoder(handle_unknown="ignore"))]), categorical),
    ])


def build_pipeline(model_name: str, columns: Sequence[str]) -> Pipeline:
    """ML_02: construye un estimador completo compatible con el servicio actual."""
    if model_name == "logreg":
        classifier = LogisticRegression(max_iter=3000, class_weight="balanced", random_state=SEED)
    elif model_name == "arbol":
        classifier = DecisionTreeClassifier(class_weight="balanced", random_state=SEED)
    else:
        raise ValueError(f"ML_02: modelo desconocido: {model_name!r}.")
    return Pipeline([("preprocess", build_preprocessor(columns)), ("classifier", classifier)])


def split_train_test(X: pd.DataFrame, y: pd.Series) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """ML_02: reserva la prueba antes de cualquier ajuste."""
    return train_test_split(X, y, test_size=0.2, stratify=y, random_state=SEED)


def dataset_sha256(path: str | Path = DATA_PATH) -> str:
    """ML_01: identifica exactamente los bytes del archivo de entrada."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def variable_type(column: str) -> str:
    """ML_01: distingue códigos nominales, indicadores y magnitudes."""
    if column in CATEGORICAL_CODES:
        return "nominal"
    return "binaria" if column in BINARY_COLUMNS else "numérica"


def variable_moment(column: str) -> str:
    """ML_01: asigna el momento de observación previsto."""
    if column in FEATURES_SEM1:
        return "1er semestre"
    if column in FEATURES_SEM2:
        return "2º semestre"
    return "macroeconómica" if column in FEATURES_MACRO else "inscripción"


def variable_schema(frame: pd.DataFrame, columns: Sequence[str]) -> list[dict[str, Any]]:
    """ML_01: genera metadatos a partir del CSV, sin inventar códigos de categorías."""
    rows = []
    for column in columns:
        observed = frame[column].dropna()
        row = {
            "nombre": column, "id": VARIABLE_IDS[column], "descripcion_es": DESCRIPTIONS[column],
            "tipo": variable_type(column), "momento": variable_moment(column),
            "min": float(observed.min()) if not observed.empty else None,
            "max": float(observed.max()) if not observed.empty else None,
            "ejemplo": float(observed.iloc[0]) if not observed.empty else None,
        }
        if column in CATEGORICAL_CODES:
            row["valores_permitidos"] = sorted(observed.unique().tolist())
        rows.append(row)
    return rows


def write_json(path: Path, value: Any) -> None:
    """INT_03: escribe JSON UTF-8 estricto y legible."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
                    encoding="utf-8")
