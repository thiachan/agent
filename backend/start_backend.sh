#!/bin/bash
echo "Starting GSSO AI Center Backend Server..."
cd "$(dirname "$0")"
source venv/bin/activate
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --limit-concurrency 1000 --limit-max-requests 10000 --timeout-keep-alive 5 --ws-max-size 16777216

