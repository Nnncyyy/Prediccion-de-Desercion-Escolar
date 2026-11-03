"""ML_02 · referencia trivial y ocho experimentos en orden modelo → conjunto → tarea; selección por CV."""
from __future__ import annotations

import itertools
import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
import pandas as pd
import sklearn
from sklearn.calibration import calibration_curve
from sklearn.dummy import DummyClassifier
from sklearn.model_selection import GridSearchCV
from sklearn.metrics import ConfusionMatrixDisplay
from sklearn.pipeline import Pipeline
from sklearn.tree import plot_tree

from ml.common import (
    CLASS_LABELS, DATA_PATH, DESCRIPTIONS, FEATURE_SETS, LIMITATIONS, METRICS_DIR,
    REPORTS_DIR, SEED, VARIABLE_IDS, dataset_sha256, load_dataset, make_target,
    split_train_test, write_json,
)
from ml.plotting import plt, save_figure
from ml.training.workflow import cv_summary, evaluate_model, fit_search, make_cv, select_experiment

# EXP_01…08: logreg antes de arbol; temprano antes de completo; multiclase antes de binaria.
EXPERIMENT_ORDER = list(itertools.product(
    ("logreg", "arbol"), ("temprano", "completo"), ("multiclase", "binaria"),
))


def run_experiment(frame: pd.DataFrame, identifier: str, model_name: str,
                   feature_set: str, task: str) -> tuple[dict, Pipeline, dict]:
    """ML_02: ajusta en train y obtiene una sola evaluación de prueba."""
    X = frame[FEATURE_SETS[feature_set]]
    y = make_target(frame["Target"], task)
    X_train, X_test, y_train, y_test = split_train_test(X, y)
    search = fit_search(model_name, X_train, y_train)
    cv = cv_summary(search, X_train, y_train)
    metrics, predictions = evaluate_model(search.best_estimator_, X_test, y_test, task)
    record = {
        "id": identifier, "model_name": model_name, "feature_set": feature_set, "task": task,
        "n_features": X.shape[1], "n_train": len(y_train), "best_params": search.best_params_,
        "cv": cv, "test": metrics,
    }
    return record, search.best_estimator_, predictions



def run_baseline(frame: pd.DataFrame) -> dict:
    """EXP_00: prior binario temprano, mismo split y métricas; fuera de selección."""
    X = frame[FEATURE_SETS["temprano"]]
    y = make_target(frame["Target"], "binaria")
    X_train, X_test, y_train, y_test = split_train_test(X, y)
    search = GridSearchCV(DummyClassifier(strategy="prior"), {}, scoring="f1_macro",
                          cv=make_cv(), n_jobs=1, error_score="raise")
    search.fit(X_train, y_train)
    metrics, _ = evaluate_model(search.best_estimator_, X_test, y_test, "binaria")
    return {
        "id": "EXP_00", "model_name": "dummy_prior", "feature_set": "temprano",
        "task": "binaria", "n_features": X.shape[1], "n_train": len(y_train),
        "best_params": {"strategy": "prior"},
        "cv": cv_summary(search, X_train, y_train), "test": metrics,
    }


def confusion_figure(record: dict) -> None:
    """FIG_ML_06: usa la matriz almacenada; no vuelve a predecir."""
    fig, ax = plt.subplots(figsize=(7, 6))
    ConfusionMatrixDisplay(np.asarray(record["test"]["confusion_matrix"]),
                           display_labels=[CLASS_LABELS[c] for c in record["test"]["classes"]]).plot(
                               ax=ax, colorbar=False, values_format="d")
    ax.set(title=f"FIG_ML_06 · {record['id']} · Matriz de confusión",
           xlabel="Clase predicha", ylabel="Clase observada")
    save_figure(fig, f"FIG_ML_06_matriz_confusion_{record['id']}.png")


def calibration_figure(records: list[dict], predictions: dict) -> None:
    """FIG_ML_07: compara probabilidades binarias sin recalibrar ni ajustar umbrales."""
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.plot([0, 1], [0, 1], linestyle="--", color="black", label="Calibración ideal")
    for record in records:
        if record["task"] != "binaria":
            continue
        values = predictions[record["id"]]
        observed, predicted = calibration_curve(values["observed_dropout"], values["dropout_probability"],
                                                 n_bins=10, strategy="uniform")
        ax.plot(predicted, observed, marker="o", label=f"{record['id']} · {record['model_name']} · {record['feature_set']}")
    ax.set(title="FIG_ML_07 · Calibración de la probabilidad de deserción",
           xlabel="Probabilidad media estimada", ylabel="Proporción observada de deserción",
           xlim=(0, 1), ylim=(0, 1))
    ax.legend(fontsize=8)
    save_figure(fig, "FIG_ML_07_calibracion_dropout.png")


def transformed_variables(pipeline: Pipeline) -> tuple[list[str], list[str]]:
    """ML_02: asocia cada salida del preprocesador con su variable y etiqueta legible."""
    preprocessor = pipeline.named_steps["preprocess"]
    numeric = list(preprocessor.transformers_[0][2])
    categorical = list(preprocessor.transformers_[1][2])
    origins = numeric.copy()
    labels = [f"{VARIABLE_IDS[c]} · {DESCRIPTIONS[c]} (estandarizada)" for c in numeric]
    encoder = preprocessor.named_transformers_["cat"].named_steps["encoder"]
    for column, categories in zip(categorical, encoder.categories_):
        for category in categories:
            origins.append(column)
            labels.append(f"{VARIABLE_IDS[column]} · {DESCRIPTIONS[column]} = {category:g}")
    return origins, labels


def importance_and_tree_figures(records: list[dict], pipelines: dict,
                                frame: pd.DataFrame) -> dict:
    """FIG_ML_08…10: separa interpretación temprana de evidencia del conjunto completo."""
    summaries = {}
    for horizon, figure_id, filename in (
        ("temprano", "FIG_ML_08", "FIG_ML_08_importancia_variables.png"),
        ("completo", "FIG_ML_10", "FIG_ML_10_importancia_conjunto_completo.png"),
    ):
        chosen = {model: next(r for r in records if r["task"] == "binaria"
                              and r["feature_set"] == horizon and r["model_name"] == model)
                  for model in ("logreg", "arbol")}
        fig, axes = plt.subplots(1, 2, figsize=(18, 9))
        for ax, (model_name, record) in zip(axes, chosen.items()):
            pipeline = pipelines[record["id"]]
            classifier = pipeline.named_steps["classifier"]
            origins, labels = transformed_variables(pipeline)
            weights = (np.abs(classifier.coef_).mean(axis=0) if model_name == "logreg"
                       else classifier.feature_importances_)
            ranked = pd.Series(weights).nlargest(15)
            importance = pd.Series(ranked.values, index=[labels[i] for i in ranked.index]).sort_values()
            ax.barh(importance.index, importance.values)
            ax.set(title=f"{record['id']} · {'Regresión logística' if model_name == 'logreg' else 'Árbol'}",
                   xlabel="Valor absoluto del coeficiente" if model_name == "logreg"
                   else "Importancia por reducción de impureza")
            principal = int(ranked.index[0])
            summaries[record["id"]] = {
                "principal": labels[principal],
                "peso_principal": float(weights[principal]),
                "proporcion_principal": float(weights[principal] / weights.sum()),
            }
            if horizon == "temprano" and model_name == "logreg":
                X_train, _, _, _ = split_train_test(frame[FEATURE_SETS[horizon]],
                                                    make_target(frame["Target"], "binaria"))
                preprocessor = pipeline.named_steps["preprocess"]
                categorical = list(preprocessor.transformers_[1][2])
                encoder = preprocessor.named_transformers_["cat"].named_steps["encoder"]
                offset = len(preprocessor.transformers_[0][2])
                categories_by_index = {}
                for column, categories in zip(categorical, encoder.categories_):
                    for category in categories:
                        categories_by_index[offset] = (column, category)
                        offset += 1
                summaries[record["id"]]["soporte_categorias_top"] = [
                    {"variable": VARIABLE_IDS[origins[i]], "etiqueta": labels[i],
                     "codigo": float(categories_by_index[i][1]),
                     "n_train_codigo": int(X_train[categories_by_index[i][0]]
                                           .eq(categories_by_index[i][1]).sum())}
                    for i in ranked.index if i in categories_by_index
                ]
        fig.suptitle(f"{figure_id} · Variables principales de los modelos binarios · {horizon}")
        save_figure(fig, filename)

    record = next(r for r in records if r["task"] == "binaria"
                  and r["feature_set"] == "temprano" and r["model_name"] == "arbol")
    pipeline = pipelines[record["id"]]
    _, labels = transformed_variables(pipeline)
    fig, ax = plt.subplots(figsize=(32, 13))
    plot_tree(pipeline.named_steps["classifier"], max_depth=3,
              feature_names=[textwrap.fill(label, width=35) for label in labels],
              class_names=[CLASS_LABELS[c] for c in pipeline.classes_],
              filled=True, impurity=False, precision=2, fontsize=7, ax=ax)
    # FIG_ML_09: plot_tree no permite traducir estas anotaciones mediante argumentos.
    for annotation in ax.texts:
        label = (annotation.get_text().replace("samples", "muestras").replace("value", "pesos por clase")
                 .replace("class =", "clase =").replace("True", "Sí").replace("False", "No"))
        annotation.set_text(label)
    ax.set_title(f"FIG_ML_09 · {record['id']} · Árbol hasta profundidad dibujada 3\n"
                 "Umbrales numéricos estandarizados; valores de clase ponderados", fontsize=18)
    save_figure(fig, "FIG_ML_09_arbol.png")
    return {"logreg": "EXP_02", "arbol": record["id"],
            "completo": {"logreg": "EXP_04", "arbol": "EXP_08"}, "resumen": summaries}


def write_csv(records: list[dict]) -> None:
    """TAB_ML_02: exporta todas las métricas y metadatos sin perder estructuras."""
    import json

    rows = []
    for record in records:
        row = {k: v for k, v in record.items() if k not in ("test", "cv")}
        row.update({f"cv_{k}": v for k, v in record["cv"].items()})
        row.update({f"test_{k}": v for k, v in record["test"].items()})
        rows.append({k: json.dumps(v, ensure_ascii=False, sort_keys=True) if isinstance(v, (dict, list)) else v
                     for k, v in row.items()})
    pd.DataFrame(rows).to_csv(METRICS_DIR / "experimentos.csv", index=False, encoding="utf-8")


def write_report(records: list[dict], selected: dict, interpreted: dict, metadata: dict) -> None:
    """ML_02: genera tablas y justificación con resultados de ejecución, sin cifras manuales."""
    lines = ["# ML_02 · Comparativa de modelos · SIPDE / INT_03", "",
             "Orden fijo: modelo (logreg, arbol), conjunto (temprano, completo), "
             "tarea (multiclase, binaria). Cada combinación recibe su EXP_xx en ese orden.",
             "Se reserva test antes de ajustar imputadores, escaladores y categorías. "
             "La búsqueda usa F1-macro y solo train; el recall de desempate se calcula por CV "
             "del mejor estimador, también exclusivamente en train. Test se predice una vez por experimento.",
             f"Semilla: {SEED}. SHA-256: `{metadata['dataset_sha256']}`. "
             f"scikit-learn: {metadata['sklearn_version']}; pandas: {metadata['pandas_version']}.", "",
             "## TAB_ML_02 · Resultados de los experimentos", "",
             "EXP_00 es una referencia trivial (DummyClassifier, strategy=prior): "
             "usa la tarea binaria, el conjunto temprano y la misma partición; no participa en la selección.", "",
             "| ID | Modelo | Conjunto | Tarea | F1-macro CV ± DE | Recall Dropout CV | F1-macro test | Recall Dropout test | Precisión Dropout test | Exactitud | Exactitud balanceada | F1 Dropout | ROC-AUC | Brier Dropout |",
             "|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for record in records:
        cv, test = record["cv"], record["test"]
        lines.append(f"| {record['id']} | {record['model_name'] + (' (referencia trivial)' if record['id'] == 'EXP_00' else '')} | {record['feature_set']} | {record['task']} | "
                     f"{cv['f1_macro_mean']:.6f} ± {cv['f1_macro_std']:.6f} | {cv['recall_dropout_mean']:.6f} | "
                     + " | ".join(f"{test[key]:.6f}" for key in ["f1_macro", "recall_dropout", "precision_dropout",
                                                                  "accuracy", "balanced_accuracy", "f1_dropout", "roc_auc", "brier_dropout"]) + " |")
    lines += ["", "ROC-AUC binaria usa Dropout como positivo; multiclase usa OVR macro. "
              "Brier siempre compara el indicador Dropout con su probabilidad. Las matrices están en orden de classes. "
              "La partición es idéntica entre modelos y conjuntos de una misma tarea; al reagrupar el objetivo "
              "cambia la estratificación, por lo que no se comparan las tareas como si compartieran todos los individuos de test.", "",
              "## Selección automática dentro del horizonte temprano según ML_00", ""]
    by_id = {record["id"]: record for record in records}
    for task, identifier in selected.items():
        record = by_id[identifier]
        best = max([r for r in records if r["task"] == task and r["feature_set"] == "temprano" and r["id"] != "EXP_00"], key=lambda r: r["cv"]["f1_macro_mean"])
        best_tree = max([r for r in records if r["task"] == task and r["feature_set"] == "temprano" and r["model_name"] == "arbol"],
                        key=lambda r: (r["cv"]["f1_macro_mean"], r["cv"]["recall_dropout_mean"]))
        tree_gap = best["cv"]["f1_macro_mean"] - best_tree["cv"]["f1_macro_mean"]
        gap = best["cv"]["f1_macro_mean"] - record["cv"]["f1_macro_mean"]
        lines += [f"### {task}: {identifier}", "",
                  f"Se selecciona {record['model_name']} / {record['feature_set']}: "
                  f"F1-macro CV {record['cv']['f1_macro_mean']:.6f} ± {record['cv']['f1_macro_std']:.6f}; "
                  f"recall Dropout CV {record['cv']['recall_dropout_mean']:.6f}. "
                  f"El máximo de la tarea en temprano es {best['id']} con {best['cv']['f1_macro_mean']:.6f}; "
                  f"la diferencia es {gap:.6f}. "
                  + ("Se aplica la preferencia por árbol dentro del margen de 0.01 por interpretabilidad."
                     if record["model_name"] == "arbol" else "Ningún árbol alcanza el margen de 0.01; se conserva el máximo de CV."),
                  f"El mejor árbol es {best_tree['id']}, con F1-macro CV {best_tree['cv']['f1_macro_mean']:.6f}; "
                  f"su distancia al máximo es {tree_gap:.6f}.",
                  f"Entrenamiento: {record['n_train']} filas; prueba: {record['test']['n_test']}. "
                  f"Hiperparámetros: `{record['best_params']}`.", "",
                  f"Matriz de confusión de {identifier}; filas observadas, columnas predichas:", "",
                  "| Clase | " + " | ".join(CLASS_LABELS[c] for c in record["test"]["classes"]) + " |",
                  "|---|" + "---:|" * len(record["test"]["classes"])]
        for label, row in zip(record["test"]["classes"], record["test"]["confusion_matrix"]):
            lines.append(f"| {CLASS_LABELS[label]} | " + " | ".join(str(value) for value in row) + " |")
        lines += ["", f"![FIG_ML_06 · {identifier}](figures/FIG_ML_06_matriz_confusion_{identifier}.png)", ""]
    production = by_id[selected["binaria"]]
    ceiling = by_id["EXP_04"]
    early_reference = by_id["EXP_02"]
    lines += ["## Candidata para el sistema", "",
              f"Se recomienda {production['id']} ({production['model_name']}, {production['feature_set']}, binaria). "
              "ML_00 fija el horizonte temprano como decisión de producto ANTES de comparar: "
              "la alerta debe estar disponible al cierre del primer semestre. "
              "Dentro de ese horizonte se selecciona por F1-macro de CV y el desempate predefinido. "
              "La multiclase se conserva como comparación.",
              "EXP_04 es una referencia de techo con datos del segundo semestre: "
              "unidades inscritas o aprobadas iguales a cero pueden reflejar deserciones ya ocurridas "
              "y proximidad al objetivo. No satisface el horizonte de producción.",
              f"Frente a EXP_04, el costo de anticipar con EXP_02 es "
              f"{ceiling['cv']['f1_macro_mean'] - early_reference['cv']['f1_macro_mean']:.6f} de F1-macro CV "
              f"y {ceiling['cv']['recall_dropout_mean'] - early_reference['cv']['recall_dropout_mean']:.6f} de recall Dropout CV; "
              f"en test es {ceiling['test']['f1_macro'] - early_reference['test']['f1_macro']:.6f} de F1-macro "
              f"y {ceiling['test']['recall_dropout'] - early_reference['test']['recall_dropout']:.6f} de recall Dropout "
              "(diferencias EXP_04 menos EXP_02; un signo negativo indica mejora al anticipar). "
              f"EXP_02 test: F1-macro {early_reference['test']['f1_macro']:.6f}, "
              f"recall {early_reference['test']['recall_dropout']:.6f}; "
              f"EXP_04 test: F1-macro {ceiling['test']['f1_macro']:.6f}, "
              f"recall {ceiling['test']['recall_dropout']:.6f}.",
              "La recomendación es experimental: no certifica calibración ni desempeño en ESCOM. "
              "Los pesos balanceados pueden alterar la calibración; FIG_ML_07 y Brier describen esa limitación. "
              "Las curvas de test son descriptivas: no se ajustó calibrador ni umbral con ellas.", "",
              "## Interpretación y limitaciones", "",
              f"FIG_ML_08 interpreta {interpreted['logreg']} (modelo de producción) y {interpreted['arbol']} "
              "en el horizonte temprano: muestra los 15 mayores valores absolutos de coeficientes de la regresión "
              "y las 15 mayores importancias del árbol tras el preprocesamiento. "
              f"La principal salida de EXP_02 por |coef| es {interpreted['resumen']['EXP_02']['principal']} "
              f"({interpreted['resumen']['EXP_02']['peso_principal']:.6f}); "
              f"en EXP_06 es {interpreted['resumen']['EXP_06']['principal']} "
              f"({interpreted['resumen']['EXP_06']['proporcion_principal']:.2%} de la importancia total). "
              "Las categorías aparecen con su código observado y las numéricas con su escala estandarizada. "
              "El valor absoluto oculta el signo del coeficiente; estas escalas no son comparables "
              "entre modelos ni implican causalidad.",
              "FIG_ML_09 representa EXP_06, árbol binario temprano, hasta profundidad dibujada 3; "
              "trunca solo el dibujo, no el modelo. Los umbrales numéricos están estandarizados "
              "y los conteos de clase incluyen pesos balanceados.",
              "FIG_ML_10 conserva EXP_04 y EXP_08, binarios del conjunto completo. "
              f"En EXP_08, {interpreted['resumen']['EXP_08']['principal']} concentra "
              f"{interpreted['resumen']['EXP_08']['proporcion_principal']:.2%} de la importancia total "
              "por reducción de impureza. Su uso de información del segundo semestre evidencia proximidad "
              "al objetivo y disponibilidad tardía; no justifica incorporarla al horizonte de producción.", "",
              "### Soporte de categorías nominales en el top 15 de EXP_02", "",
              "Advertencia: las categorías nominales con poco soporte pueden recibir coeficientes grandes "
              "en la regresión. Un |coef| alto no garantiza una asociación estable. "
              "Se cuenta el código observado en las filas originales de train de la partición binaria, "
              "sin incluir test ni contar imputaciones como observaciones del código.", "",
              "| Categoría del top 15 por coeficiente absoluto | Registros de train con ese código |",
              "|---|---:|",
              *[f"| {row['etiqueta']} | {row['n_train_codigo']} |"
                for row in interpreted['resumen']['EXP_02']['soporte_categorias_top']], "",
              LIMITATIONS, "La CV usada para seleccionar hiperparámetros no es anidada; su mejor puntuación "
              "puede ser optimista. El test queda fuera de esa selección y solo estima desempeño en esta población. "
              "La incertidumbre entre pliegues no es un intervalo de confianza poblacional.", ""]
    for name in ["FIG_ML_07_calibracion_dropout", "FIG_ML_08_importancia_variables", "FIG_ML_09_arbol",
                 "FIG_ML_10_importancia_conjunto_completo"]:
        lines += [f"![{name}](figures/{name}.png)", ""]
    lines += ["Hiperparámetros de cada experimento:", ""]
    lines.extend(f"- {r['id']}: `{r['best_params']}`." for r in records)
    (REPORTS_DIR / "ML_02_comparativa_modelos.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    """ML_02: regenera resultados completos y recomienda sin consultar métricas de test."""
    frame = load_dataset()
    records, pipelines, predictions = [], {}, {}
    for index, (model, feature_set, task) in enumerate(EXPERIMENT_ORDER, 1):
        identifier = f"EXP_{index:02d}"
        print(f"ML_02 · {identifier}: {model} / {feature_set} / {task}", flush=True)
        record, pipeline, predicted = run_experiment(frame, identifier, model, feature_set, task)
        records.append(record)
        pipelines[identifier], predictions[identifier] = pipeline, predicted
        print(f"{identifier}: CV={record['cv']['f1_macro_mean']:.9f}; "
              f"F1-macro test={record['test']['f1_macro']:.9f}; recall Dropout={record['test']['recall_dropout']:.9f}", flush=True)
    selected = {task: select_experiment([r for r in records if r["task"] == task and r["feature_set"] == "temprano"])["id"]
                for task in ("multiclase", "binaria")}
    for record in records:
        confusion_figure(record)
    calibration_figure(records, predictions)
    interpreted = importance_and_tree_figures(records, pipelines, frame)
    metadata = {"dataset_sha256": dataset_sha256(DATA_PATH), "seed": SEED,
                "sklearn_version": sklearn.__version__, "pandas_version": pd.__version__,
                "numpy_version": np.__version__}
    production = next(record for record in records if record["id"] == selected["binaria"])
    recommendation = {"modelo": production["model_name"], "conjunto": production["feature_set"], "tarea": "binaria"}
    records = [run_baseline(frame), *records]
    write_json(METRICS_DIR / "experimentos.json", {"id": "ML_02", "metadata": metadata,
               "experiments": records, "selected": selected, "recommended_config": recommendation,
               "interpretation": interpreted})
    write_csv(records)
    write_report(records, selected, interpreted, metadata)
    print(f"ML_02: seleccionados={selected}; CONFIG_RECOMENDADA={recommendation}", flush=True)


if __name__ == "__main__":
    main()
