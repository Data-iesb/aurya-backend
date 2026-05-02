#!/bin/bash
# Start Aurya API locally
cd "$(dirname "$0")"
fuser -k 8000/tcp 2>/dev/null
sleep 1
PYTHONPATH=. nohup python3 -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 > /tmp/aurya.log 2>&1 &
echo "Aurya started (PID: $!) — logs at /tmp/aurya.log"
echo "Waiting for startup..."
sleep 5
curl -s http://localhost:8000/health && echo "" || echo "Not ready yet — check /tmp/aurya.log"
