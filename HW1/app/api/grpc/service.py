"""gRPC сервис для ML Service."""

import grpc
from concurrent import futures

import ml_service_pb2
import ml_service_pb2_grpc
from app.services.model_service import model_service
from app.services.dataset_service import dataset_service
from app.core.logging import logger


class MLServiceServicer(ml_service_pb2_grpc.MLServiceServicer):
    """Реализация gRPC сервиса для ML Service."""

    def HealthCheck(self, request, context):
        """Проверка статуса сервиса."""
        logger.info("gRPC: Проверка здоровья сервиса")
        return ml_service_pb2.HealthCheckResponse(
            status="healthy",
            version="0.1.0"
        )

    def GetAvailableModels(self, request, context):
        """Получить список доступных типов моделей."""
        logger.info("gRPC: Запрос списка доступных моделей")
        model_types = model_service.get_available_model_types()
        return ml_service_pb2.GetAvailableModelsResponse(
            model_types=model_types
        )

    def GetModels(self, request, context):
        """Получить список всех моделей."""
        logger.info("gRPC: Запрос списка моделей")
        models = model_service.get_all_models()
        
        pb_models = []
        for model in models:
            hyperparams = {k: str(v) for k, v in model.get('hyperparameters', {}).items()}
            pb_model = ml_service_pb2.ModelInfo(
                model_id=model.get('model_id', ''),
                model_type=model.get('model_type', ''),
                dataset_id=model.get('dataset_id', ''),
                hyperparameters=hyperparams,
                created_at=model.get('created_at', ''),
                status=model.get('status', ''),
            )
            pb_models.append(pb_model)
        
        return ml_service_pb2.GetModelsResponse(models=pb_models)

    def TrainModel(self, request, context):
        """Обучить модель."""
        logger.info(
            "gRPC: Запрос на обучение модели",
            extra={"model_type": request.model_type, "dataset_id": request.dataset_id}
        )
        
        try:
            X, y = dataset_service.load_dataset(request.dataset_id)
            
            hyperparameters = {}
            for key, value in request.hyperparameters.items():
                try:
                    if '.' in value:
                        hyperparameters[key] = float(value)
                    else:
                        hyperparameters[key] = int(value)
                except ValueError:
                    hyperparameters[key] = value
            
            model_id = model_service.train_model(
                model_type=request.model_type,
                dataset_id=request.dataset_id,
                hyperparameters=hyperparameters,
                X=X,
                y=y,
            )
            
            model_info = model_service.get_model(model_id)
            if not model_info:
                context.set_code(grpc.StatusCode.INTERNAL)
                context.set_details("Ошибка при создании модели")
                return ml_service_pb2.TrainModelResponse()
            
            hyperparams = {k: str(v) for k, v in model_info.get('hyperparameters', {}).items()}
            pb_model = ml_service_pb2.ModelInfo(
                model_id=model_info.get('model_id', ''),
                model_type=model_info.get('model_type', ''),
                dataset_id=model_info.get('dataset_id', ''),
                hyperparameters=hyperparams,
                created_at=model_info.get('created_at', ''),
                status=model_info.get('status', ''),
            )
            
            return ml_service_pb2.TrainModelResponse(model=pb_model)
        except ValueError as e:
            logger.error(f"gRPC: Ошибка при обучении модели: {str(e)}")
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(str(e))
            return ml_service_pb2.TrainModelResponse()
        except Exception as e:
            logger.error(f"gRPC: Неожиданная ошибка при обучении модели: {str(e)}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Внутренняя ошибка: {str(e)}")
            return ml_service_pb2.TrainModelResponse()

    def Predict(self, request, context):
        """Получить предсказания от модели."""
        logger.info("gRPC: Запрос на получение предсказаний")
        
        try:
            features = [list(f.values) for f in request.features]
            
            predictions = model_service.predict(request.model_id, features)
            
            return ml_service_pb2.PredictResponse(
                predictions=predictions,
                model_id=request.model_id
            )
        except ValueError as e:
            logger.error(f"gRPC: Ошибка при получении предсказаний: {str(e)}")
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(str(e))
            return ml_service_pb2.PredictResponse()
        except Exception as e:
            logger.error(f"gRPC: Неожиданная ошибка при получении предсказаний: {str(e)}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Внутренняя ошибка: {str(e)}")
            return ml_service_pb2.PredictResponse()

    def RetrainModel(self, request, context):
        """Переобучить модель."""
        logger.info("gRPC: Запрос на переобучение модели")
        
        try:
            X, y = dataset_service.load_dataset(request.dataset_id)
            
            hyperparameters = {}
            for key, value in request.hyperparameters.items():
                try:
                    if '.' in value:
                        hyperparameters[key] = float(value)
                    else:
                        hyperparameters[key] = int(value)
                except ValueError:
                    hyperparameters[key] = value
            
            new_model_id = model_service.retrain_model(
                model_id=request.model_id,
                dataset_id=request.dataset_id,
                hyperparameters=hyperparameters,
                X=X,
                y=y,
            )
            
            model_info = model_service.get_model(new_model_id)
            if not model_info:
                context.set_code(grpc.StatusCode.INTERNAL)
                context.set_details("Ошибка при создании модели")
                return ml_service_pb2.RetrainModelResponse()
            
            hyperparams = {k: str(v) for k, v in model_info.get('hyperparameters', {}).items()}
            pb_model = ml_service_pb2.ModelInfo(
                model_id=model_info.get('model_id', ''),
                model_type=model_info.get('model_type', ''),
                dataset_id=model_info.get('dataset_id', ''),
                hyperparameters=hyperparams,
                created_at=model_info.get('created_at', ''),
                status=model_info.get('status', ''),
            )
            
            return ml_service_pb2.RetrainModelResponse(model=pb_model)
        except ValueError as e:
            logger.error(f"gRPC: Ошибка при переобучении модели: {str(e)}")
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(str(e))
            return ml_service_pb2.RetrainModelResponse()
        except Exception as e:
            logger.error(f"gRPC: Неожиданная ошибка при переобучении модели: {str(e)}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Внутренняя ошибка: {str(e)}")
            return ml_service_pb2.RetrainModelResponse()

    def DeleteModel(self, request, context):
        """Удалить модель."""
        logger.info("gRPC: Запрос на удаление модели")
        
        success = model_service.delete_model(request.model_id)
        if not success:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f"Модель {request.model_id} не найдена")
            return ml_service_pb2.DeleteModelResponse(
                success=False,
                message=f"Модель {request.model_id} не найдена"
            )
        
        return ml_service_pb2.DeleteModelResponse(
            success=True,
            message=f"Модель {request.model_id} успешно удалена"
        )

    def GetDatasets(self, request, context):
        """Получить список всех датасетов."""
        logger.info("gRPC: Запрос списка датасетов")
        datasets = dataset_service.get_all_datasets()
        
        pb_datasets = []
        for dataset in datasets:
            pb_dataset = ml_service_pb2.DatasetInfo(
                dataset_id=dataset.get('dataset_id', ''),
                filename=dataset.get('file_name', ''),
                size=dataset.get('size', 0),
                created_at=dataset.get('created_at', ''),
                dvc_version=dataset.get('dvc_version', ''),
            )
            pb_datasets.append(pb_dataset)
        
        return ml_service_pb2.GetDatasetsResponse(datasets=pb_datasets)

    def UploadDataset(self, request, context):
        """Загрузить датасет."""
        logger.info("gRPC: Запрос на загрузку датасета")
        
        if request.format not in ["csv", "json"]:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("Поддерживаются только форматы csv и json")
            return ml_service_pb2.UploadDatasetResponse()
        
        try:
            dataset_id = dataset_service.upload_dataset(
                request.filename,
                request.content,
                request.format
            )
            
            dataset_info = dataset_service.get_dataset(dataset_id)
            if not dataset_info:
                context.set_code(grpc.StatusCode.INTERNAL)
                context.set_details("Ошибка при загрузке датасета")
                return ml_service_pb2.UploadDatasetResponse()
            
            pb_dataset = ml_service_pb2.DatasetInfo(
                dataset_id=dataset_info.get('dataset_id', ''),
                filename=dataset_info.get('file_name', ''),
                size=dataset_info.get('size', 0),
                created_at=dataset_info.get('created_at', ''),
                dvc_version=dataset_info.get('dvc_version', ''),
            )
            
            return ml_service_pb2.UploadDatasetResponse(dataset=pb_dataset)
        except Exception as e:
            logger.error(f"gRPC: Ошибка при загрузке датасета: {str(e)}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Внутренняя ошибка: {str(e)}")
            return ml_service_pb2.UploadDatasetResponse()

    def DeleteDataset(self, request, context):
        """Удалить датасет."""
        logger.info("gRPC: Запрос на удаление датасета")
        
        success = dataset_service.delete_dataset(request.dataset_id)
        if not success:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f"Датасет {request.dataset_id} не найден")
            return ml_service_pb2.DeleteDatasetResponse(
                success=False,
                message=f"Датасет {request.dataset_id} не найден"
            )
        
        return ml_service_pb2.DeleteDatasetResponse(
            success=True,
            message=f"Датасет {request.dataset_id} успешно удален"
        )


def serve(port: int = 50051):
    """Запустить gRPC сервер."""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    ml_service_pb2_grpc.add_MLServiceServicer_to_server(
        MLServiceServicer(), server
    )
    server.add_insecure_port(f'[::]:{port}')
    server.start()
    logger.info(f"gRPC сервер запущен на порту {port}")
    
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Остановка gRPC сервера")
        server.stop(0)

