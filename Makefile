.PHONY: help all start stop restart status logs clean test build minikube-start minikube-stop minikube-deploy minikube-clean minikube-build minikube-port-forward minikube-port-forward-stop

help:
	@echo "Основные команды:"
	@echo "  make all              - Запустить все сервисы (ClearML + Minikube)"
	@echo "  make start            - Запустить ClearML (docker-compose)"
	@echo "  make stop             - Остановить ClearML"
	@echo "  make status           - Статус контейнеров"
	@echo "  make logs             - Логи контейнеров"
	@echo "  make clean            - Удалить все контейнеры и volumes"
	@echo ""
	@echo "Minikube команды:"
	@echo "  make minikube-start   - Запустить minikube и развернуть сервисы"
	@echo "  make minikube-stop    - Остановить развертывание"
	@echo "  make minikube-port-forward - Port forwarding для доступа к сервисам"
	@echo "  make minikube-clean   - Очистить развертывание"
	@echo "  make minikube-update-secret - Обновить Secret из .env файла"

all: start minikube-start minikube-port-forward
	@echo ""
	@echo "Все сервисы запущены!"
	@echo "ClearML Web UI: http://localhost:8080"
	@echo "REST API: http://localhost:8000"
	@echo "Dashboard: http://localhost:8501"
	@echo "MinIO Console: http://localhost:9001"

start:
	@echo "Запуск ClearML и зависимостей..."
	@docker-compose up -d
	@sleep 15
	@docker-compose ps

stop:
	@docker-compose stop

restart: stop start

status:
	@docker-compose ps

logs:
	@docker-compose logs -f

clean:
	@docker-compose down -v

minikube-start:
	@echo "Запуск minikube..."
	@minikube start --driver=docker || true
	@make minikube-build
	@make minikube-deploy
	@echo "Ожидание готовности сервисов..."
	@kubectl wait --for=condition=available --timeout=300s deployment/ml-api -n ml-service || true
	@kubectl wait --for=condition=available --timeout=300s deployment/ml-dashboard -n ml-service || true
	@kubectl wait --for=condition=available --timeout=300s deployment/minio -n ml-service || true
	@echo "Сервисы развернуты! Запустите: make minikube-port-forward"

minikube-build:
	@echo "Сборка образов..."
	@eval $$(minikube docker-env) && docker build -f docker/Dockerfile.api -t ml-api:latest .
	@eval $$(minikube docker-env) && docker build -f docker/Dockerfile.grpc -t ml-grpc:latest .
	@eval $$(minikube docker-env) && docker build -f docker/Dockerfile.dashboard -t ml-dashboard:latest .

minikube-deploy: minikube-update-secret
	@kubectl apply -f k8s/namespace.yaml
	@kubectl apply -f k8s/minio/pvc.yaml
	@kubectl apply -f k8s/api/pvc.yaml
	@kubectl apply -f k8s/minio/deployment.yaml
	@kubectl apply -f k8s/minio/service.yaml
	@kubectl wait --for=condition=available --timeout=120s deployment/minio -n ml-service || true
	@sleep 10
	@kubectl apply -f k8s/minio/job-init.yaml
	@sleep 5
	@kubectl apply -k k8s/

minikube-update-secret:
	@bash scripts/update-secret.sh
	@kubectl apply -f k8s/secret.yaml

minikube-stop:
	@kubectl delete -k k8s/ --ignore-not-found=true || true
	@kubectl delete -f k8s/api/pvc.yaml --ignore-not-found=true || true
	@kubectl delete -f k8s/minio/pvc.yaml --ignore-not-found=true || true

minikube-port-forward:
	@bash scripts/port-forward.sh

minikube-port-forward-stop:
	@bash scripts/port-forward-stop.sh

minikube-clean: minikube-stop minikube-port-forward-stop
	@kubectl delete namespace ml-service --ignore-not-found=true || true
