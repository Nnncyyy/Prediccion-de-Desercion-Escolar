# INT_03 · Pipeline ML de SIPDE

ML_01 audita el dataset y el legado. ML_02 compara modelos y genera un artefacto compatible con el backend. Todo resultado numérico de los informes se calcula mediante los scripts; no se transcriben métricas a mano.

## Reproducción

Desde la raíz de `Prediccion-de-Desercion-Escolar`, usa el entorno existente, sin instalar paquetes:

```bash
source backend/.venv/bin/activate
python ml/eda/audit_dataset.py
python ml/training/experiments.py
python ml/training/train.py
python ml/training/evaluate.py
cd backend && pytest -q
```

Después de `experiments.py`, consulta `recommended_config` en `ml/reports/metrics/experimentos.json`. `CONFIG_RECOMENDADA` en `ml/common.py` debe coincidir antes de ejecutar `train.py`. La configuración entregada es logreg / temprano / binaria (EXP_02): ML_00 fija el horizonte al cierre del primer semestre antes de comparar modelos; el conjunto completo solo es referencia de techo. `train.py` siempre repite la búsqueda sobre train; no necesita cargar modelos de los experimentos ni reajusta con test.

Los scripts resuelven rutas predeterminadas desde su ubicación, por lo que también funcionan desde otro directorio al invocarlos por ruta absoluta. Las rutas proporcionadas expresamente por CLI se interpretan desde el directorio de invocación. `evaluate.py` usa por defecto la ruta del CSV registrada en el artefacto, relativa a la raíz del repo; `--csv` permite indicar su nueva ubicación si se mueve el proyecto, exigiendo el mismo SHA-256.

Para los controles rápidos propios, desde la raíz (sin necesitar el artefacto local):

```bash
source backend/.venv/bin/activate
python -m pytest -q ml/tests
```

`ml/requirements.txt` documenta dependencias; en esta entrega se usa exclusivamente el entorno existente. `threadpoolctl`, ya requerido por scikit-learn, limita el cálculo a un hilo sin añadir paquetes.

## Comandos y contrato

Ejemplo explícito para ejecutar una variante de comparación, manteniendo los parámetros históricos `--csv` y `--out`:

```bash
python ml/training/train.py \
  --csv ml/data/dataset.csv \
  --out ml/artifacts/variante/dropout_model.joblib \
  --modelo logreg --conjunto temprano --tarea binaria --version 1.0.0-variante
python ml/training/evaluate.py \
  --artifact ml/artifacts/variante/dropout_model.joblib \
  --csv ml/data/dataset.csv
```

Se aceptan modelos `logreg` y `arbol`, conjuntos `temprano` y `completo`, y tareas `binaria` y `multiclase`. La versión predeterminada es `1.0.0`. Los JSON de esquema y tarjeta se escriben junto al joblib, en `ml/artifacts/` por defecto. Carga únicamente artefactos joblib locales y confiables.

El joblib conserva `pipeline`, `columns`, `numeric_columns` y `model_name`, que consume el backend. Añade versión, tarea, conjunto, clases, métricas de test, fecha UTC, SHA-256, versiones, semilla, hiperparámetros, CV y resumen de las particiones. `numeric_columns` contiene las columnas de transporte numérico, incluidos los códigos nominales; PT_08 exige que la entrada ya use números JSON y rechaza cadenas numéricas. Dentro del pipeline esos códigos se codifican con categorías, no como magnitudes continuas.

El estimador guardado se ajusta solo con train. `evaluate.py` reconstruye la partición, calcula métricas y verifica igualdad absoluta con tolerancia `1e-9`, sin tolerancia relativa. Devuelve código distinto de cero si cambia cualquier métrica, el hash del CSV o la semilla. Los errores de carga o esquema también producen fallo. El timestamp de entrenamiento puede variar sin afectar las métricas.

## Archivos y trazabilidad

| ID | Archivo o ruta | Contenido |
|---|---|---|
| INT_03 | `common.py` | Semilla, rutas, esquema, descripciones, grupos, objetivo y pipeline compartidos. |
| ML_00 | `reports/ML_00_protocolo_experimental.md` | Diseño, horizontes, rejillas, métricas y selección; sin resultados. |
| ML_01 | `eda/audit_dataset.py` | Generador de auditoría, diccionario y figuras. |
| ML_01 | `reports/dataset_profile.json` | Calidad, distribución, tipos, estadísticas, hash y versión de pandas. |
| VAR_01…VAR_34 | `data/diccionario_variables.csv` | Nombre, significado, tipo, momento, rangos y conjuntos de cada variable. |
| TAB_ML_01 | `reports/ML_01_auditoria_dataset.md` | Auditoría y tabla de variables por momento. |
| AUD_01…AUD_12 | `reports/ML_01_auditoria_expoescom.md` | Hallazgos confirmados del legado y líneas reales, redactado por inspección. |
| ML_02 | `training/workflow.py` | Búsqueda, evaluación y selección sin consulta de test. |
| EXP_01…EXP_08 | `training/experiments.py` | Comparación de todas las combinaciones, en el orden fijado por ML_00. |
| TAB_ML_02 | `reports/ML_02_comparativa_modelos.md` | Tabla de resultados, matrices y justificación automática de la recomendación. |
| ML_02 | `reports/metrics/experimentos.json` y `.csv` | Métricas completas, mejores hiperparámetros, CV y selección por tarea. |
| ML_02 | `training/train.py` | Entrenamiento reproducible del modelo elegido. |
| ML_02 | `artifacts/dropout_model.joblib` | Pipeline y metadatos; el binario está excluido de Git. |
| ML_02 | `artifacts/feature_schema.json` y `model_card.json` | Esquema versionable y tarjeta con uso previsto y limitaciones. |
| PT_10 | `training/evaluate.py` y `reports/metrics/evaluacion_<version>.json` | Verificación del artefacto contra métricas guardadas. |
| PT_08/PT_09/PT_10 | `backend/tests/test_ml_pt*.py` | Pruebas oficiales de esquema, métricas, sin fuga y reproducibilidad; artefacto temporal sin matplotlib. |
| INT_03 | `tests/test_pipeline.py` | Controles rápidos propios de selección y comparación numérica, sin artefactos locales. |

Los generadores sobrescriben sus salidas. La auditoría del legado y el protocolo son textos mantenidos por revisión; no contienen métricas experimentales copiadas. `plotting.py` fija el backend Agg, salida PNG y resolución de 150 dpi.

| ID | Figura en `reports/figures/` |
|---|---|
| FIG_ML_01 | `FIG_ML_01_distribucion_clases.png`: conteos y proporciones. |
| FIG_ML_02 | `FIG_ML_02_tasa_aprobacion_sem1_por_clase.png`: aprobadas/inscritas, omitiendo denominadores cero. |
| FIG_ML_03 | `FIG_ML_03_edad_por_clase.png`: distribución de edad por estado académico. |
| FIG_ML_04 | `FIG_ML_04_correlacion_dropout.png`: asociaciones exploratorias de Pearson. |
| FIG_ML_05 | `FIG_ML_05_colegiatura_beca_vs_dropout.png`: proporciones por indicadores económicos. |
| FIG_ML_06 | `FIG_ML_06_matriz_confusion_EXP_xx.png`: matriz por experimento. |
| FIG_ML_07 | `FIG_ML_07_calibracion_dropout.png`: curvas binarias descriptivas de test. |
| FIG_ML_08 | `FIG_ML_08_importancia_variables.png`: mayores coeficientes absolutos/importancias de los mejores binarios por familia; categorías con su código observado y numéricas estandarizadas. |
| FIG_ML_09 | `FIG_ML_09_arbol.png`: mejor árbol binario por CV, dibujo truncado a profundidad tres. |

## Uso responsable y procedencia

El CSV local procede del Instituto Politécnico de Portalegre, Portugal, durante 2008–2019. No representa población de ESCOM-IPN. El conjunto temprano solo está disponible al cierre del primer semestre y completo al cierre del segundo. Los estados económicos no incluyen fecha individual de captura: debe verificarse su disponibilidad histórica antes de usarlos como datos de inscripción. No hay horas de trabajo ni calificaciones por materia, por lo que el pipeline no inventa estas variables.

`Enrolled` significa continuidad observada, no “riesgo intermedio”. `No_Dropout` agrupa ese estado y graduación, sin garantizar finalización futura. Las probabilidades son apoyo experimental, no un diagnóstico. `Gender` y `Nacionality` son sensibles: las métricas agregadas no prueban equidad y deben complementarse con validación local, temporal y por subgrupos antes de uso operativo. Los pesos de clase balanceados pueden afectar la calibración; se informa Brier y la curva, sin ajustar un calibrador con test.

Se conserva `Nacionality` tal como aparece en el origen. No se trasladan significados de códigos individuales de otra versión sin mapeo verificado. El esquema JSON enumera únicamente códigos observados, y sus rangos describen esta muestra, no límites universales. La ficha UCI actual tiene un esquema ampliado; el programa valida la copia local especificada para INT_03.

Fuentes primarias: [ficha y documentación UCI](https://archive.ics.uci.edu/dataset/697/predict+students+dropout+and+academic+success) y [Realinho et al., descriptor de datos](https://doi.org/10.3390/data7110146). La ficha indica licencia CC BY 4.0. El CSV original y el código legado se conservan sin cambios.

## INT_03 · Inferencia y demo ACE_03

El contrato de endpoints, errores, formulario, RA_01 y pendientes de INT_02 está en [docs/contrato-ml.md](../docs/contrato-ml.md). `train.py` también genera `artifacts/ejemplos_prediccion.json`: tres filas reales de test, una por clase original (`Dropout`, `Enrolled`, `Graduate`), solo con las columnas del modelo, clase real y probabilidades emitidas. En la tarea binaria las dos últimas clases comparten el objetivo `No_Dropout`.

Las pruebas oficiales de CI son las de `backend/tests/`; entrenan el candidato en un directorio temporal por sesión y aíslan la BD para probar la API. No necesitan matplotlib ni el joblib local. `ml/tests/` conserva solamente controles rápidos de selección por CV y tolerancia numérica, sin IDs PT duplicados.
