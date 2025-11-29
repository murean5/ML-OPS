"""Pydantic схемы для API - только для валидации запросов/ответов."""

from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, List, Any, Optional
from datetime import datetime


class TrainRequest(BaseModel):
    """Запрос на обучение модели."""
    model_config = ConfigDict(extra="ignore", populate_by_name=False)
    model_type: str = Field(..., description="Тип модели (linear, random_forest)")
    dataset_id: str = Field(..., description="ID датасета")
    hyperparameters: Dict[str, Any] = Field(
        default_factory=dict, description="Гиперпараметры модели"
    )


class PredictRequest(BaseModel):
    """Запрос на получение предсказания."""
    model_config = ConfigDict(extra="ignore", populate_by_name=False)
    features: List[List[float]] | List[Dict[str, float]] = Field(
        ..., 
        description="Массив признаков для предсказания"
    )


class PredictResponse(BaseModel):
    """Ответ с предсказанием."""
    model_config = ConfigDict(extra="ignore", populate_by_name=False)
    predictions: List[float] = Field(..., description="Предсказания модели")
    model_id: str = Field(..., description="ID модели")


class ModelInfo(BaseModel):
    """Информация о модели."""
    model_config = ConfigDict(extra="ignore", populate_by_name=False)
    model_id: str
    model_type: str
    dataset_id: str
    hyperparameters: Dict[str, Any]
    created_at: datetime
    status: str
    metrics: Optional[Dict[str, Optional[float]]] = None
    clearml_model_id: Optional[str] = None


class DatasetInfo(BaseModel):
    """Информация о датасете."""
    model_config = ConfigDict(extra="ignore", populate_by_name=False)
    dataset_id: str
    file_name: str
    size: int
    created_at: datetime
    dvc_version: Optional[str] = None


class HealthResponse(BaseModel):
    """Ответ проверки здоровья сервиса."""
    model_config = ConfigDict(extra="ignore", populate_by_name=False)
    status: str = "healthy"
    version: str = "0.1.0"

