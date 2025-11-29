#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$PROJECT_DIR/.env"
SECRET_FILE="$PROJECT_DIR/k8s/secret.yaml"

if [ ! -f "$ENV_FILE" ]; then
    echo "Ошибка: файл .env не найден: $ENV_FILE"
    exit 1
fi

CLEARML_API_ACCESS_KEY=$(grep "^CLEARML_API_ACCESS_KEY=" "$ENV_FILE" | cut -d '=' -f2- | tr -d '"' | tr -d "'" | xargs)
CLEARML_API_SECRET_KEY=$(grep "^CLEARML_API_SECRET_KEY=" "$ENV_FILE" | cut -d '=' -f2- | tr -d '"' | tr -d "'" | xargs)

if [ -z "$CLEARML_API_ACCESS_KEY" ] || [ -z "$CLEARML_API_SECRET_KEY" ]; then
    echo "Ошибка: CLEARML_API_ACCESS_KEY или CLEARML_API_SECRET_KEY не найдены в .env"
    exit 1
fi

cat > "$SECRET_FILE" <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: ml-service-secret
  namespace: ml-service
type: Opaque
stringData:
  CLEARML_API_ACCESS_KEY: "$CLEARML_API_ACCESS_KEY"
  CLEARML_API_SECRET_KEY: "$CLEARML_API_SECRET_KEY"
EOF

echo "✅ Secret обновлен из .env файла: $SECRET_FILE"
echo "   CLEARML_API_ACCESS_KEY: ${CLEARML_API_ACCESS_KEY:0:10}..."
echo "   CLEARML_API_SECRET_KEY: ${#CLEARML_API_SECRET_KEY} символов"

