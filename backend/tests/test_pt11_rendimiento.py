"""Medición local de latencia HTTP con inferencia y persistencia reales."""

from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from math import ceil
from pathlib import Path
import platform
import sqlite3
from statistics import median
from time import perf_counter

from app import database
from app.models import Enrollment, Period, Student, Subject
from helpers import student_data

WORKERS = 10
REQUESTS = 100
P95_LIMIT = 1.0
STUDENTS = 200
SUBJECTS = 5
EVIDENCE = Path(__file__).resolve().parents[2] / 'docs' / 'pruebas' / 'PT_11_rendimiento.json'


def seed_workload():
    students = [Student(**student_data(f'PT11-{number:03d}')) for number in range(STUDENTS)]
    subjects = [Subject(code=f'PT11-M{number}', name=f'Materia {number}') for number in range(SUBJECTS)]
    period = Period(code='PT11-1', name='Periodo de rendimiento')
    with database.SessionLocal() as db:
        db.add_all([*students, *subjects, period])
        db.flush()
        student_ids = [student.id for student in students]
        db.add_all(
            Enrollment(student_id=student_id, subject_id=subject.id, period_id=period.id,
                       term=period.code, grade=5 + index)
            for student_id in student_ids
            for index, subject in enumerate(subjects)
        )
        db.commit()
    return student_ids


def measure(client, headers, method, path, options):
    def send(index):
        started = perf_counter()
        response = client.request(method, path, headers=headers, **options(index))
        return perf_counter() - started, response.status_code

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        started = perf_counter()
        samples = list(pool.map(send, range(REQUESTS)))
        elapsed = perf_counter() - started
    durations = sorted(duration for duration, _ in samples)
    statuses = Counter(status for _, status in samples)
    return {
        'peticiones': len(samples),
        'respuestas_por_codigo': dict(statuses),
        'p50_s': median(durations),
        'p95_s': durations[ceil(0.95 * len(durations)) - 1],
        'max_s': durations[-1],
        'peticiones_por_s': len(samples) / elapsed,
        'duracion_lote_s': elapsed,
    }


def test_pt11_latencia_con_carga(api_client, auth_headers, real_features, trained_model):
    """PT_11 · CU_02/CU_04/CU_06/RF_03/RF_09/RF_12/RNF · Medir tres rutas con 10 hilos. Esperado: 100 respuestas 200 por ruta y p95 menor que 1 s."""
    student_ids = seed_workload()
    endpoints = [
        ('GET', '/api/students', lambda _: {'params': {'limit': STUDENTS}}),
        ('GET', '/api/dashboard', lambda _: {}),
        ('POST', '/api/ml/predict', lambda index: {
            'json': {'student_id': student_ids[index], 'features': real_features},
        }),
    ]

    # Una solicitud de calentamiento por ruta queda fuera de su respectivo lote.
    evidence = {
        'id': 'PT_11',
        'fecha_utc': datetime.now(timezone.utc).isoformat(),
        'entorno': {'python': platform.python_version(), 'sistema': platform.system(),
                    'arquitectura': platform.machine(), 'sqlite': sqlite3.sqlite_version,
                    'modelo': trained_model.artifact['version']},
        'carga': {'alumnos': STUDENTS, 'inscripciones': STUDENTS * SUBJECTS, 'hilos': WORKERS,
                  'peticiones_por_ruta': REQUESTS, 'calentamiento_por_ruta': 1,
                  'limit_students': STUDENTS},
        'p95_limite_s_exclusivo': P95_LIMIT,
        'metodo_p95': 'rango más próximo (ceil(0.95 × n))',
        'resultados': {},
    }
    errors = []
    for method, path, options in endpoints:
        route = f'{method} {path}'
        warmup = api_client.request(method, path, headers=auth_headers, **options(0))
        stats = measure(api_client, auth_headers, method, path, options)
        stats['codigo_calentamiento'] = warmup.status_code
        evidence['resultados'][route] = stats
        if warmup.status_code != 200 or stats['respuestas_por_codigo'] != {200: REQUESTS}:
            errors.append(f'{route}: calentamiento={warmup.status_code}, lote={stats["respuestas_por_codigo"]}')
        if stats['p95_s'] >= P95_LIMIT:
            errors.append(f'{route}: p95={stats["p95_s"]:.6f} s, límite exclusivo {P95_LIMIT} s')

    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    assert not errors, '\n'.join(errors)
