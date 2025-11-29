"""Конфигурация приложения."""

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass


class Settings:
    """Настройки приложения."""
    
    def __init__(self):
        self.api_host = os.getenv("API_HOST", "0.0.0.0")
        self.api_port = int(os.getenv("API_PORT", "8000"))
        self.grpc_port = int(os.getenv("GRPC_PORT", "50051"))

        self.minio_endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")
        self.minio_access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
        self.minio_secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin")
        self.minio_secure = os.getenv("MINIO_SECURE", "false").lower() in ("true", "1", "yes")

        self.clearml_api_host = os.getenv("CLEARML_API_HOST")
        self.clearml_web_host = os.getenv("CLEARML_WEB_HOST")
        self.clearml_api_access_key = os.getenv("CLEARML_API_ACCESS_KEY")
        self.clearml_api_secret_key = os.getenv("CLEARML_API_SECRET_KEY")

        self.dvc_remote = os.getenv("DVC_REMOTE", "minio")
        self.dvc_cache_dir = os.getenv("DVC_CACHE_DIR", ".dvc/cache")

        self.models_dir = os.getenv("MODELS_DIR", "models")
        self.datasets_dir = os.getenv("DATASETS_DIR", "data")


settings = Settings()
