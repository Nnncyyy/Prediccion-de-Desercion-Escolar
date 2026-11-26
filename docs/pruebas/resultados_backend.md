# Resultados del backend SIPDE · Tarea I

## Planificación y diseño

Se ejecutó la batería de la Tarea I junto con la suite previa del backend. El plan registra los escenarios y los criterios de aceptación. Los guiones nuevos figuran en los docstrings y las aserciones de las pruebas. [Plan](../pruebas.md) · [Trazabilidad](../matriz-trazabilidad.md)

## Ejecución

- Inicio `2026-11-24T22:30:55-06:00`. Python 3.13.5, pytest 9.2.0, Linux x86_64 y SQLite 3.46.1.
- API `0.1.0` del árbol de trabajo de la Tarea I, SQLite temporal y modelo local `1.0.0-pruebas`. PT_13 ejecutó la migración `0001_esquema_inicial`.
- JUnit registró 129.43 s. [JUnit](junit_backend.xml) · [Salida completa](evidencia_pytest_backend.txt)

## Resultados y comparativa

La unidad de conteo es el caso de pytest. Los 76 casos previos se incluyen una vez en el total, aunque tengan más de una referencia en la matriz.

| PT | Casos | Aprobados | Fallidos | Xfail | Módulo | RF/CU trazado | Observaciones |
|---|---:|---:|---:|---:|---|---|---|
| PT_01 | 10 | 10 | 0 | 0 | MOD_06 | RF_01 / CU_01 | JWT de ocho horas, rechazo uniforme de credenciales incorrectas, sesión inválida y cambio de contraseña. Incluye el caso previo de login y /me. |
| PT_02 | 23 | 23 | 0 | 0 | MOD_02 | RF_03 / RF_06 / CU_02 | Expedientes, conflictos de matrícula, búsqueda sensible a tildes en SQLite, paginación, estados y asignación de tutor. Incluye dos casos previos. |
| PT_03 | 10 | 10 | 0 | 0 | MOD_03 | RF_05 / CU_03 | 6.0 aprobó. Se observaron 422, 404 y 409 en los escenarios rechazados, con edición y borrado verificables. Incluye el caso previo de periodo automático. |
| PT_04 | 5 | 5 | 0 | 0 | MOD_04 | RF_09 / RF_11 / CU_04 / RN_03 | Historial por alumno y global, alcance del tutor y versión de inferencia persistida. Los rechazos dejaron BD_07 sin filas. Incluye el caso previo de persistencia. |
| PT_05 | 7 | 7 | 0 | 0 | MOD_01 / MOD_05 | RF_12 / CU_06 / CU_05 / RF_13 | Panel admin con 5 alumnos, promedio 5.17 y 6 predicciones. Panel tutor con 3 alumnos, promedio 3.67 y 3 predicciones. Incluye reportes RF_13 existentes. |
| PT_06 | 27 | 27 | 0 | 0 | MOD_02–MOD_06 | RNF_03 / BD_01–BD_12 | PRAGMA devolvió 1. Se comprobaron 7 casos UNIQUE, 10 FOREIGN KEY y 9 CHECK. |
| PT_07 | 178 | 178 | 0 | 0 | MOD_01–MOD_06 | RN_04 / RNF_01 / RF_02 / RF_07 / RF_13 | 132 cruces de rol y operación, 24 cruces con alumno ajeno, dos rutas públicas, inventario OpenAPI y dos protecciones del administrador. Incluye cobertura previa de importación, permisos y sesión ML. |
| PT_08 | 27 | 27 | 0 | 0 | MOD_04 | RF_09 / CU_04 | Esquema, probabilidades, contrato HTTP, caché y errores de entrada y artefactos, con las pruebas de IA existentes. |
| PT_09 | 2 | 2 | 0 | 0 | MOD_04 | RF_08 / ML_01 / ML_02 | Se cumplieron los mínimos de F1-macro y recall Dropout. La matriz coincide con el conjunto de test. |
| PT_10 | 5 | 5 | 0 | 0 | MOD_04 | RF_08 / RNF_06 / ML_00 / ML_02 | Particiones, preprocesamiento, horizonte temprano, reproducibilidad y detección de alteraciones. |
| PT_11 | 1 | 1 | 0 | 0 | MOD_01 / MOD_02 / MOD_04 | RNF de rendimiento / RF_03 / RF_09 / RF_12 / CU_02 / CU_04 / CU_06 | 300/300 respuestas HTTP 200. Las tres rutas cumplieron p95 < 1.0 s. |
| PT_12 | 0 | 0 | 0 | 0 | MOD_04 | RF_09 / RF_10 / CU_04 / CU_05 | Inventario de usabilidad. Pendiente de una ejecución de aceptación. |
| PT_13 | 4 | 4 | 0 | 0 | MOD_01–MOD_06 | RT_01 / RNF_01 / RNF_03 | Migración inicial, seed idempotente, reinicio SQLite y configuración probados en test_instalacion.py. |
| PT_14 | 1 | 1 | 0 | 0 | MOD_02–MOD_06 | RF_01–RF_06 / RF_09–RF_11 / RF_13–RF_14 / CU_01–CU_05 / RNF_05 | Flujo completo con alerta alta, seguimiento, predicción, historial, resumen, dos CSV y los 17 eventos de bitácora esperados. |
| RA_01 | 11 | 11 | 0 | 0 | MOD_04 | RF_10 / CU_05 / RN_05 | Casos unitarios previos de las reglas, valores límite y niveles de alerta. |

La suite completa registró 311 casos ejecutados, con 311/311 aprobados, 0/311 fallidos, 0/311 xfail y 0 casos omitidos. La suite reúne 235 casos nuevos y 76 previos. PT_12 tuvo 0 casos en esta ejecución.

### PT_11 · Rendimiento

Se sembraron 200 alumnos y 1,000 inscripciones. Cada ruta recibió 100 peticiones medidas en un lote con 10 hilos de TestClient. El p95 se calculó por rango más próximo. [Datos de la medición](PT_11_rendimiento.json)

| Operación | HTTP 200 | p50 (s) | p95 (s) | Máx. (s) | Peticiones/s |
|---|---:|---:|---:|---:|---:|
| `GET /api/students` | 100/100 | 0.1545 | 0.2515 | 0.2717 | 58.27 |
| `GET /api/dashboard` | 100/100 | 0.3807 | 0.5357 | 0.5839 | 27.74 |
| `POST /api/ml/predict` | 100/100 | 0.3107 | 0.3812 | 0.4376 | 31.30 |

## Decisión y defectos

La batería del backend cumplió los criterios probados y las tres rutas de PT_11 quedaron por debajo de 1.0 s de p95 en este entorno local. La ejecución registró un aviso de deprecación de Starlette sobre httpx.

- Defectos reproducidos e IDs BUG_BE_0X asignados · 0. [Bitácora de defectos](bugs_backend.md)
- Evidencia para el equipo de frontend · esquema con 36 rutas y 44 operaciones generado por FastAPI. [OpenAPI](../openapi.json)
