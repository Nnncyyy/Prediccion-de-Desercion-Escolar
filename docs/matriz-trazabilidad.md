# Matriz de trazabilidad inicial

| Requisito | Caso de uso | Componente | Prueba | Responsable |
|---|---|---|---|---|
| RF_01 | CU_01 | API auth + Login UI | PT_01 | INT_02 / INT_04 |
| RF_03 | CU_02 | students + UI | PT_02 | INT_02 / INT_04 |
| RF_05 | CU_03 | enrollments + UI | PT_03 | INT_02 / INT_04 |
| RF_09 | CU_04 | `backend/app/services/ml.py` + `/api/ml/*`; `docs/contrato-ml.md` | PT_08 + `backend/tests/test_ml_api.py` (PT_07 parcial) | INT_03 |
| RF_10 | CU_05 / RA_01 | `backend/app/services/risk.py` | `backend/tests/test_risk.py` (RA_01) | INT_03 |
| RF_12 | CU_06 | dashboard UI | PT_06 | INT_04 |
| RF_08 | ML_01 / ML_02 | `ml/training/` (train, evaluate, workflow); auditoría ML_01 | PT_09 / PT_10 | INT_03 |
| RF_15 | ML_02 | `ml/training/experiments.py` | Reporte `ml/reports/ML_02_comparativa_modelos.md` (EXP_01…EXP_08) | INT_03 |
| RNF_06 | ML_00 / ML_02 | Semilla, split y pipeline solo train; `ml/training/evaluate.py` | PT_10 / reproducción de métricas | INT_03 |
