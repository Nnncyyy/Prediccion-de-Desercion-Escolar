# Matriz de trazabilidad de pruebas de SIPDE

| Requisito/regla | Caso de uso o referencia | Módulo | Prueba | Archivo de prueba | Responsable |
|---|---|---|---|---|---|
| RF_01 | CU_01 | MOD_06 Administración | PT_01, PT_07, PT_14 | `backend/tests/test_pt01_autenticacion.py`, `test_api_dominio.py::test_login_y_cuenta`, `test_pt07_permisos.py`, `test_pt14_regresion.py` | INT_02 |
| RF_02 | ACT_01 / CU_01 | MOD_06 Administración | PT_07, PT_14 | `backend/tests/test_pt07_permisos.py`, `test_pt14_regresion.py` | INT_02 |
| RF_03, RF_06 | CU_02 | MOD_02 Estudiantes | PT_02, PT_07, PT_14 | `backend/tests/test_pt02_estudiantes.py`, `test_api_dominio.py`, `test_pt07_permisos.py`, `test_pt14_regresion.py` | INT_02 |
| RF_04 | CU_02 / CU_03 | MOD_03 Historial académico / MOD_06 Administración | PT_02, PT_03, PT_07, PT_14 | `backend/tests/test_pt02_estudiantes.py`, `test_pt03_calificaciones.py`, `test_pt07_permisos.py`, `test_pt14_regresion.py` | INT_02 |
| RF_05 | CU_03 | MOD_03 Historial académico | PT_03, PT_07, PT_14 | `backend/tests/test_pt03_calificaciones.py`, `test_api_dominio.py::test_periodo_automatico`, `test_api_importacion_reportes.py`, `test_pt07_permisos.py`, `test_pt14_regresion.py` | INT_02 |
| RF_07 | CU_02 / CU_03 | MOD_02 Estudiantes / MOD_03 Historial académico | PT_07 | `backend/tests/test_api_importacion_reportes.py`, `test_pt07_permisos.py` | INT_02 |
| RF_08, RNF_06 | ML_00 / ML_01 / ML_02 | MOD_04 Predicción de riesgo | PT_09, PT_10 | `backend/tests/test_ml_pt09_metricas.py`, `test_ml_pt10_fuga.py` | INT_03 |
| RF_09, RF_11, RN_03 | CU_04 | MOD_04 Predicción de riesgo | PT_04, PT_07, PT_08, PT_14 | `backend/tests/test_pt04_prediccion.py`, `test_api_dominio.py::test_prediccion_persistida`, `test_ml_api.py`, `test_ml_pt08_esquema.py`, `test_pt07_permisos.py`, `test_pt14_regresion.py` | INT_02 / INT_03 |
| RF_10, RN_05 | CU_05 / RA_01 | MOD_04 Predicción de riesgo | RA_01, PT_05, PT_07, PT_14 | `backend/tests/test_risk.py`, `test_pt05_dashboard.py`, `test_pt07_permisos.py`, `test_pt14_regresion.py` | INT_02 / INT_03 |
| RF_12 | CU_06 / CU_05 para el indicador RA_01 | MOD_01 Panel | PT_05, PT_07, PT_11 | `backend/tests/test_pt05_dashboard.py`, `test_pt07_permisos.py`, `test_pt11_rendimiento.py` | INT_02 / INT_03 |
| RF_13 | Consultar y exportar reportes | MOD_05 Reportes | PT_05, PT_07, PT_14 | `backend/tests/test_api_importacion_reportes.py`, `test_pt07_permisos.py`, `test_pt14_regresion.py` | INT_02 |
| RF_14 | BD_08 / seguimiento académico | MOD_02 Estudiantes | PT_07, PT_14 | `backend/tests/test_pt07_permisos.py`, `test_pt14_regresion.py` | INT_02 |
| RF_15 | ML_02 / EXP_01–EXP_08 | MOD_04 Predicción de riesgo | Comparativa RF_15 | `ml/training/experiments.py`, `ml/reports/ML_02_comparativa_modelos.md` | INT_03 |
| RNF_03 | BD_01–BD_12 | MOD_02–MOD_06 | PT_06, PT_13 | `backend/tests/test_pt06_base_datos.py`, `test_instalacion.py` | INT_02 |
| RN_04, RNF_01 | ACT_01 / ACT_02 / ACT_03 | MOD_01–MOD_06 | PT_01, PT_07 | `backend/tests/test_pt01_autenticacion.py`, `test_pt07_permisos.py` | INT_02 |
| RNF_05 | BD_12 | MOD_06 Administración | PT_02, PT_04, PT_14 | `backend/tests/test_pt02_estudiantes.py`, `test_api_dominio.py::test_prediccion_persistida`, `test_pt14_regresion.py` | INT_02 / INT_03 |
| RNF de rendimiento, RF_03, RF_09, RF_12 | CU_02 / CU_04 / CU_06 | MOD_01 / MOD_02 / MOD_04 | PT_11 | `backend/tests/test_pt11_rendimiento.py` | INT_02 / INT_03 |
| RT_01, RNF_01, RNF_03 | Instalación limpia y datos de demostración | MOD_01–MOD_06 | PT_13 | `backend/tests/test_instalacion.py` | INT_02 |
| RF_01–RF_06, RF_09–RF_11, RF_13–RF_14, RNF_05 | CU_01–CU_05 / BD_08 / BD_12 | MOD_02–MOD_06 | PT_14 | `backend/tests/test_pt14_regresion.py` | INT_02 / INT_03 |

Las referencias abreviadas `test_*.py` en las filas de backend se resuelven bajo `backend/tests/`. El contrato HTTP ubica el dashboard en CU_06 y la alerta RA_01 en CU_05. PT_05 verifica ambos en el panel. PT_12 corresponde al plan de usabilidad y queda fuera de la ejecución de pytest del backend. [Plan de pruebas](pruebas.md)
