# ARQ_01 — Arquitectura de SIPDE

```mermaid
flowchart TD
    U[ACT_01 Administrador / ACT_02 Tutor] --> FE[React + TypeScript]
    FE -->|HTTP JSON + JWT| API[FastAPI]
    API --> BD[(SQLite dev / PostgreSQL opcional)]
    API --> RA[RA_01 Alertas por reglas]
    API --> ML[ML_01 scikit-learn model.joblib]
    CSV[dataset.csv histórico] --> TRAIN[Entrenamiento offline]
    TRAIN --> ML
```

Backend usa módulos `config`, `models`, `schemas`, `security` y `services`. Frontend concentra el cliente HTTP en `src/api.ts` y la interfaz en `src/App.tsx` (dividir por módulos en sprint 2). El contrato del API se documenta automáticamente en `/docs`.

**Decisión arquitectónica:** monolito modular sin microservicios. Autenticación inicial JWT, pruebas y CI. Falta migración Alembic, permisos granulares, registro de auditoría, copias de seguridad y seguridad para producción.
