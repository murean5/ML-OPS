"""Настройка логирования для приложения."""

import logging
import sys
from pythonjsonlogger import jsonlogger

log_handler = logging.StreamHandler(sys.stdout)
formatter = jsonlogger.JsonFormatter(
    '%(asctime)s %(name)s %(levelname)s %(message)s %(pathname)s %(lineno)d'
)
log_handler.setFormatter(formatter)

logger = logging.getLogger("ml-service")
logger.setLevel(logging.INFO)
logger.addHandler(log_handler)

logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("clearml").setLevel(logging.WARNING)
