# PT — Plan de pruebas inicial

- PT_01 Inicio de sesión: credenciales válidas → JWT; inválidas → HTTP 401.
- PT_02 Alumnos: alta válida → HTTP 201; matrícula repetida → HTTP 409.
- PT_03 Calificaciones: registrar nota 0..10; fuera de rango → HTTP 422.
- PT_04 IA (entrada inicial sustituida por PT_08/PT_09/PT_10 abajo): controles oficiales de esquema, métricas, sin fuga y reproducibilidad; responsable INT_03.
- PT_05 Alertas / RA_01 (RF_10): evidencia vigente en `backend/tests/test_risk.py`; sin calificaciones → sin_datos; 2 reprobadas y trabajo 30 h → alta; no etiquetar como probabilidad ML. Responsable INT_03.
- PT_06 Dashboard: conteos según BD.
- PT_07 Seguridad: endpoint privado sin token → 401/403.
- PT_08 Integración: crear estudiante + materia + inscripción y consultar alerta.
- PT_09 Manual: ejecutar desde clon limpio con .env configurado.

Cada ejecución debe incluir ID, fecha, versión, responsable, entrada, salida esperada, resultado observado, estado, evidencia y defecto si aplica.

## INT_03 · Entradas vigentes de IA

Esta sección fija los IDs vigentes de IA: PT_08 es esquema/integridad, PT_09 métricas y PT_10 sin fuga/reproducibilidad. Las asignaciones del plan inicial PT_08 Integración y PT_09 Manual conservadas arriba son históricas, no corresponden a estas pruebas de IA y requieren reindexación por sus responsables fuera de INT_03. PT_11–PT_14 quedan reservados para rendimiento, usabilidad, instalación y regresión de otras tareas.

| ID | Requerimiento / diseño | Objetivo, entrada y resultado esperado | Evidencia ejecutable | Responsable |
|---|---|---|---|---|
| PT_08 | RF_09 / CU_04 | Artefacto, esquema y FEATURE_SETS con columnas idénticas, sin BOM; fila real devuelve probabilidades que suman 1 y p(Dropout) en [0,1]. Faltantes, sobrantes, tipos inválidos, rangos y códigos desconocidos → 422 por campo. BOM/espacios se aceptan. ACE_03 verifica tres filas reales de test. | `backend/tests/test_ml_pt08_esquema.py` | INT_03 |
| PT_09 | RF_08 / ML_01 / ML_02 | Entrenamiento temporal recomendado: F1-macro y recall Dropout superan constantes fijadas tras ejecución y redondeo hacia abajo a 0.05; comentario con valores observados. Matriz k×k con suma igual a test y orden de clases comprobado. | `backend/tests/test_ml_pt09_metricas.py` | INT_03 |
| PT_10 | RF_08 / RNF_06 / ML_00 / ML_02 | Train/test disjuntos y estratificados (<1 punto de diferencia de proporción Dropout); media del escalador igual a train, distinta de todo el CSV; temprano sin 2º semestre; dos entrenamientos dan métricas idénticas. Evaluación detecta alteraciones. | `backend/tests/test_ml_pt10_fuga.py`; `ml/training/evaluate.py` | INT_03 |
| RF_09_API / PT_07 parcial | RF_09 / CU_04 / RN_01 / RN_05 | Login del admin de settings contra SQLite temporal y lifespan real; GET model/schema y POST predict → 200 y contrato; sin token → 401/403; entrada inválida → 422; sin artefactos → 503. Caché recarga por mtime y metadatos antiguos admiten null. Sin escritura de PredictionLog. | `backend/tests/test_ml_api.py` | INT_03 |
| RA_01 | RF_10 / RA_01_R1…R3 | Cada regla y niveles; exactamente 6.0 aprueba, exactamente 30 h activa R3; 29 h y sin empleo no la activan; sin notas/nulos → sin_datos. Llaves actuales y method conservados. | `backend/tests/test_risk.py` | INT_03 |
| RF_15 | RF_15 / ML_02 | Ocho experimentos; recomendación por CV solo dentro del horizonte temprano fijado previamente; EXP_04 como referencia de techo, costo frente a EXP_02 generado por código. | `ml/training/experiments.py` → `ml/reports/ML_02_comparativa_modelos.md` | INT_03 |

### INT_03 · Ejecución y aislamiento

```bash
source backend/.venv/bin/activate
python ml/training/experiments.py
python ml/training/train.py
python ml/training/evaluate.py
cd backend && pytest -q
```

`backend/tests/conftest.py` agrega la raíz al sys.path, entrena CONFIG_RECOMENDADA una vez por sesión en un directorio temporal (<60 s), cambia settings.model_path durante la sesión y crea una BD SQLite temporal para cada prueba HTTP. Ninguna prueba necesita el joblib local ni importa matplotlib. El bucle de TestClient tiene un latido por temporizador para funcionar también en sandboxes que bloquean el aviso por socketpair; se ejecuta el lifespan completo y el login real. No se instalan dependencias nuevas.

Los mínimos de PT_09 se encuentran en las constantes del test y sus valores observados en el comentario generado desde model_card.json. RF_11/RN_03 (persistencia) y RN_04 (restricción por rol) siguen pendientes de INT_02 según `docs/contrato-ml.md`.

### INT_03 · Registro de ejecución

Fecha de la evidencia HTTP: `2026-11-03T03:12:05.822347+00:00`; modelo `1.0.0`; SHA-256 `6bcfb6b3c826c4b8b9c7a99c063762748f6f462e24aabd26719ec2e55fed6135`; responsable INT_03.

| ID | Entrada / evidencia | Resultado observado | Estado / defecto |
|---|---|---|---|
| PT_08 / PT_09 / PT_10 / RF_09_API / RA_01 | `cd backend && pytest -q`; modelo y SQLite temporales, filas reales de test | 48 pruebas aprobadas en 6.04 s; sin matplotlib; un aviso de deprecación de Starlette sobre httpx | Correcto; sin defectos detectados en el alcance |
| INT_03 | `python -m pytest -q ml/tests`; selección por CV y tolerancia | 2 controles rápidos aprobados en 1.00 s | Correcto |
| PT_10 | `python ml/training/evaluate.py`; artefacto local de la versión indicada | matches_saved_metrics=true, diferencias=0, tolerancia absoluta 1e-09 | Correcto |

La salida HTTP real usada como evidencia está transcrita en `docs/contrato-ml.md`. El aviso de la dependencia no requiere ni motivó instalar paquetes adicionales.
