from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str = "sqlite:///./sipde.db"
    jwt_secret: str = ""
    admin_email: str = ""
    admin_password: str = ""
    cors_origins: str = "http://localhost:5173"
    model_path: str = "ml/artifacts/dropout_model.joblib"
    ml_umbral_medio: float = 0.33  # RN_01: ML_UMBRAL_MEDIO, categoría orientativa
    ml_umbral_alto: float = 0.66  # RN_01: ML_UMBRAL_ALTO, categoría orientativa
    model_config = SettingsConfigDict(env_file=str(Path(__file__).resolve().parents[1] / '.env'), extra='ignore')

settings = Settings()
