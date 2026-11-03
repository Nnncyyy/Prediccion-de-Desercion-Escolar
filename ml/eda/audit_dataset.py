"""ML_01 · audita el CSV local y regenera perfil, diccionario, figuras y reporte."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd

from ml.common import (
    ALL_FEATURES, CLASS_LABELS, CLASSES, DATA_PATH, DESCRIPTIONS, FEATURES_SEM1,
    FEATURE_SETS, LIMITATIONS, ML_DIR, REPORTS_DIR, VARIABLE_IDS, dataset_sha256,
    load_dataset, variable_schema, write_json,
)
from ml.plotting import plt, save_figure

UCI_URL = "https://archive.ics.uci.edu/dataset/697/predict+students+dropout+and+academic+success"
PAPER_URL = "https://doi.org/10.3390/data7110146"


def build_profile(frame: pd.DataFrame) -> dict:
    """ML_01: calcula calidad y estadística descriptiva sin alterar observaciones."""
    counts = frame["Target"].value_counts().reindex(CLASSES)
    statistics = {}
    for column in frame.columns:
        series = frame[column]
        statistics[column] = (
            {"min": float(series.min()), "max": float(series.max()), "media": float(series.mean())}
            if pd.api.types.is_numeric_dtype(series) and series.notna().any()
            else {"min": None, "max": None, "media": None}
        )
    return {
        "id": "ML_01", "filas": len(frame), "columnas": len(frame.columns),
        "variables_predictoras": len(ALL_FEATURES),
        "nulos_por_columna": frame.isna().sum().astype(int).to_dict(),
        "duplicados": int(frame.duplicated().sum()),
        "tipos": frame.dtypes.astype(str).to_dict(), "estadisticas": statistics,
        "clases": {label: {"conteo": int(counts[label]), "porcentaje": float(100 * counts[label] / len(frame))}
                   for label in CLASSES},
        "sha256": dataset_sha256(), "pandas_version": pd.__version__,
        "nota": "La media de códigos nominales no tiene interpretación ordinal; Target no tiene media numérica.",
    }


def write_dictionary(frame: pd.DataFrame) -> pd.DataFrame:
    """TAB_ML_01: documenta los códigos observados sin reinterpretar su numeración."""
    rows = []
    for metadata in variable_schema(frame, ALL_FEATURES):
        column = metadata["nombre"]
        rows.append({
            "id": metadata["id"], "columna": column, "descripcion_es": metadata["descripcion_es"],
            "tipo": metadata["tipo"], "momento": metadata["momento"],
            "min": metadata["min"], "max": metadata["max"],
            "grupo_modelo": "temprano y completo" if column in FEATURE_SETS["temprano"] else "completo",
        })
    dictionary = pd.DataFrame(rows)
    dictionary.to_csv(ML_DIR / "data" / "diccionario_variables.csv", index=False, encoding="utf-8")
    return dictionary


def class_figures(frame: pd.DataFrame, profile: dict) -> dict:
    """FIG_ML_01…03: resume clases, aprobación y edad con división segura."""
    labels = [CLASS_LABELS[label] for label in CLASSES]
    counts = [profile["clases"][label]["conteo"] for label in CLASSES]
    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(labels, counts)
    for bar, label in zip(bars, CLASSES):
        values = profile["clases"][label]
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                f"{values['conteo']} ({values['porcentaje']:.2f}%)", ha="center", va="bottom")
    ax.set(title="FIG_ML_01 · Distribución de clases", xlabel="Estado académico observado", ylabel="Estudiantes")
    ax.set_ylim(0, max(counts) * 1.15)
    save_figure(fig, "FIG_ML_01_distribucion_clases.png")

    enrolled = frame[FEATURES_SEM1[1]]
    ratio = frame[FEATURES_SEM1[3]].div(enrolled.where(enrolled != 0))
    findings = {"sin_unidades_inscritas": int((enrolled == 0).sum()), "clases": {}}
    for values, title, ylabel, filename in [
        (ratio, "FIG_ML_02 · Tasa de aprobación del primer semestre", "Unidades aprobadas / inscritas",
         "FIG_ML_02_tasa_aprobacion_sem1_por_clase.png"),
        (frame["Age at enrollment"], "FIG_ML_03 · Edad al inscribirse por clase", "Edad (años)",
         "FIG_ML_03_edad_por_clase.png"),
    ]:
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.boxplot([values[frame["Target"] == label].dropna() for label in CLASSES], tick_labels=labels)
        ax.set(title=title, xlabel="Estado académico observado", ylabel=ylabel)
        save_figure(fig, filename)
    for label in CLASSES:
        mask = frame["Target"] == label
        findings["clases"][label] = {"mediana_tasa": float(ratio[mask].median()),
                                      "mediana_edad": float(frame.loc[mask, "Age at enrollment"].median())}
    return findings


def association_figures(frame: pd.DataFrame) -> tuple[pd.Series, list[dict]]:
    """FIG_ML_04…05: muestra asociaciones descriptivas, sin interpretación causal."""
    indicator = frame["Target"].eq("Dropout").astype(int)
    correlations = frame[ALL_FEATURES].corrwith(indicator).dropna()
    top = correlations.loc[correlations.abs().sort_values(ascending=False).head(15).index]
    fig, ax = plt.subplots(figsize=(11, 8))
    ordered = top.iloc[::-1]
    ax.barh([f"{VARIABLE_IDS[c]} · {DESCRIPTIONS[c]}" for c in ordered.index], ordered.values)
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set(title="FIG_ML_04 · Asociaciones de Pearson con deserción",
           xlabel="Correlación con el indicador de deserción", ylabel="Variable")
    save_figure(fig, "FIG_ML_04_correlacion_dropout.png")

    fig, axes = plt.subplots(1, 2, figsize=(10, 5), sharey=True)
    rates = []
    for ax, column, title in zip(axes, ["Tuition fees up to date", "Scholarship holder"],
                                 ["Colegiatura al corriente", "Beneficiario de beca"]):
        grouped = frame.assign(desercion=indicator).groupby(column)["desercion"].agg(["mean", "size", "sum"])
        bars = ax.bar(["Sí" if code == 1 else "No" for code in grouped.index], 100 * grouped["mean"])
        for bar, (code, row) in zip(bars, grouped.iterrows()):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                    f"{100 * row['mean']:.2f}%\nn={int(row['size'])}", ha="center", va="bottom")
            rates.append({"columna": column, "codigo": int(code), "n": int(row["size"]),
                          "dropout": int(row["sum"]), "porcentaje": float(100 * row["mean"])})
        ax.set(title=title, xlabel="Indicador registrado", ylim=(0, 100))
    axes[0].set_ylabel("Estudiantes con deserción (%)")
    fig.suptitle("FIG_ML_05 · Colegiatura, beca y deserción observada")
    save_figure(fig, "FIG_ML_05_colegiatura_beca_vs_dropout.png")
    return top, rates


def write_report(profile: dict, dictionary: pd.DataFrame, findings: dict,
                 correlations: pd.Series, rates: list[dict]) -> None:
    """ML_01: genera cada cifra del informe a partir de los cálculos de auditoría."""
    lines = [
        "# ML_01 · Auditoría del dataset · SIPDE / INT_03", "",
        f"Se analizaron {profile['filas']} filas, {profile['columnas']} columnas y "
        f"{profile['variables_predictoras']} variables predictoras. pandas: {profile['pandas_version']}.",
        f"SHA-256 del CSV: `{profile['sha256']}`.", "",
        "## Calidad de datos", "",
        f"Nulos totales: {sum(profile['nulos_por_columna'].values())}; filas duplicadas completas: {profile['duplicados']}. "
        "Se conserva el CSV original. La lectura elimina el BOM UTF-8 y espacios exteriores de los encabezados; "
        "no imputa ni modifica Target. Los rangos observados no equivalen a límites clínicos ni validaciones universales.",
        "El perfil JSON contiene nulos, tipos y mínimo/máximo/media de cada variable. "
        "La media de códigos nominales carece de interpretación ordinal; para Target las estadísticas numéricas son nulas.", "",
        "### TAB_ML_01 · Variables por momento de observación", "",
        "| Momento | Cantidad | Conjuntos |", "|---|---:|---|",
    ]
    for moment, group in dictionary.groupby("momento", sort=False):
        lines.append(f"| {moment} | {len(group)} | {', '.join(group['grupo_modelo'].unique())} |")
    lines += ["", "El diccionario contiene una fila por VAR_xx. Detalle de rangos observados:", "",
              "| ID | Variable | Tipo | Mínimo | Máximo |", "|---|---|---|---:|---:|"]
    for row in dictionary.to_dict("records"):
        lines.append(f"| {row['id']} | {row['descripcion_es']} | {row['tipo']} | {row['min']:g} | {row['max']:g} |")
    lines += ["", "## Desbalance y hallazgos", ""]
    for label, values in profile["clases"].items():
        lines.append(f"- FIG_ML_01: {label} ({CLASS_LABELS[label]}): {values['conteo']} estudiantes "
                     f"({values['porcentaje']:.4f}%).")
    counts = [row["conteo"] for row in profile["clases"].values()]
    lines += [f"\nRazón entre clase mayoritaria y minoritaria: {max(counts) / min(counts):.4f}. "
              "Se usan pesos balanceados y F1-macro para no ocultar clases pequeñas.", ""]
    for label, values in findings["clases"].items():
        lines.append(f"- FIG_ML_02 / FIG_ML_03, {label}: mediana de aprobación {values['mediana_tasa']:.4f}; "
                     f"mediana de edad {values['mediana_edad']:.2f} años.")
    lines += [f"\nFIG_ML_02 excluye de la razón {findings['sin_unidades_inscritas']} casos sin unidades inscritas; "
              "se conservan en el dataset y en el entrenamiento. No se sustituye la razón indefinida por cero.", ""]
    for column, correlation in correlations.head(3).items():
        lines.append(f"- FIG_ML_04: {VARIABLE_IDS[column]} ({DESCRIPTIONS[column]}), r={correlation:.6f}.")
    lines += ["\nEstas correlaciones son exploratorias, no causales. "
              "Pearson sobre códigos nominales depende de su numeración arbitraria; el pipeline los codifica por separado.", ""]
    for row in rates:
        lines.append(f"- FIG_ML_05: {DESCRIPTIONS[row['columna']]}, indicador {row['codigo']}: "
                     f"{row['dropout']}/{row['n']} casos de deserción ({row['porcentaje']:.4f}%).")
    lines += ["", "## Limitaciones y procedencia", "", LIMITATIONS,
              "La auditoría exploratoria usa todo el CSV para describirlo; las rejillas y conjuntos se fijan "
              "en ML_00 y no se seleccionan por asociaciones del test.",
              "La captura transversal no permite validar cronológicamente el horizonte ni identificar reingresos. "
              "No se asignan significados de categorías individuales sin un mapeo verificado.",
              f"ML_01 · Nota de procedencia: el CSV local tiene {profile['variables_predictoras']} predictores, "
              f"mientras la ficha actual de [UCI]({UCI_URL}) reporta 36 e incluye "
              "`Previous qualification (grade)` y `Admission grade`, ausentes aquí. "
              "Por eso se fija el SHA-256 del archivo usado; no se añaden variables ausentes. El [descriptor de Realinho et al.]"
              f"({PAPER_URL}) documenta la procedencia y los momentos de observación.", ""]
    for name in ["FIG_ML_01_distribucion_clases", "FIG_ML_02_tasa_aprobacion_sem1_por_clase",
                 "FIG_ML_03_edad_por_clase", "FIG_ML_04_correlacion_dropout", "FIG_ML_05_colegiatura_beca_vs_dropout"]:
        lines += [f"![{name}](figures/{name}.png)", ""]
    (REPORTS_DIR / "ML_01_auditoria_dataset.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    """ML_01: sobrescribe todos los entregables de la auditoría."""
    frame = load_dataset(DATA_PATH)
    profile = build_profile(frame)
    write_json(REPORTS_DIR / "dataset_profile.json", profile)
    dictionary = write_dictionary(frame)
    findings = class_figures(frame, profile)
    correlations, rates = association_figures(frame)
    write_report(profile, dictionary, findings, correlations, rates)
    print(f"ML_01: {profile['filas']} filas, {profile['columnas']} columnas; "
          f"nulos={sum(profile['nulos_por_columna'].values())}; duplicados={profile['duplicados']}.")
    for label, values in profile["clases"].items():
        print(f"ML_01: {label}: {values['conteo']} ({values['porcentaje']:.6f}%).")
    print(f"ML_01: SHA-256 {profile['sha256']}")


if __name__ == "__main__":
    main()
