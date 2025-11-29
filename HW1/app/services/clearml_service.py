"""Сервис для работы с ClearML."""

import os
from typing import Optional, Dict, Any
from app.core.config import settings
from app.core.logging import logger

try:
    from clearml import Task, OutputModel
    try:
        from clearml import Project
    except ImportError:
        Project = None
except ImportError:
    logger.warning("ClearML не установлен, функциональность будет ограничена")
    Task = None
    OutputModel = None
    Project = None


class ClearMLService:
    """Сервис для интеграции с ClearML."""

    def __init__(self):
        """Инициализация сервиса."""
        self.initialized = False
        if Task is not None:
            try:
                api_host = os.getenv("CLEARML_API_HOST")
                if not api_host:
                    api_host = "http://clearml-apiserver:8008" if os.path.exists("/.dockerenv") else "http://localhost:8008"
                    os.environ["CLEARML_API_HOST"] = api_host
                elif not api_host.startswith("http://") and not api_host.startswith("https://"):
                    api_host = f"http://{api_host}"
                    os.environ["CLEARML_API_HOST"] = api_host
                
                web_host = os.getenv("CLEARML_WEB_HOST")
                if not web_host:
                    web_host = "http://localhost:8080"
                    os.environ["CLEARML_WEB_HOST"] = web_host
                elif not web_host.startswith("http://") and not web_host.startswith("https://"):
                    web_host = f"http://{web_host}"
                    os.environ["CLEARML_WEB_HOST"] = web_host
                
                access_key = os.getenv("CLEARML_API_ACCESS_KEY") or settings.clearml_api_access_key
                secret_key = os.getenv("CLEARML_API_SECRET_KEY") or settings.clearml_api_secret_key
                
                if access_key:
                    os.environ["CLEARML_API_ACCESS_KEY"] = access_key
                if secret_key:
                    os.environ["CLEARML_API_SECRET_KEY"] = secret_key
                
                if not access_key or not secret_key:
                    logger.warning("ClearML credentials не найдены. ClearML функциональность будет ограничена.")
                    self.initialized = False
                    return
                
                clearml_conf_path = "/tmp/clearml.conf"
                try:
                    with open(clearml_conf_path, "w") as f:
                        f.write(f"api {{\n")
                        f.write(f"  api_server: {api_host}\n")
                        f.write(f"  web_server: {web_host}\n")
                        f.write(f"  files_server: {web_host.replace(':8080', ':8081')}\n")
                        f.write(f"  credentials {{\n")
                        f.write(f"    \"{api_host}\" {{\n")
                        f.write(f"      access_key = \"{access_key}\"\n")
                        f.write(f"      secret_key = \"{secret_key}\"\n")
                        f.write(f"    }}\n")
                        f.write(f"  }}\n")
                        f.write(f"}}\n")
                    os.environ["CLEARML_CONFIG_FILE"] = clearml_conf_path
                    logger.info(f"Создан файл конфигурации ClearML: {clearml_conf_path}")
                except Exception as e:
                    logger.warning(f"Не удалось создать файл конфигурации ClearML: {e}")
                
                if not os.getenv("CLEARML_S3_HOST"):
                    s3_host = "minio:9000" if os.path.exists("/.dockerenv") else "localhost:9000"
                    os.environ["CLEARML_S3_HOST"] = s3_host
                    os.environ["CLEARML_S3_ACCESS_KEY"] = settings.minio_access_key
                    os.environ["CLEARML_S3_SECRET_KEY"] = settings.minio_secret_key
                    os.environ["CLEARML_S3_BUCKET"] = "clearml-models"
                    os.environ["CLEARML_S3_REGION"] = "us-east-1"
                    os.environ["CLEARML_S3_USE_HTTPS"] = "false"
                
                self.initialized = True
                logger.info(f"ClearML инициализирован (API: {os.getenv('CLEARML_API_HOST')}, S3: {os.getenv('CLEARML_S3_HOST')})")
            except Exception as e:
                logger.warning(f"Не удалось инициализировать ClearML: {e}")
        else:
            logger.warning("ClearML не доступен")

    def create_experiment(
        self,
        model_id: str,
        model_type: str,
        hyperparameters: Dict[str, Any],
        dataset_id: str,
    ) -> Optional[Task]:
        """
        Создать эксперимент в ClearML.

        Args:
            model_id: ID модели
            model_type: Тип модели
            hyperparameters: Гиперпараметры
            dataset_id: ID датасета

        Returns:
            Объект Task или None
        """
        if not self.initialized or Task is None:
            return None

        try:
            project_name = os.getenv("CLEARML_PROJECT_NAME", "ml-service")
            if Project is not None:
                try:
                    project = Project.get_project_id(project_name)
                    if project is None:
                        Project.create(project_name=project_name, description="ML Service experiments")
                        logger.info(f"Проект {project_name} создан в ClearML")
                except Exception as e:
                    logger.debug(f"Проект {project_name} уже существует или ошибка при создании: {e}")
            
            try:
                if hasattr(Task, '_set_default_task'):
                    Task._set_default_task(None)
                current_task = Task.current_task()
                if current_task:
                    try:
                        if hasattr(current_task, 'close'):
                            current_task.close()
                        elif hasattr(current_task, 'mark_completed'):
                            current_task.mark_completed()
                    except:
                        pass
            except:
                pass
            
            task = Task.init(
                project_name=project_name,
                task_name=f"{model_type}_{model_id}",
                task_type=Task.TaskTypes.training,
                reuse_last_task_id=False,
                auto_connect_frameworks=False,
                auto_connect_streams=False,
                continue_last_task=False,
            )
            task.add_tags([model_type, dataset_id, f"model_id_{model_id}"])

            try:
                task.connect(hyperparameters, name="hyperparameters")
                task.connect({"dataset_id": dataset_id}, name="dataset_info")
            except Exception as e:
                logger.warning(f"Не удалось подключить параметры к task: {e}")

            logger.info(f"Эксперимент создан в ClearML (model_id: {model_id}, task_id: {task.id})")

            return task
        except Exception as e:
            logger.error(f"Ошибка при создании эксперимента в ClearML (model_id: {model_id}): {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None

    def save_model(
        self,
        model_id: str,
        model_type: str,
        model_path: str,
        hyperparameters: Dict[str, Any],
        dataset_id: str,
        metrics: Optional[Dict[str, float]] = None,
        task: Optional[Any] = None,
    ) -> Optional[str]:
        """
        Сохранить модель в ClearML.

        Args:
            model_id: ID модели
            model_type: Тип модели
            model_path: Путь к файлу модели
            hyperparameters: Гиперпараметры
            dataset_id: ID датасета
            metrics: Метрики модели
            task: Существующий Task объект (если None, создается новый)

        Returns:
            ID модели в ClearML или None
        """
        if not self.initialized or OutputModel is None:
            logger.warning("ClearML не инициализирован или OutputModel недоступен")
            return None

        try:
            if task is None:
                logger.info(f"Task не передан, создаю новый эксперимент для model_id: {model_id}")
                task = self.create_experiment(model_id, model_type, hyperparameters, dataset_id)
                if task is None:
                    logger.error(f"Не удалось создать Task для model_id: {model_id}")
                    return None
            else:
                logger.info(f"Использую существующий Task {task.id} для model_id: {model_id}")
            
            if metrics:
                for metric_name, metric_value in metrics.items():
                    if metric_value is not None and not (isinstance(metric_value, float) and (metric_value != metric_value or metric_value == float('inf'))):
                        task.logger.report_scalar(
                            title="Final Metrics",
                            series=metric_name,
                            value=float(metric_value),
                            iteration=2
                        )

            if not os.path.exists(model_path):
                logger.error(f"Файл модели не найден: {model_path}")
                return None

            model_name = f"{model_type}_{model_id}"
            output_model = OutputModel(task=task, name=model_name)
            output_model.update_weights(model_path)
            model_id_clearml = output_model.id
            
            logger.info(
                f"Модель сохранена в ClearML и загружена в S3 (model_id: {model_id_clearml}, task_id: {task.id})"
            )
            
            try:
                task.mark_completed()
                logger.info(f"Task {task.id} успешно установлен в статус completed")
            except Exception as e:
                logger.error(f"Ошибка при установке статуса completed для task {task.id}: {e}")
                try:
                    task.status = Task.TaskStatusEnum.completed
                    logger.info(f"Task {task.id} статус установлен напрямую через status")
                except Exception as e2:
                    logger.error(f"Не удалось установить статус completed для task {task.id}: {e2}")
            
            try:
                if hasattr(task, 'flush'):
                    task.flush()
            except Exception as e:
                logger.debug(f"Не удалось выполнить flush для task {task.id}: {e}")
            
            try:
                Task._set_default_task(None)
            except:
                pass

            return output_model.id
        except Exception as e:
            logger.error(f"Ошибка при сохранении модели в ClearML (model_id: {model_id}): {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None

    def load_model(self, clearml_model_id: Optional[str], model_id: str) -> Optional[str]:
        """
        Загрузить модель из ClearML.

        Args:
            clearml_model_id: ID модели в ClearML
            model_id: ID модели в системе

        Returns:
            Путь к загруженному файлу модели или None
        """
        if not self.initialized or clearml_model_id is None or OutputModel is None:
            return None

        try:
            model = OutputModel(model_id=clearml_model_id)
            local_path = os.path.join(settings.models_dir, f"{model_id}_clearml.pkl")
            model.get_weights(local_path)

            logger.info(f"Модель загружена из ClearML (model_id: {model_id}, clearml_model_id: {clearml_model_id})")

            return local_path
        except Exception as e:
            logger.error(f"Ошибка при загрузке модели из ClearML (model_id: {model_id}): {str(e)}")
            return None

clearml_service = ClearMLService()

