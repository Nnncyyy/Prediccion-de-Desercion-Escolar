# ML_00 · Protocolo experimental v2 · SIPDE / INT_03

Este protocolo fija las decisiones antes de consultar las métricas de prueba. ML_01 describe los datos y ML_02 compara regresión logística y árbol de decisión para apoyar tutorías con una estimación de deserción observada. No es un diagnóstico ni una autorización para decisiones automáticas sobre estudiantes.

## Objetivo, horizonte y tareas

El objetivo `Target` corresponde al estado observado al término de la duración normal de los estudios: `Dropout`, `Enrolled` o `Graduate`. El conjunto **temprano** usa inscripción, primer semestre y contexto macroeconómico, por lo que su horizonte de disponibilidad es el cierre del primer semestre. El **completo** añade el segundo semestre y solo puede emplearse al cierre de ese semestre. La etiqueta no representa necesariamente deserción durante el semestre inmediatamente siguiente; no hay fechas individuales para estimar tiempo hasta el abandono.

La tarea **multiclase** conserva los estados originales. La **binaria** compara `Dropout` con `No_Dropout`, agrupando `Enrolled` y `Graduate`. `Enrolled` no significa riesgo intermedio: es continuidad de estudios al observar el objetivo. Agruparlo no garantiza graduación futura. La tarea binaria es candidata natural para el sistema que muestra probabilidad de deserción; la multiclase sirve de comparación.

Las variables de beca, deuda y colegiatura se agrupan con inscripción según el diseño solicitado. Antes de una aplicación real debe verificarse la fecha de captura: el CSV no la registra. Las variables macroeconómicas también deben estar disponibles en la fecha de estimación.

El horizonte de producción es **temprano**, fijado como decisión de producto ANTES de comparar modelos: SIPDE debe estimar al cierre del primer semestre. El conjunto completo es solo una referencia de techo; ceros en unidades inscritas/aprobadas del segundo semestre pueden reflejar deserciones ya ocurridas y proximidad al objetivo. EXP_04 documenta el costo de anticipar frente a EXP_02, con diferencias generadas por código; las métricas de test no deciden el horizonte. `CONFIG_RECOMENDADA` corresponde a logreg / temprano / binaria (EXP_02), sujeto al criterio de CV dentro del horizonte fijado.

## Partición y prevención de fuga

Se usa `SEED = 42` en la semilla global, división, validación cruzada y clasificadores. Se divide el CSV crudo con `train_test_split(test_size=0.2, stratify=y, random_state=SEED)`: 80% entrenamiento y 20% prueba. Para una misma tarea, todos los modelos y conjuntos comparten índices. La estratificación cambia al reagrupar el objetivo entre tareas.

Se seleccionan hiperparámetros exclusivamente sobre entrenamiento con `GridSearchCV(scoring="f1_macro")` y `StratifiedKFold(5, shuffle=True, random_state=SEED)`. Cada pliegue ajusta un pipeline completo: imputación mediana y escalado para numéricas; imputación por moda y `OneHotEncoder(handle_unknown="ignore")` para códigos nominales. Los indicadores binarios se tratan como numéricos. Nunca se imputa el objetivo: se rechazan etiquetas nulas o desconocidas. No se ajustan transformaciones con el CSV completo ni con test.

Ambos modelos usan `class_weight="balanced"`. La regresión logística usa `max_iter=3000` y explora `C ∈ {0.01, 0.1, 1, 10}`. El árbol explora `max_depth ∈ {3, 4, 5, 6, 8}` y `min_samples_leaf ∈ {1, 10, 30}`. Se conserva el primer hiperparámetro de la rejilla si hay empate exacto de F1 entre candidatos del mismo experimento. El mejor estimador se reajusta únicamente en train mediante el comportamiento de `GridSearchCV(refit=True)`.

## EXP_01…EXP_08 · Orden predefinido

| ID | Modelo | Conjunto | Tarea |
|---|---|---|---|
| EXP_01 | logreg | temprano | multiclase |
| EXP_02 | logreg | temprano | binaria |
| EXP_03 | logreg | completo | multiclase |
| EXP_04 | logreg | completo | binaria |
| EXP_05 | arbol | temprano | multiclase |
| EXP_06 | arbol | temprano | binaria |
| EXP_07 | arbol | completo | multiclase |
| EXP_08 | arbol | completo | binaria |

## Métricas y selección automática

La métrica principal es **F1-macro**: media no ponderada de F1 entre clases. Se informa media y desviación estándar de CV del hiperparámetro ganador. Para desempatar modelos se obtiene recall de `Dropout` con otra CV sobre train, del hiperparámetro ya elegido; no se consulta test.

Por cada tarea se escoge el máximo F1-macro medio en CV entre sus experimentos del horizonte temprano. Un empate exacto se resuelve por mayor recall de `Dropout` en CV. Se prefiere el árbol por interpretabilidad si el mejor árbol queda a una distancia de F1-macro ≤0.01 respecto del máximo de esa tarea dentro del horizonte temprano. Si califican varios árboles se elige el de mayor F1-macro y después recall. Un empate restante conserva el orden EXP_xx. La preferencia por árbol puede sacrificar una pequeña cantidad de F1 y recall y se documenta con la diferencia observada. Los experimentos completos se reportan como referencia, sin competir por la recomendación de producción.

En test se reportan exactitud, exactitud balanceada, F1-macro, precisión, recall y F1 de `Dropout`, ROC-AUC y Brier de la probabilidad de `Dropout`, más matriz de confusión con orden de clases explícito. En binaria, ROC-AUC usa el indicador `y == "Dropout"`; se busca la columna de probabilidad por `pipeline.classes_`, nunca por una posición supuesta. En multiclase se usa ROC-AUC OVR macro. Brier usa siempre el indicador binario de `Dropout` y su probabilidad; menor es mejor.

Las curvas de calibración de los experimentos binarios usan diez intervalos uniformes de probabilidad; se omiten intervalos vacíos. Son una evaluación descriptiva del test. No se seleccionan modelos, umbrales o calibradores con test. Los pesos balanceados pueden afectar la calibración. Cualquier calibración futura requerirá un procedimiento independiente dentro de train y un nuevo protocolo.

## Reproducibilidad y límites

Cada experimento predice test una sola vez y reutiliza esas predicciones para métricas y gráficas. `train.py` reproduce el candidato recomendado; guarda el mejor estimador ajustado exclusivamente en train. `evaluate.py` carga ese artefacto, reconstruye la misma partición, verifica SHA-256 y semilla, y exige coincidencia de todas las métricas con tolerancia absoluta `1e-9` y relativa cero. Si no coinciden termina con código distinto de cero. Esta segunda evaluación verifica reproducción y no realimenta la selección.

Se registran semilla, SHA-256, versiones de bibliotecas, columnas, clases, mejores hiperparámetros, métricas y fecha ISO UTC. Se conserva el CSV sin cambios, se usa UTF-8 con eliminación de BOM y se generan cifras por código. Los JSON y CSV mantienen precisión completa; las tablas Markdown redondean solo para presentación. Se limita BLAS a un hilo durante el ajuste y la predicción. La fecha de entrenamiento cambia en cada ejecución; no afecta las métricas.

ML_01 genera FIG_ML_01…FIG_ML_05 y TAB_ML_01. ML_02 genera FIG_ML_06…FIG_ML_09 y TAB_ML_02. Las pruebas oficiales de `backend/tests/` son PT_08 (esquema e integridad), PT_09 (F1-macro, recall Dropout y matriz de confusión) y PT_10 (sin fuga y reproducibilidad, RNF_06). Se ejecutan además las pruebas existentes del backend.

Los datos provienen de Portugal y no validan desempeño en ESCOM. No existen horas laborales ni calificaciones por materia. `Gender` y `Nacionality` pueden introducir sesgos: se documenta su inclusión, pero la comparación agregada no constituye una auditoría de equidad. Antes de uso real se necesitan validación local y temporal, revisión por subgrupos, y un análisis de su exclusión. La CV de selección no es anidada y su mejor F1 puede ser optimista; la prueba reservada ofrece una estimación independiente dentro de esta población. No se infiere causalidad de correlaciones, coeficientes ni importancias.
