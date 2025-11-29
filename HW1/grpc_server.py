"""Скрипт для запуска gRPC сервера."""

from app.api.grpc.service import serve
from app.core.config import settings
from app.core.logging import logger

if __name__ == "__main__":
    logger.info("Запуск gRPC сервера")
    serve(port=settings.grpc_port)

