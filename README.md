# SIPDE — Sistema Inteligente de Predicción de Deserción Escolar

Proyecto académico de Ingeniería de Software para Sistemas Inteligentes. Reúne una aplicación React y TypeScript, una API FastAPI y SQLAlchemy, SQLite para desarrollo y PostgreSQL opcional.

## Inicio rápido (PT_13)

Con Python 3.11+, Node.js 20+ y Git, desde la raíz en Linux o macOS:

```bash
python3 -m venv backend/.venv
source backend/.venv/bin/activate
python -m pip install -r backend/scripts/requirements-instalacion.txt
python backend/scripts/generar_env.py
python ml/training/train.py
cd backend
python -m alembic upgrade head
python -m app.seed
python -m uvicorn app.main:app
```

En otra terminal, entra en `frontend/`, ejecuta `npm install`, copia `.env.example` a `.env` y ejecuta `npm run dev`. Usa las credenciales generadas para iniciar sesión. [Aplicación](http://localhost:5173), [Swagger UI](http://localhost:8000/docs)

El manual incluye PowerShell, configuración de PostgreSQL, Docker opcional y pruebas. [Manual de instalación](docs/manual-instalacion/MANUAL_INSTALACION.md)

## Qué funciona hoy

- Salud de la API, inicio de sesión con JWT, perfil y cambio de contraseña. El administrador gestiona cuentas de administración, tutoría y operación.
- Altas, búsquedas y actualización de expedientes y datos laborales, bajas lógicas, reactivación y asignación a tutores.
- Catálogos de carreras, periodos y materias, gestión de inscripciones y calificaciones, y notas de seguimiento de tutoría.
- Alertas académicas RA_01 y dashboard con indicadores académicos y de ML según el rol y el alcance del usuario.
- Consulta del esquema, inferencia con el modelo entrenado e historial de predicciones desde la API. La inferencia usa variables del dataset histórico y RA_01 usa las calificaciones y los datos laborales del expediente.
- Bitácora de operaciones para administradores.
- Importación CSV de alumnos e inscripciones, con validación previa y plantillas. Reportes de indicadores y exportación CSV de alumnos y predicciones.

[Contrato de la API](docs/contrato-api.md), [Entrenamiento y procedencia del dataset](ml/README.md)

## Estructura y colaboración

- `backend/app/` contiene las rutas, entidades, reglas y servicios. `backend/alembic/` contiene las migraciones.
- `frontend/` contiene las vistas y el cliente de la API.
- `ml/` contiene el conjunto de datos académico, el entrenamiento y las métricas.
- `docs/` contiene requisitos, arquitectura y pruebas.

Relaciona cada contribución con su identificador `RF_XX`, `CU_XX` o `PT_XX`. Ejecuta las pruebas antes de enviar cambios y conserva los secretos y los expedientes reales fuera del repositorio.
