"""REST API эндпоинты."""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import List
from app.schemas.models import (
    TrainRequest,
    PredictRequest,
    PredictResponse,
    ModelInfo,
    DatasetInfo,
    HealthResponse,
)
from app.services.model_service import model_service
from app.services.dataset_service import dataset_service
from app.core.logging import logger

router = APIRouter(prefix="/api/v1", tags=["ML Service"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Проверка статуса сервиса."""
    logger.info("Проверка здоровья сервиса")
    return HealthResponse(status="healthy", version="0.1.0")


@router.get("/models/available", response_model=List[str])
async def get_available_models():
    """Получить список доступных типов моделей."""
    logger.info("Запрос списка доступных моделей")
    return model_service.get_available_model_types()


@router.get("/models", response_model=List[ModelInfo])
async def get_models():
    """Получить список всех обученных моделей."""
    logger.info("Запрос списка моделей")
    models = model_service.get_all_models()
    return [ModelInfo(**model) for model in models]


@router.post("/models/train", response_model=ModelInfo)
async def train_model(request: TrainRequest):
    """Обучить модель."""
    logger.info(
        "Запрос на обучение модели",
        extra={"model_type": request.model_type, "dataset_id": request.dataset_id},
    )

    try:
        X, y = dataset_service.load_dataset(request.dataset_id)

        model_id = model_service.train_model(
            model_type=request.model_type,
            dataset_id=request.dataset_id,
            hyperparameters=request.hyperparameters,
            X=X,
            y=y,
        )

        model_info = model_service.get_model(model_id)
        if not model_info:
            raise HTTPException(status_code=500, detail="Ошибка при создании модели")

        return ModelInfo(**model_info)
    except ValueError as e:
        logger.error("Ошибка при обучении модели")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Неожиданная ошибка при обучении модели")
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка: {str(e)}")


@router.post("/models/{model_id}/predict", response_model=PredictResponse)
async def predict(model_id: str, request: PredictRequest):
    """Получить предсказания от модели."""
    logger.info("Запрос на получение предсказаний")

    try:
        predictions = model_service.predict(model_id, request.features)
        return PredictResponse(predictions=predictions, model_id=model_id)
    except ValueError as e:
        logger.error("Ошибка при получении предсказаний")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Неожиданная ошибка при получении предсказаний")
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка: {str(e)}")


@router.put("/models/{model_id}/retrain", response_model=ModelInfo)
async def retrain_model(
    model_id: str,
    dataset_id: str = Form(...),
    hyperparameters: str = Form("{}"),
):
    """Переобучить модель."""
    logger.info("Запрос на переобучение модели")

    try:
        import json
        hyperparams_dict = json.loads(hyperparameters) if hyperparameters else {}

        X, y = dataset_service.load_dataset(dataset_id)

        new_model_id = model_service.retrain_model(
            model_id=model_id,
            dataset_id=dataset_id,
            hyperparameters=hyperparams_dict,
            X=X,
            y=y,
        )

        model_info = model_service.get_model(new_model_id)
        if not model_info:
            raise HTTPException(status_code=500, detail="Ошибка при создании модели")

        return ModelInfo(**model_info)
    except ValueError as e:
        logger.error("Ошибка при переобучении модели")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Неожиданная ошибка при переобучении модели")
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка: {str(e)}")


@router.get("/models/{model_id}", response_model=ModelInfo)
async def get_model(model_id: str):
    """Получить информацию о модели."""
    logger.info(f"Запрос информации о модели {model_id}")
    
    model_info = model_service.get_model(model_id)
    if not model_info:
        raise HTTPException(status_code=404, detail=f"Модель {model_id} не найдена")
    
    return ModelInfo(**model_info)


@router.delete("/models/{model_id}")
async def delete_model(model_id: str):
    """Удалить модель."""
    logger.info("Запрос на удаление модели")

    success = model_service.delete_model(model_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Модель {model_id} не найдена")

    return {"message": f"Модель {model_id} успешно удалена"}


@router.get("/datasets", response_model=List[DatasetInfo])
async def get_datasets():
    """Получить список всех датасетов."""
    logger.info("Запрос списка датасетов")
    datasets = dataset_service.get_all_datasets()
    return [DatasetInfo(**dataset) for dataset in datasets]


@router.post("/datasets/upload", response_model=DatasetInfo)
async def upload_dataset(
    file: UploadFile = File(...),
    format: str = Form("csv"),
):
    """Загрузить датасет."""
    logger.info("Запрос на загрузку датасета")

    if format not in ["csv", "json"]:
        raise HTTPException(status_code=400, detail="Поддерживаются только форматы csv и json")

    try:
        content = await file.read()
        dataset_id = dataset_service.upload_dataset(file.filename, content, format)

        dataset_info = dataset_service.get_dataset(dataset_id)
        if not dataset_info:
            raise HTTPException(status_code=500, detail="Ошибка при загрузке датасета")

        return DatasetInfo(**dataset_info)
    except Exception as e:
        logger.error(f"Ошибка при загрузке датасета: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка: {str(e)}")


@router.get("/datasets/{dataset_id}", response_model=DatasetInfo)
async def get_dataset(dataset_id: str):
    """Получить информацию о датасете."""
    logger.info(f"Запрос информации о датасете {dataset_id}")
    
    dataset_info = dataset_service.get_dataset(dataset_id)
    if not dataset_info:
        raise HTTPException(status_code=404, detail=f"Датасет {dataset_id} не найден")
    
    return DatasetInfo(**dataset_info)


@router.delete("/datasets/{dataset_id}")
async def delete_dataset(dataset_id: str):
    """Удалить датасет."""
    logger.info("Запрос на удаление датасета")

    success = dataset_service.delete_dataset(dataset_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Датасет {dataset_id} не найден")

    return {"message": f"Датасет {dataset_id} успешно удален"}
