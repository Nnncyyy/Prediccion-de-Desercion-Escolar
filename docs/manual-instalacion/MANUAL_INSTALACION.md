# PT_13 · Manual de instalación de SIPDE

## MI_01 · Requisitos (RT_01, RT_02, RT_04)

- Python 3.11 o posterior, con `venv` y `pip`.
- Node.js 20 o posterior, con npm, para el frontend.
- Git para obtener el repositorio.
- SQLite viene con Python. PostgreSQL y Docker son opcionales.

La verificación del backend usó Python 3.13.5, pip 26.3 y Git 2.47.3. El entorno tenía FastAPI 0.162.0, Uvicorn 0.54.0, SQLAlchemy 2.1.6, Alembic 1.20.1, Pydantic 2.14.2, pydantic-settings 2.16.2, python-dotenv 1.2.4, PyJWT 2.15.1, python-multipart 0.0.34, psycopg 3.3.6, pandas 2.3.3, NumPy 2.5.4, scikit-learn 1.9.1, joblib 1.6.0, pytest 9.2.0 y HTTPX 0.28.1. Node.js 20.19.2 y npm 9.2.0 estaban disponibles en la máquina.

## MI_02 · Obtener el código

En Linux, macOS o Windows PowerShell:

```sh
git clone https://github.com/Nnncyyy/Prediccion-de-Desercion-Escolar.git
cd Prediccion-de-Desercion-Escolar
```

Los bloques de instalación parten de la raíz del repositorio, salvo donde se indique otro directorio.

## MI_03 · Backend con SQLite (RNF_01, RNF_03, RNF_06)

Crea el entorno virtual, instala las dependencias y genera `backend/.env`. El generador muestra el correo y la contraseña inicial del administrador. Guarda las credenciales en un sitio privado. Usa `--force` únicamente para reemplazar la configuración existente. Cambiar `ADMIN_PASSWORD` en el archivo no cambia la contraseña de una cuenta ya creada.

La instalación entrena el modelo antes de cargar la demostración. El archivo `.joblib` se genera localmente y está fuera de Git. El comando predeterminado usa `ml/data/dataset.csv` y genera el artefacto, el esquema y los ejemplos ACE_03. [Pipeline de entrenamiento](../../ml/README.md)

**Linux/macOS**

```bash
python3 -m venv backend/.venv
source backend/.venv/bin/activate
python -m pip install -r backend/scripts/requirements-instalacion.txt
python backend/scripts/generar_env.py
python ml/training/train.py
cd backend
python -m alembic upgrade head
python -m app.seed
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

**Windows PowerShell**

```powershell
py -3 -m venv backend/.venv
.\backend\.venv\Scripts\python.exe -m pip install -r backend/scripts/requirements-instalacion.txt
.\backend\.venv\Scripts\python.exe backend/scripts/generar_env.py
.\backend\.venv\Scripts\python.exe ml/training/train.py
Set-Location backend
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m app.seed
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

El seed es opcional y carga **DATOS FICTICIOS DE DEMOSTRACIÓN**. La primera ejecución imprime una contraseña compartida para los dos tutores y el operador si `SEED_PASSWORD` está vacía. Define esa variable en `backend/.env` si quieres conservar una contraseña conocida para las cuentas nuevas. Las predicciones de la demostración vinculan ejemplos del conjunto de prueba portugués con expedientes ficticios. Los códigos `DEMO-*` de materias son claves locales. [Mapa curricular de LCD](https://www.escom.ipn.mx/htmls/oferta/mapaCurrLCD2020.php), [Programa de Aprendizaje Automático de ESCOM](https://www.escom.ipn.mx/docs/oferta/uaoISC2020/machineLearning.pdf)

En otra terminal, comprueba el estado. En PowerShell usa `curl.exe`.

```bash
curl --fail http://127.0.0.1:8000/api/health
```

Abre [Swagger UI](http://127.0.0.1:8000/docs) y ejecuta `POST /api/auth/login` con el correo y la contraseña de administrador. Usa el campo `access_token` en **Authorize** y prueba `GET /api/dashboard`. La cuenta inicial también se crea al arrancar Uvicorn si omitiste el seed. [Contrato HTTP](../contrato-api.md)

## MI_04 · Frontend (RT_02)

Abre otra terminal en la raíz del repositorio.

**Linux/macOS**

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

**Windows PowerShell**

```powershell
Set-Location frontend
npm install
Copy-Item .env.example .env
npm run dev
```

`frontend/.env` configura `VITE_API_URL=http://localhost:8000`. Abre [SIPDE](http://localhost:5173) e inicia sesión con la cuenta de administrador que generaste.

## MI_05 · PostgreSQL y Alembic (opcional, RNF_03, RT_03)

1. Prepara una base vacía `sipde` y un usuario con permisos para crear tablas en su esquema. Al cambiar de motor, conserva un respaldo independiente de cualquier SQLite con datos.
2. En `backend/.env` fija `AUTO_CREATE_TABLES=false` y `DATABASE_URL=postgresql+psycopg://sipde:CAMBIAR_POSTGRES_PASSWORD@localhost:5432/sipde`. Sustituye el marcador por la contraseña de ese usuario. Codifica los caracteres reservados de la contraseña para una URL.
3. Desde `backend/`, aplica la migración con el entorno virtual. Después puedes ejecutar el seed si la base es para demostración y arrancar Uvicorn como en MI_03.

**Linux/macOS**

```bash
.venv/bin/python -m alembic upgrade head
.venv/bin/python -m alembic current
```

**Windows PowerShell**

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m alembic current
```

`DATABASE_URL` del entorno tiene prioridad sobre `backend/.env`. Para una ejecución puntual, `python -m alembic -x url=sqlite:///./sipde-prueba.sqlite upgrade head` tiene prioridad sobre ambas. Usa la misma base en el backend y en Alembic. La opción `AUTO_CREATE_TABLES=true` del backend sirve para desarrollo y pruebas. `create_all` crea las tablas nuevas y la estructura de tablas existentes requiere migraciones.

## MI_06 · Docker (opcional, RT_01, RT_03)

Se requiere Docker con BuildKit y Docker Compose 2.17 o posterior. Docker no estaba instalado en la máquina de desarrollo y este flujo quedó sin probar. El ejemplo levanta la API y PostgreSQL. Ejecuta el frontend como en MI_04.

Desde la raíz, genera `backend/.env` con MI_03 y ejecuta estos comandos en Linux, macOS o PowerShell:

```sh
docker compose --env-file backend/.env up --build -d
docker compose --env-file backend/.env logs backend
docker compose --env-file backend/.env exec backend python -m app.seed
docker compose --env-file backend/.env down
```

El contenedor entrena el modelo durante la construcción para usar la versión de scikit-learn de la propia imagen. En el arranque aplica Alembic después de que PostgreSQL esté listo. Usa el `POSTGRES_PASSWORD` generado, que se compone de caracteres seguros para URL. El comando `down` conserva el volumen con los datos. Si se reutiliza un volumen, usa la contraseña con la que fue inicializado PostgreSQL.

## MI_07 · Ejecutar pruebas (PT_13, RNF_03, RNF_06)

Desde la raíz, con las dependencias de MI_03 instaladas:

**Linux/macOS**

```bash
cd backend
.venv/bin/python -m pytest -q
.venv/bin/python -m pytest -q tests/test_instalacion.py
```

**Windows PowerShell**

```powershell
Set-Location backend
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pytest -q tests/test_instalacion.py
```

Las pruebas entrenan su propio modelo temporal y usan bases aisladas. CI aplica las migraciones sobre una SQLite temporal antes de pytest. [Evidencia de PT_13](evidencia_PT_13.txt)

## MI_08 · Solución de problemas

| Síntoma | Acción |
| --- | --- |
| `JWT_SECRET` inválido al iniciar | Usa un secreto aleatorio de al menos 24 caracteres, sin el prefijo `CAMBIAR`. Si necesitas regenerar todo el archivo, guarda primero tu configuración y ejecuta el generador con `--force`. |
| Puerto 8000 ocupado | Detén el proceso que lo usa o arranca Uvicorn con `--port 8001`. Cambia `VITE_API_URL` al mismo puerto y reinicia Vite. |
| ML responde 503 porque falta el modelo o el esquema | Ejecuta `python ml/training/train.py` desde la raíz con el entorno virtual, o usa su ejecutable de Python como en MI_03. Verifica que `MODEL_PATH` apunte al artefacto generado. |
| CORS bloquea el frontend | Agrega el origen exacto del frontend a `CORS_ORIGINS` en `backend/.env`, separado por coma si hay varios. `localhost` y `127.0.0.1` son orígenes distintos. Reinicia Uvicorn. |
| SQLite antigua con columnas faltantes o sin historial Alembic | Para datos descartables, detén el backend y ejecuta `python -m app.seed --reset` desde `backend/` con su Python virtual. Esto borra la base SQLite configurada, aplica Alembic y carga la demostración. También puedes borrar `backend/sipde.db` y repetir desde `alembic upgrade head`. Si necesitas conservar los datos, respalda la BD y migra sus datos a una base con el esquema actual. |
