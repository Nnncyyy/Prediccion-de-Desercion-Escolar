# SIPDE — Sistema Inteligente de Predicción de Deserción Escolar

**Proyecto académico | Ingeniería de Software para Sistemas Inteligentes | Equipo de 4 integrantes**

Monorepositorio con frontend React + TypeScript + Vite, API FastAPI + SQLAlchemy, BD SQLite de desarrollo (PostgreSQL opcional), evaluación de alertas académicas y módulo de aprendizaje automático.

> Estado: **base funcional de desarrollo**, no sistema institucional listo para producción. El motor de alertas académicas se basa en reglas; el estimador ML funciona solo después de entrenarlo. No se deben confundir las alertas de reglas con una probabilidad estadística de deserción.

## Inicio rápido (dos terminales)

Requisitos: Python 3.11+ y Node.js 20+.

**Terminal A — Backend**

```bash
cd backend
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env   # Windows PowerShell: Copy-Item ..\.env.example .env
# Edita JWT_SECRET, ADMIN_EMAIL y ADMIN_PASSWORD en backend/.env
uvicorn app.main:app --reload
```

API: http://localhost:8000/docs — Backend crea tablas y cuenta administradora en el primer arranque. Se requiere configurar contraseña y secreto antes de iniciarlo.

**Terminal B — Frontend**

```bash
cd frontend
npm install
cp .env.example .env    # Windows PowerShell: Copy-Item .env.example .env
npm run dev
```

Abre http://localhost:5173; inicia sesión con `ADMIN_EMAIL` y `ADMIN_PASSWORD` configurados en el backend.

## Qué funciona hoy
- Inicio de sesión y autorización mediante JWT, rol administrador inicial (API protegida).
- Alta, listado y detalle de estudiantes; registro de materias, periodos, inscripciones y calificaciones.
- Dashboard con conteos, desempeño básico y alertas **orientativas**, no validadas clínicamente ni institucionalmente.
- Predicción con modelo **solo si** se genera el archivo entrenado y se aporta el conjunto de variables completo mediante API.
- Esquema inicial de BD y pruebas automatizadas de salud y reglas.

## Entrenamiento IA (opcional, paso separado)

```bash
cd backend
python ../ml/training/train.py --csv ../ml/data/dataset.csv --out ../ml/artifacts/dropout_model.joblib
```

Dataset de partida: 4,424 registros, 35 columnas y clases `Dropout`, `Enrolled`, `Graduate`. **No** incluye empleo, horas de trabajo ni calificación por materia individual; estos campos adicionales se almacenan en la BD y alimentan alertas, **no** el modelo ML hasta disponer de datos históricos que los contengan. El endpoint `POST /api/ml/predict` exige un diccionario `features` con todas las variables del entrenamiento. La UI no ofrece aún formulario completo para esa inferencia.

**Advertencia:** el dataset y `EXPOESCOM.py` se incluyen como referencias académicas suministradas por el equipo; verificar derechos y permisos antes de hacer público el repositorio. La base de datos local, claves y artefactos ML están excluidos de Git.

## Colaboración
1. Rama principal `main` protegida; ramas `feature/INT_02-estudiantes`, etc.
2. Abrir issue con identificador `RF_XX` / `CU_XX` / `PT_XX`; trabajar en rama, hacer Pull Request, obtener revisión y ejecutar pruebas.
3. No subir `.env`, datos reales de alumnos ni contraseñas.
4. Reunión breve dos veces por semana; mantener `docs/plan-semanal.md` y `docs/matriz-trazabilidad.md` al día.

## Estructura
- `frontend/`: vistas, componentes, cliente API y estilos.
- `backend/app/`: rutas, entidades, acceso a datos, reglas, seguridad y servicio de predicción.
- `ml/`: conjunto de datos de muestra, entrenamiento, métricas y modelos locales.
- `docs/`: requisitos, arquitectura, casos de uso, planes de trabajo y pruebas.
- `tests/`: reservado para pruebas end-to-end.
- `.github/`: CI y plantilla Pull Request.

## Limitaciones importantes
- Almacenamiento SQLite es para desarrollo; configurar `DATABASE_URL` de PostgreSQL en producción y añadir migraciones Alembic.
- Los umbrales de alerta son configuraciones iniciales que deben validarse con responsables académicos.
- Endpoint de entrenamiento NO accesible desde la web: entrenar fuera de la API, con evaluación independiente.
- Faltan editar/desactivar alumnos, perfiles adicionales, seguimiento por tutor, reportes PDF y despliegue seguro; están planificados en `docs/plan-semanal.md`.
