# syntax=docker/dockerfile:1
# RT_01 / RT_03 · API SIPDE y migraciones en PostgreSQL.
FROM python:3.12-slim

WORKDIR /sipde/backend
COPY requirements.txt ./
COPY scripts/requirements-instalacion.txt ./scripts/
RUN python -m pip install --no-cache-dir -r scripts/requirements-instalacion.txt

COPY . ./
COPY --from=ml common.py /sipde/ml/common.py
COPY --from=ml data/dataset.csv /sipde/ml/data/dataset.csv
COPY --from=ml training/ /sipde/ml/training/
RUN python ../ml/training/train.py

EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
