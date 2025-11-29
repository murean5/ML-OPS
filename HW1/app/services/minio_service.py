"""Сервис для работы с MinIO."""

from minio import Minio
from minio.error import S3Error
from app.core.config import settings
from app.core.logging import logger


class MinIOService:
    """Сервис для работы с MinIO."""

    def __init__(self):
        """Инициализация сервиса."""
        self.client = None
        self.dvc_bucket = "dvc-storage"
        try:
            endpoint = settings.minio_endpoint
            endpoint = endpoint.replace('http://', '').replace('https://', '')
            
            self.client = Minio(
                endpoint=endpoint,
                access_key=settings.minio_access_key,
                secret_key=settings.minio_secret_key,
                secure=settings.minio_secure,
            )
            logger.info("MinIO инициализирован")
        except Exception as e:
            logger.warning(f"Не удалось инициализировать MinIO: {e}")

    def _ensure_bucket_exists(self, bucket_name: str):
        """
        Создать бакет если его нет.
        
        Args:
            bucket_name: Имя бакета
        """
        if self.client is None:
            return
            
        try:
            if self.client.bucket_exists(bucket_name=bucket_name):
                logger.info(
                    "Бакет уже существует в MinIO",
                    extra={"bucket": bucket_name},
                )
                return
            
            self.client.make_bucket(bucket_name=bucket_name)
            logger.info(
                "Создан бакет в MinIO",
                extra={"bucket": bucket_name},
            )
        except S3Error as e:
            if e.code == "BucketAlreadyOwnedByYou":
                logger.info(
                    "Бакет уже существует в MinIO",
                    extra={"bucket": bucket_name},
                )
            else:
                logger.error(
                    "Ошибка при создании бакета в MinIO",
                    extra={"error": str(e), "bucket": bucket_name},
                )
        except Exception as e:
            logger.error(
                "Ошибка при создании бакета в MinIO",
                extra={"error": str(e), "bucket": bucket_name},
            )


minio_service = MinIOService()

