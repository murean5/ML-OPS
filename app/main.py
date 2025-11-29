"""Точка входа REST API."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.rest import routes
from app.core.logging import logger
from app.services.minio_service import minio_service

app = FastAPI(
    title="ML Service API",
    description="ML Service with REST and gRPC APIs",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes.router)

logger.info("REST API запущен")


@app.get("/")
async def root():
    """Корневой эндпоинт."""
    return {"message": "ML Service API", "docs": "/docs"}

