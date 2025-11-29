#!/bin/bash

pkill -f "kubectl port-forward.*ml-service" 2>/dev/null || true
sleep 1

echo "Starting port forwarding..."

nohup kubectl port-forward -n ml-service service/ml-api 8000:8000 > /tmp/k8s-pf-api.log 2>&1 &
nohup kubectl port-forward -n ml-service service/ml-dashboard 8501:8501 > /tmp/k8s-pf-dashboard.log 2>&1 &
nohup kubectl port-forward -n ml-service service/minio 9000:9000 > /tmp/k8s-pf-minio-api.log 2>&1 &
nohup kubectl port-forward -n ml-service service/minio 9001:9001 > /tmp/k8s-pf-minio-console.log 2>&1 &
nohup kubectl port-forward -n ml-service service/ml-grpc 50051:50051 > /tmp/k8s-pf-grpc.log 2>&1 &

sleep 3

echo "Port forwarding started!"
echo ""
echo "Service URLs:"
echo "  REST API: http://localhost:8000"
echo "  Dashboard: http://localhost:8501"
echo "  MinIO Console: http://localhost:9001 (minioadmin/minioadmin)"
echo "  MinIO API: http://localhost:9000"
echo "  gRPC: localhost:50051"
echo ""
echo "To stop port forwarding: ./scripts/port-forward-stop.sh"
echo "Logs: /tmp/k8s-pf-*.log"
