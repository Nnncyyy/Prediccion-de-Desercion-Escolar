from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str = "sqlite:///./sipde.db"
    jwt_secret: str = ""
    admin_email: str = ""
    admin_password: str = ""
    cors_origins: str = "http://localhost:5173"
    model_path: str = "ml/artifacts/dropout_model.joblib"
    model_config = SettingsConfigDict(env_file=str(Path(__file__).resolve().parents[1] / '.env'), extra='ignore')

settings = Settings()
