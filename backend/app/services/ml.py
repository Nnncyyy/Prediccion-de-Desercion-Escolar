from pathlib import Path
import joblib, pandas as pd
from fastapi import HTTPException
from app.config import settings

BASE_DIR = Path(__file__).resolve().parents[3]

def predict(features: dict):
    path = Path(settings.model_path)
    if not path.is_absolute(): path = (BASE_DIR / path).resolve()
    if not path.is_file(): raise HTTPException(503,'Modelo no entrenado: ejecutar ml/training/train.py')
    artifact = joblib.load(path)  # Cargar SOLO artefactos entrenados localmente/confiables.
    columns = artifact['columns']
    missing = [c for c in columns if c not in features]
    if missing: raise HTTPException(422,detail={'missing_features':missing})
    row = pd.DataFrame([{c: features[c] for c in columns}])
    for c in artifact['numeric_columns']:
        row[c] = pd.to_numeric(row[c],errors='coerce')
    model=artifact['pipeline']
    probabilities=model.predict_proba(row)[0]
    result={str(k):round(float(p),4) for k,p in zip(model.classes_,probabilities)}
    return {'predicted_class':str(model.predict(row)[0]),'probabilities':result,'model_name':artifact['model_name'],'note':'Probabilidades de clases académicas, no alertas de reglas.'}
