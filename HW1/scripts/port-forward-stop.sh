#!/bin/bash

echo "Stopping port forwarding..."
pkill -f "kubectl port-forward.*ml-service" 2>/dev/null || true
sleep 1
echo "Port forwarding stopped"

