# Plan operativo detallado y simultáneo — SIPDE

**Periodo:** 26 oct.–11 dic. 2026. **Hito interno:** MVP integrado 29 nov.; congelación 4 dic.; reserva 5–6 dic.; entrega 7–11 dic.

| Semana | INT_01 Ingeniería y documentación | INT_02 Backend y BD | INT_03 IA y datos | INT_04 Frontend | Evidencia / aceptación |
|---|---|---|---|---|---|
| S01 · 26 oct.–1 nov. | Definir problema, alcance, actores ACT, RF/RNF/RT, backlog, capítulo 1 | Inicializar FastAPI, SQLAlchemy, esquema ER BD_*, configuración .env | Auditar CSV, etiquetas, variables disponibles, línea base EXPOESCOM.py | Crear Vite, diseño visual, login prototipo, navegación de seis módulos | Repositorio funcional, documento v0.1, API health y home |
| S02 · 2–8 nov. | CU_01–CU_06 con flujos, reglas RN y trazabilidad | Autenticación JWT, usuarios, restricciones, primeras migraciones | Pipeline sin fuga, división estratificada, baseline ML_01 | Integrar login real, maquetar directorio y formularios | Login end-to-end, diagrama casos uso, evaluación inicial |
| S03 · 9–15 nov. | Gantt/PERT, factibilidad y riesgos RSK; revisar CU | Completar CRUD, catálogo materias y relaciones académicas | Comparar regresión logística y árbol; recall dropout, F1 macro | Conectar formularios estudiantes, materias, estados de error | Alta/listado/edición verificables, pruebas de API y de modelo |
| S04 · 16–22 nov. | Actualizar arquitectura, RN, matriz trazabilidad y capítulo modelado | Calificaciones, periodos, historial, API predicción y auditoría inicial | Guardar modelo versionado, validar variables, alertas transparentes | Páginas de historial, alertas, indicadores básicos | Flujo completo registrar→calificar→alertar; demo integrada |
| S05 · 23–29 nov. | Plan/guiones PT_*, pruebas de aceptación, avance de reporte | Manejo errores, perfiles de acceso, reportes, soporte PostgreSQL | Pruebas de IA, calibración y documentación de limitaciones | Dashboard con gráficas, filtros y estados responsivos | MVP integrado 29 nov., suite automática, capturas y métricas reales |
| S06 · 30 nov.–4 dic. | Integrar capítulos, referencias, matriz final y revisión de alcance | Corregir incidencias, guía instalación, congelar API | Reporte experimental, análisis resultados y figuras | Manual usuario, presentación, video de 20 min con equipo | Paquete candidato final, manuales, video, demostración ensayada |
| Reserva · 5–6 dic. | Auditoría final y checklist de identificación | Prueba instalación desde cero | Reproducir métricas y artefactos | Revisar accesibilidad y capturas | ZIP/repositorio probado en equipo distinto |
| Entrega · 7–11 dic. | Presentar y controlar versión final | Apoyo demostración | Explicar métricas ML | Demostrar interfaz | Equipo completo presente; rúbrica cubierta |

## Rutina de trabajo
- Lunes: planificación de tareas con identificadores, criterios de aceptación y responsable.
- Miércoles: sincronización de contratos API y pantallas; resolver bloqueos.
- Viernes: PRs revisados, demo semanal, actualizar documentación y pruebas.
- No mezclar cambios de código en `main` sin revisión. Una funcionalidad solo se da por finalizada cuando su flujo está probado y documentado.

## Dependencias críticas
- BD y contrato de campos → CRUD → formularios frontend.
- Script entrenado y esquema de variables → API ML → formulario inferencia.
- Materias + inscripciones + calificaciones → motor de alertas → dashboard.
- Flujo integrado → pruebas de aceptación → manual/video.
