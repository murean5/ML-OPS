## Быстрый старт

### Требования

- Docker и Docker Compose
- Minikube
- kubectl

### Запуск

```bash
make all
```

Эта команда запускает:
- ClearML и зависимости (MongoDB, Redis, Elasticsearch) в Docker Compose
- ml-api, ml-grpc, ml-dashboard, MinIO в Minikube
- Port forwarding для доступа на `localhost`

### Остановка

```bash
make stop                    # Остановить ClearML
make minikube-stop           # Остановить Minikube
make minikube-port-forward-stop  # Остановить port forwarding
```

## Доступные сервисы

- **REST API**: http://localhost:8000 (Swagger: http://localhost:8000/docs)
- **Dashboard**: http://localhost:8501
- **gRPC**: localhost:50051
- **MinIO Console**: http://localhost:9001 (minioadmin/minioadmin)
- **ClearML Web UI**: http://localhost:8080

## API

### REST API

**Датасеты:**
- `GET /api/v1/datasets` - список
- `POST /api/v1/datasets/upload` - загрузить (CSV/JSON)
- `DELETE /api/v1/datasets/{dataset_id}` - удалить

**Модели:**
- `GET /api/v1/models` - список
- `POST /api/v1/models/train` - обучить
- `POST /api/v1/models/{model_id}/predict` - предсказания
- `DELETE /api/v1/models/{model_id}` - удалить

### Пример использования

```bash
# Загрузить датасет
curl -X POST "http://localhost:8000/api/v1/datasets/upload" \
  -F "file=@dataset.csv" -F "format=csv"

# Обучить модель
curl -X POST "http://localhost:8000/api/v1/models/train" \
  -H "Content-Type: application/json" \
  -d '{"model_type": "linear", "dataset_id": "<dataset_id>", "hyperparameters": {}}'

# Получить предсказания
curl -X POST "http://localhost:8000/api/v1/models/<model_id>/predict" \
  -H "Content-Type: application/json" \
  -d '{"features": [[1.0, 2.0, 3.0, 4.0]]}'
```

## Интеграция с ClearML

При обучении модели автоматически:
- Создается Task в ClearML (проект `ml-service`)
- Логируются метрики (R², MAE, MSE, RMSE)
- Сохраняются веса модели
- Task получает статус `completed`

Просмотр: http://localhost:8080 → проект "ml-service"

## Конфигурация

### Файл .env

```bash
# ClearML
CLEARML_API_HOST=http://clearml-apiserver:8008
CLEARML_WEB_HOST=http://localhost:8080
CLEARML_API_ACCESS_KEY=your_access_key
CLEARML_API_SECRET_KEY=your_secret_key

# MinIO
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
```

### Обновление ClearML Credentials

1. Получите credentials в ClearML Web UI (Settings → Workspace → Create new credentials)
2. Обновите `.env` файл
3. Выполните: `make minikube-update-secret`

## Команды Make

```bash
make all                      # Запустить все сервисы
make start                    # Запустить ClearML
make stop                     # Остановить ClearML
make status                   # Статус контейнеров
make minikube-start           # Запустить Minikube
make minikube-stop            # Остановить Minikube
make minikube-port-forward    # Port forwarding
make minikube-update-secret   # Обновить Secret из .env
```

## Типы моделей

- **Linear Regression** (`linear`): `alpha`, `max_iter`
- **Random Forest** (`random_forest`): `n_estimators`, `max_depth`, `min_samples_split`

## Разработка

```bash
# Установка зависимостей
poetry install

# Генерация Proto файлов
poetry run python -m grpc_tools.protoc -I proto --python_out=. --grpc_python_out=. proto/ml_service.proto

# Локальный запуск
poetry run uvicorn app.main:app --reload --port 8000
poetry run python grpc_server.py
poetry run streamlit run dashboard/app.py --server.port 8501
```
