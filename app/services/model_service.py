"""Сервис управления моделями."""

import os
import uuid
import json
from datetime import datetime
from typing import Dict, Optional, List, Union
from app.models import LinearModel, RandomForestModel, BaseMLModel
from app.core.config import settings
from app.core.logging import logger
from app.services.clearml_service import ClearMLService
from app.services.minio_service import minio_service


class ModelService:
    """Сервис для управления ML моделями."""

    def __init__(self):
        """Инициализация сервиса."""
        self.models: Dict[str, Dict] = {}
        self.models_dir = settings.models_dir
        os.makedirs(self.models_dir, exist_ok=True)
        self.metadata_file = os.path.join(self.models_dir, "models_metadata.json")
        self.clearml_service = ClearMLService()
        self._load_models_from_disk()
        logger.info("Инициализирован ModelService")
    
    def _load_models_from_disk(self):
        """Загрузить метаданные моделей из файловой системы."""
        if os.path.exists(self.metadata_file):
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for model_id, model_info in data.items():
                        if isinstance(model_info.get('created_at'), str):
                            try:
                                model_info['created_at'] = datetime.fromisoformat(model_info['created_at'])
                            except:
                                model_info['created_at'] = datetime.now()
                        self.models[model_id] = model_info
                    logger.info(f"Загружено {len(self.models)} моделей из метаданных")
            except Exception as e:
                logger.warning(f"Не удалось загрузить метаданные моделей: {e}")
        
        if os.path.exists(self.models_dir):
            for file_name in os.listdir(self.models_dir):
                if file_name.endswith('.pkl') and file_name != '.gitkeep':
                    model_id = file_name[:-4]
                    if model_id not in self.models:
                        model_path = os.path.join(self.models_dir, file_name)
                        self.models[model_id] = {
                            "model_id": model_id,
                            "model_type": "linear",
                            "dataset_id": "unknown",
                            "hyperparameters": {},
                            "created_at": datetime.fromtimestamp(os.path.getmtime(model_path)),
                            "status": "trained",
                            "model_path": model_path,
                            "clearml_model_id": None,
                            "metrics": None,
                        }
                        logger.info(f"Найдена модель без метаданных: {model_id}")
    
    def _save_model_metadata(self, model_id: Optional[str] = None):
        """Сохранить метаданные моделей в файл."""
        try:
            data = {}
            for mid, info in self.models.items():
                if model_id is None or mid == model_id:
                    info_copy = info.copy()
                    if isinstance(info_copy.get('created_at'), datetime):
                        info_copy['created_at'] = info_copy['created_at'].isoformat()
                    data[mid] = info_copy
            
            all_data = {}
            if os.path.exists(self.metadata_file):
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    all_data = json.load(f)
            
            all_data.update(data)
            
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(all_data, f, indent=2, ensure_ascii=False, default=str)
        except Exception as e:
            logger.warning(f"Не удалось сохранить метаданные модели: {e}")

    def get_available_model_types(self) -> List[str]:
        """
        Получить список доступных типов моделей.

        Returns:
            Список названий типов моделей
        """
        return ["linear", "random_forest"]

    def create_model(self, model_type: str, hyperparameters: Dict) -> BaseMLModel:
        """
        Создать экземпляр модели по типу.

        Args:
            model_type: Тип модели
            hyperparameters: Гиперпараметры модели

        Returns:
            Экземпляр модели

        Raises:
            ValueError: Если тип модели неизвестен
        """
        if model_type == "linear":
            return LinearModel(hyperparameters)
        elif model_type == "random_forest":
            return RandomForestModel(hyperparameters)
        else:
            raise ValueError(f"Неизвестный тип модели: {model_type}")

    def train_model(
        self,
        model_type: str,
        dataset_id: str,
        hyperparameters: Dict,
        X: List[List[float]],
        y: List[float],
    ) -> str:
        """
        Обучить модель.

        Args:
            model_type: Тип модели
            dataset_id: ID датасета
            hyperparameters: Гиперпараметры
            X: Признаки
            y: Целевая переменная

        Returns:
            ID обученной модели
        """
        model_id = str(uuid.uuid4())
        logger.info(
            "Начало обучения модели",
            extra={
                "model_id": model_id,
                "model_type": model_type,
                "dataset_id": dataset_id,
            },
        )

        task = None
        if self.clearml_service.initialized:
            task = self.clearml_service.create_experiment(model_id, model_type, hyperparameters, dataset_id)
            if task:
                task.logger.report_scalar(
                    title="Training Progress",
                    series="status",
                    value=0.0,
                    iteration=0
                )

        model = self.create_model(model_type, hyperparameters)
        metrics = model.train(X, y)
        
        if task:
            for metric_name, metric_value in metrics.items():
                if metric_value is not None and not (isinstance(metric_value, float) and (metric_value != metric_value or metric_value == float('inf'))):
                    task.logger.report_scalar(
                        title="Training Metrics",
                        series=metric_name,
                        value=float(metric_value),
                        iteration=1
                    )

        model_path = os.path.join(self.models_dir, f"{model_id}.pkl")
        model.save(model_path)

        clearml_model_id = self.clearml_service.save_model(
            model_id=model_id,
            model_type=model_type,
            model_path=model_path,
            hyperparameters=hyperparameters,
            dataset_id=dataset_id,
            metrics=metrics,
            task=task,
        )
        
        self._save_model_to_minio(model_id, model_path)

        clean_metrics = {}
        if metrics:
            import math
            for key, value in metrics.items():
                if isinstance(value, float):
                    if math.isnan(value) or math.isinf(value):
                        continue
                    else:
                        clean_metrics[key] = value
                elif value is not None:
                    clean_metrics[key] = value
        
        self.models[model_id] = {
            "model_id": model_id,
            "model_type": model_type,
            "dataset_id": dataset_id,
            "hyperparameters": hyperparameters,
            "created_at": datetime.now(),
            "status": "trained",
            "model_path": model_path,
            "clearml_model_id": clearml_model_id,
            "metrics": clean_metrics if clean_metrics else None,
        }
        
        self._save_model_metadata(model_id)

        logger.info(
            "Модель успешно обучена",
            extra={"model_id": model_id, "clearml_model_id": clearml_model_id},
        )

        return model_id

    def get_model(self, model_id: str) -> Optional[Dict]:
        """
        Получить информацию о модели.

        Args:
            model_id: ID модели

        Returns:
            Словарь с информацией о модели или None
        """
        return self.models.get(model_id)

    def get_all_models(self) -> List[Dict]:
        """
        Получить список всех моделей.

        Returns:
            Список словарей с информацией о моделях
        """
        return list(self.models.values())

    def _convert_features_to_list(self, features: Union[List[List[float]], List[Dict[str, float]]]) -> List[List[float]]:
        """
        Конвертировать признаки в список списков.
        
        Args:
            features: Признаки в виде списка списков или списка словарей
            
        Returns:
            Список списков признаков
        """
        if not features:
            return []
        
        if isinstance(features[0], list):
            return features
        
        if isinstance(features[0], dict):
            keys = list(features[0].keys())
            keys.sort()
            
            result = []
            for item in features:
                values = [float(item.get(key, 0.0)) for key in keys]
                result.append(values)
            
            logger.info(
                "Конвертированы признаки из словарей в списки",
                extra={"samples": len(result), "features": len(keys), "keys": keys}
            )
            return result
        
        raise ValueError(f"Неподдерживаемый формат признаков: {type(features[0]) if features else 'empty'}")
    
    def _save_model_to_minio(self, model_id: str, model_path: str):
        """Сохранить модель в MinIO напрямую (резервный вариант)."""
        if not minio_service.client:
            return
        
        try:
            bucket_name = "clearml-models"
            minio_service._ensure_bucket_exists(bucket_name)
            
            object_name = f"models/{model_id}.pkl"
            
            with open(model_path, 'rb') as file_data:
                file_stat = os.stat(model_path)
                minio_service.client.put_object(
                    bucket_name=bucket_name,
                    object_name=object_name,
                    data=file_data,
                    length=file_stat.st_size,
                    content_type='application/octet-stream'
                )
            
            logger.info(
                "Модель сохранена в MinIO",
                extra={"model_id": model_id, "bucket": bucket_name, "object": object_name}
            )
        except Exception as e:
            logger.error(
                "Ошибка при сохранении модели в MinIO",
                extra={"error": str(e), "model_id": model_id}
            )
            raise

    def predict(self, model_id: str, features: Union[List[List[float]], List[Dict[str, float]]]) -> List[float]:
        """
        Получить предсказания от модели.

        Args:
            model_id: ID модели
            features: Признаки для предсказания (список списков или список словарей)

        Returns:
            Список предсказаний

        Raises:
            ValueError: Если модель не найдена
        """
        model_info = self.models.get(model_id)
        if not model_info:
            raise ValueError(f"Модель {model_id} не найдена")

        X = self._convert_features_to_list(features)

        model = self.create_model(
            model_info["model_type"], model_info["hyperparameters"]
        )
        clearml_model_id = model_info.get("clearml_model_id")
        if clearml_model_id:
            model_path = self.clearml_service.load_model(clearml_model_id, model_id)
            if model_path and os.path.exists(model_path):
                model.load(model_path)
                logger.info(f"Модель {model_id} загружена из ClearML")
            else:
                model_path = model_info.get("model_path")
                if model_path and os.path.exists(model_path):
                    model.load(model_path)
                    logger.info(f"Модель {model_id} загружена локально")
                else:
                    raise ValueError(f"Модель {model_id} не может быть загружена (ни из ClearML, ни локально)")
        else:
            model_path = model_info.get("model_path")
            if model_path and os.path.exists(model_path):
                model.load(model_path)
                logger.info(f"Модель {model_id} загружена локально")
            else:
                raise ValueError(f"Модель {model_id} не найдена локально и нет ClearML ID")

        return model.predict(X)

    def retrain_model(
        self,
        model_id: str,
        dataset_id: str,
        hyperparameters: Optional[Dict],
        X: List[List[float]],
        y: List[float],
    ) -> str:
        """
        Переобучить модель.

        Args:
            model_id: ID существующей модели
            dataset_id: ID датасета
            hyperparameters: Новые гиперпараметры (опционально)
            X: Признаки
            y: Целевая переменная

        Returns:
            ID новой модели

        Raises:
            ValueError: Если исходная модель не найдена
        """
        old_model_info = self.models.get(model_id)
        if not old_model_info:
            raise ValueError(f"Модель {model_id} не найдена")

        new_hyperparameters = hyperparameters or old_model_info["hyperparameters"]
        model_type = old_model_info["model_type"]

        new_model_id = self.train_model(
            model_type, dataset_id, new_hyperparameters, X, y
        )

        logger.info(
            "Модель переобучена",
            extra={"old_model_id": model_id, "new_model_id": new_model_id},
        )

        return new_model_id

    def _save_model_metadata(self, model_id: Optional[str] = None):
        """Сохранить метаданные моделей в файл."""
        try:
            data = {}
            for mid, info in self.models.items():
                if model_id is None or mid == model_id:
                    info_copy = info.copy()
                    if isinstance(info_copy.get('created_at'), datetime):
                        info_copy['created_at'] = info_copy['created_at'].isoformat()
                    data[mid] = info_copy
            
            all_data = {}
            if os.path.exists(self.metadata_file):
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    all_data = json.load(f)
            
            all_data.update(data)
            
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(all_data, f, indent=2, ensure_ascii=False, default=str)
        except Exception as e:
            logger.warning(f"Не удалось сохранить метаданные модели: {e}")

    def delete_model(self, model_id: str) -> bool:
        """
        Удалить модель.

        Args:
            model_id: ID модели

        Returns:
            True если модель удалена, False если не найдена
        """
        if model_id not in self.models:
            return False

        model_info = self.models[model_id]
        model_path = model_info.get("model_path")

        if model_path and os.path.exists(model_path):
            os.remove(model_path)

        del self.models[model_id]

        logger.info("Модель удалена")
        return True


model_service = ModelService()

