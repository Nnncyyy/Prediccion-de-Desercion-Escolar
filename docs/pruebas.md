# PT · Plan de pruebas de SIPDE

El inventario usa las etapas del capítulo 7 del informe. Los resultados del backend se registran por caso de pytest, incluidas las parametrizaciones.

## Planificación y diseño

| ID | Tipo | Nivel | Prioridad | Escenario y resultado esperado | Responsable |
|---|---|---|---|---|---|
| PT_01 | Funcional y seguridad | Integración HTTP | Alta | Las credenciales y la cuenta vigentes dan acceso. Login inválido y sesiones ausentes, vencidas o alteradas devuelven 401. El cambio válido permite iniciar sesión con la clave nueva. | INT_02 |
| PT_02 | Funcional | Integración HTTP | Alta | Alta completa, edición parcial, conflictos 409 por matrícula, búsqueda literal, filtros, paginación, baja y reactivación. Solo se asignan tutores activos y la desvinculación retira su acceso. | INT_02 |
| PT_03 | Funcional e integridad | Integración HTTP | Alta | 6.0 aprueba. Las notas inválidas devuelven 422, las referencias ausentes 404, y un alumno inactivo o una inscripción duplicada 409. PATCH y DELETE cambian el historial. El periodo automático se reutiliza. | INT_02 |
| PT_04 | Funcional e integración ML | Integración HTTP y persistencia | Alta | Inferencia con un alumno asignado, 404 fuera de alcance o ante un alumno ausente, y 422 con variables incompletas. BD_07 conserva la versión y el historial respeta las asignaciones. | INT_02 / INT_03 |
| PT_05 | Funcional | Integración HTTP | Alta | El panel coincide con el lote controlado para admin y tutor, incluidos promedios, alertas RA_01 y categorías ML. También cubre RF_13 mediante las pruebas existentes de reportes. | INT_02 / INT_03 |
| PT_06 | Integridad de datos | Base de datos | Alta | SQLite activa las claves foráneas y rechaza filas que infringen restricciones UNIQUE, FOREIGN KEY o CHECK mediante SQLAlchemy. | INT_02 |
| PT_07 | Autorización y privacidad | Integración HTTP | Alta | La matriz RN_04 fija el HTTP exacto de cada operación por rol. Las respuestas omiten password_hash. Un administrador conserva su rol y la última cuenta administradora sigue activa. | INT_02 |
| PT_08 | Contrato y validación ML | Componente e integración HTTP | Alta | Artefacto, esquema y columnas de entrenamiento coinciden. Una fila real produce probabilidades en rango que suman 1. Los valores inválidos devuelven 422 por campo. | INT_03 |
| PT_09 | Evaluación ML | Componente | Alta | F1-macro ≥ 0.80, recall Dropout ≥ 0.75 y matriz de confusión coherente con el conjunto de test. | INT_03 |
| PT_10 | Ausencia de fuga y reproducibilidad | Componente | Alta | Particiones disjuntas y estratificadas, escalador ajustado en train, horizonte temprano sin variables de segundo semestre y métricas reproducibles. | INT_03 |
| PT_11 | Rendimiento | Integración HTTP local | Alta | Con 200 alumnos y 1,000 inscripciones, cada ruta atiende 100 solicitudes con 10 hilos, todas HTTP 200 y p95 < 1.0 s. | INT_02 / INT_03 |
| PT_12 | Usabilidad | Aceptación | Media | Un tutor distingue una alerta RA_01 de una probabilidad ML al revisar un historial. Pendiente de ejecución de usabilidad. | INT_02 / INT_03 |
| PT_13 | Instalación | Integración local | Alta | Migración inicial equivalente al modelo, carga de demostración idempotente, reinicio SQLite y generación válida de configuración. | INT_02 |
| PT_14 | Regresión | Sistema vía API | Alta | Admin, operador y tutor completan el recorrido de catálogo, captura, alerta, seguimiento e inferencia. Historial, resumen, ambos CSV y eventos de bitácora coinciden con el recorrido. | INT_02 / INT_03 |

La búsqueda PT_02 en SQLite aplica `str.casefold()` a la matrícula, el nombre y la consulta. `ÁNGELA` encuentra `Ángela` y `ANGELA` encuentra `Angela`. Las tildes se conservan y `%` y `_` se tratan como caracteres literales. Para PostgreSQL, el código utiliza `icontains(..., autoescape=True)`. Esta ejecución usa SQLite.

La matriz de PT_07 toma las operaciones principales de la arquitectura y los permisos de importación y reportes del contrato HTTP. Cruza las 44 operaciones publicadas con los tres roles, incluye ambos endpoints públicos sin token y comprueba ocho operaciones con alumnos ajenos para los tres roles. Los casos de instalación existentes se ejecutan como PT_13. Las pruebas unitarias de `test_risk.py` conservan el identificador RA_01 y la cobertura de RF_10. [Arquitectura](arquitectura.md) · [Contrato HTTP](contrato-api.md)

## Ejecución y evidencias

Ejecutar desde la raíz del repositorio con las dependencias locales instaladas.

```bash
mkdir -p docs/pruebas
cd backend
.venv/bin/python -m pytest -q
set -o pipefail
{
  date -Iseconds
  .venv/bin/python --version
  .venv/bin/python -m pytest -v -rA --junitxml=../docs/pruebas/junit_backend.xml
} 2>&1 | tee ../docs/pruebas/evidencia_pytest_backend.txt
```

Los casos HTTP reutilizan el lifespan real, SQLite temporal y el modelo `1.0.0-pruebas` que `conftest.py` entrena una vez por sesión con datos locales. PT_06 ejecuta SQL contra su propia base temporal. PT_11 mide cada ruta en un lote separado después de una solicitud de calentamiento por ruta. El test actualiza `PT_11_rendimiento.json` con p50, p95, máximo, rendimiento y códigos HTTP. El lote de estudiantes solicita las 200 filas. Cada POST medido ejecuta el modelo y guarda la predicción.

Cada ejecución registra fecha, versión, entradas, resultado esperado, resultado obtenido, comparativa, decisión y evidencia. Se registra cada defecto real con un ID `BUG_BE_0X` y el caso esperado permanece ejecutable con `xfail(strict=True)`. Una aprobación inesperada obliga a revisar esa marca.

- [Matriz RF ↔ CU ↔ MOD ↔ PT ↔ pruebas](matriz-trazabilidad.md)
- [Resultados y decisión del backend](pruebas/resultados_backend.md)
- [Bitácora de defectos](pruebas/bugs_backend.md)
- [Evidencia previa de instalación PT_13](manual-instalacion/evidencia_PT_13.txt)
- [Contrato OpenAPI para frontend](openapi.json)

## Evidencia previa de IA

INT_03 registró una corrida anterior el `2026-11-03T03:12:05.822347+00:00` con modelo `1.0.0` y SHA-256 de datos `6bcfb6b3c826c4b8b9c7a99c063762748f6f462e24aabd26719ec2e55fed6135`. Pasaron 48 casos de backend y 2 controles de `ml/tests`. La evaluación del artefacto local reportó `matches_saved_metrics=true` con tolerancia absoluta de 1e-09. La comparativa RF_15 mantiene los ocho experimentos y la selección por CV dentro del horizonte temprano. [Contrato ML](contrato-ml.md)
