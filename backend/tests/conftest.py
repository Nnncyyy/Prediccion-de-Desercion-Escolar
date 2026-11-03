"""INT_03 · RF_08/RF_09/RNF_06: fixtures aisladas para PT_08–PT_10 e integración API.

Objetivo: entrenar el candidato real sin artefactos locales ni matplotlib.
Resultado esperado: modelo temporal reproducible en menos de 60 segundos y BD temporal.
"""
from argparse import Namespace
import asyncio
from pathlib import Path
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'backend'))

import joblib
import pytest

from ml.common import CONFIG_RECOMENDADA, DATA_PATH, FEATURE_SETS, load_dataset, make_target, split_train_test
from ml.training.train import export_examples, save_artifact, training_data_summary
from ml.training.workflow import cv_summary, evaluate_model, fit_search


@pytest.fixture(scope='session')
def trained_model(tmp_path_factory):
    """PT_08/PT_09/PT_10: entrena por las mismas funciones que el comando oficial."""
    started = perf_counter()
    directory = tmp_path_factory.mktemp('int03_ml')
    config = CONFIG_RECOMENDADA
    frame = load_dataset()
    X_train, X_test, y_train, y_test = split_train_test(
        frame[FEATURE_SETS[config['conjunto']]], make_target(frame.Target, config['tarea']))
    search = fit_search(config['modelo'], X_train, y_train)
    metrics, _ = evaluate_model(search.best_estimator_, X_test, y_test, config['tarea'])
    cv = cv_summary(search, X_train, y_train)
    args = Namespace(csv=DATA_PATH, out=directory / 'dropout_model.joblib', version='1.0.0-pruebas', **config)
    save_artifact(args, frame, search, metrics, cv,
                  training_data_summary(frame, X_train, X_test, y_train, y_test))
    export_examples(args, frame, search.best_estimator_)
    assert perf_counter() - started < 60, 'INT_03: el entrenamiento de sesión excede 60 s'
    from app.config import settings
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(settings, 'model_path', str(args.out))
        yield Namespace(artifact=joblib.load(args.out), path=args.out, frame=frame,
                        X_train=X_train, X_test=X_test, y_train=y_train, y_test=y_test,
                        metrics=metrics, search=search)


@pytest.fixture
def real_features(trained_model):
    """PT_08: entrega una copia independiente de una fila real de test."""
    return trained_model.X_test.iloc[0].to_dict()


def api_event_loop():
    """PT_07 parcial: mantiene activo el bucle ASGI aun si el sandbox bloquea socketpair.

    TestClient comunica hilos por memoria; este latido permite procesar sus tareas
    sin depender del aviso por socket local. No cambia la aplicación ni omite lifespan.
    """
    loop = asyncio.new_event_loop()

    def heartbeat():
        loop.call_later(0.01, heartbeat)

    loop.call_soon(heartbeat)
    return loop


@pytest.fixture
def api_client(trained_model, tmp_path, monkeypatch):
    """PT_07 parcial / RF_09: arranca el lifespan real contra una BD SQLite temporal."""
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.config import settings
    from app import database

    url = f'sqlite:///{tmp_path / "int03_api.sqlite"}'
    engine = create_engine(url, connect_args={'check_same_thread': False})
    sessions = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(settings, 'database_url', url)
    monkeypatch.setattr(settings, 'jwt_secret', 'INT_03_clave_temporal_exclusiva_de_pruebas')
    monkeypatch.setattr(settings, 'admin_email', 'int03@example.test')
    monkeypatch.setattr(settings, 'admin_password', 'INT_03_password_solo_pruebas')
    monkeypatch.setattr(database, 'engine', engine)
    monkeypatch.setattr(database, 'SessionLocal', sessions)
    from app import main
    monkeypatch.setattr(main, 'engine', engine)
    monkeypatch.setattr(main, 'SessionLocal', sessions)
    try:
        with TestClient(main.app, backend_options={'loop_factory': api_event_loop}) as client:
            yield client
    finally:
        engine.dispose()


@pytest.fixture
def auth_headers(api_client):
    """PT_07 parcial: inicia sesión con el administrador de settings del entorno temporal."""
    from app.config import settings
    response = api_client.post('/api/auth/login', json={
        'email': settings.admin_email, 'password': settings.admin_password,
    })
    assert response.status_code == 200
    return {'Authorization': f'Bearer {response.json()["access_token"]}'}
