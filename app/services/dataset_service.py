"""Сервис управления датасетами."""

import os
import uuid
import json
import pandas as pd
from datetime import datetime
from typing import Dict, Optional, List, Tuple
from app.core.config import settings
from app.core.logging import logger
from app.services.dvc_service import DVCService
from app.services.minio_service import minio_service


class DatasetService:
    """Сервис для управления датасетами."""

    def __init__(self):
        """Инициализация сервиса."""
        self.datasets: Dict[str, Dict] = {}
        self.datasets_dir = settings.datasets_dir
        os.makedirs(self.datasets_dir, exist_ok=True)
        self.metadata_file = os.path.join(self.datasets_dir, "datasets_metadata.json")
        self.dvc_service = DVCService()
        self._load_metadata_from_file()
        self._load_datasets_from_minio()
        logger.info("Инициализирован DatasetService")
    
    def _load_metadata_from_file(self):
        """Загрузить метаданные датасетов из файла."""
        if os.path.exists(self.metadata_file):
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for dataset_id, dataset_info in data.items():
                        if isinstance(dataset_info.get('created_at'), str):
                            try:
                                dataset_info['created_at'] = datetime.fromisoformat(dataset_info['created_at'])
                            except:
                                dataset_info['created_at'] = datetime.now()
                        self.datasets[dataset_id] = dataset_info
                    logger.info(f"Загружено {len(self.datasets)} датасетов из метаданных")
            except Exception as e:
                logger.warning(f"Не удалось загрузить метаданные датасетов: {e}")
    
    def _save_metadata_to_file(self):
        """Сохранить метаданные датасетов в файл."""
        try:
            data = {}
            for dataset_id, dataset_info in self.datasets.items():
                info_copy = dataset_info.copy()
                if isinstance(info_copy.get('created_at'), datetime):
                    info_copy['created_at'] = info_copy['created_at'].isoformat()
                data[dataset_id] = info_copy
            
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        except Exception as e:
            logger.warning(f"Не удалось сохранить метаданные датасетов: {e}")
    
    def _load_datasets_from_minio(self):
        """Загрузить список датасетов из DVC."""
        pass
    

    def upload_dataset(
        self, file_name: str, file_content: bytes, format: str = "csv"
    ) -> str:
        """
        Загрузить датасет и сохранить в DVC.

        Args:
            file_name: Имя файла
            file_content: Содержимое файла
            format: Формат файла (csv или json)

        Returns:
            ID датасета
        """
        dataset_id = str(uuid.uuid4())
        filepath = os.path.join(self.datasets_dir, f"{dataset_id}.{format}")

        with open(filepath, "wb") as f:
            f.write(file_content)

        file_size = os.path.getsize(filepath)
        dvc_version = self.dvc_service.add_dataset(filepath, file_name)
        self.dvc_service.push_dataset(filepath)

        self.datasets[dataset_id] = {
            "dataset_id": dataset_id,
            "file_name": file_name,
            "filepath": filepath,
            "format": format,
            "size": file_size,
            "created_at": datetime.now(),
            "dvc_version": dvc_version,
        }
        
        self._save_metadata_to_file()

        logger.info(
            f"Датасет загружен и заверсионирован: {file_name} (ID: {dataset_id}, DVC: {dvc_version})"
        )

        return dataset_id
    

    def get_dataset(self, dataset_id: str) -> Optional[Dict]:
        """
        Получить информацию о датасете.

        Args:
            dataset_id: ID датасета

        Returns:
            Словарь с информацией о датасете или None
        """
        return self.datasets.get(dataset_id)

    def get_all_datasets(self) -> List[Dict]:
        """
        Получить список всех датасетов.

        Returns:
            Список словарей с информацией о датасетах
        """
        return list(self.datasets.values())

    def load_dataset(self, dataset_id: str) -> Tuple[List[List[float]], List[float]]:
        """
        Загрузить датасет и вернуть признаки и целевую переменную.
        Если файла нет локально - загружает из DVC.

        Args:
            dataset_id: ID датасета

        Returns:
            Кортеж (X, y) где X - признаки, y - целевая переменная

        Raises:
            ValueError: Если датасет не найден
        """
        dataset_info = self.datasets.get(dataset_id)
        if not dataset_info:
            raise ValueError(f"Датасет {dataset_id} не найден")

        filepath = dataset_info["filepath"]
        format = dataset_info["format"]
        file_name = dataset_info["file_name"]

        if not os.path.exists(filepath):
            logger.info(f"Файл {filepath} не найден локально, загружаем из DVC")
            if not self.dvc_service.pull_dataset(filepath):
                raise ValueError(f"Не удалось загрузить датасет {dataset_id} из DVC")

        if format == "csv":
            df = pd.read_csv(filepath)
        elif format == "json":
            df = pd.read_json(filepath)
        else:
            raise ValueError(f"Неподдерживаемый формат: {format}")

        if len(df.columns) < 2:
            raise ValueError("Датасет должен содержать минимум 2 столбца")

        X = df.iloc[:, :-1].values.tolist()
        y = df.iloc[:, -1].values.tolist()

        logger.info(
            f"Датасет загружен (ID: {dataset_id}): {len(X)} samples, {len(X[0]) if X else 0} features"
        )

        return X, y

    def delete_dataset(self, dataset_id: str) -> bool:
        """
        Удалить датасет.

        Args:
            dataset_id: ID датасета

        Returns:
            True если датасет удален, False если не найден
        """
        if dataset_id not in self.datasets:
            return False

        dataset_info = self.datasets[dataset_id]
        filepath = dataset_info["filepath"]
        file_name = dataset_info["file_name"]

        if os.path.exists(filepath):
            os.remove(filepath)
        
        dvc_file = f"{filepath}.dvc"
        if os.path.exists(dvc_file):
            os.remove(dvc_file)

        del self.datasets[dataset_id]
        
        self._save_metadata_to_file()
        
        logger.info(f"Датасет удален: {dataset_id}")
        return True
    

dataset_service = DatasetService()

