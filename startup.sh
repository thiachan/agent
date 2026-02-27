#!/bin/bash
# Boot startup: start both AGENT services
# Called by @reboot cron

sleep 10  # wait for networking

# ── Backend ───────────────────────────────────────────────────────────────────
cd /home/ubuntu/AGENT/backend
source venv/bin/activate
nohup python -m uvicorn main:app \
  --host 0.0.0.0 --port 8000 \
  --limit-concurrency 1000 --timeout-keep-alive 5 --ws-max-size 16777216 \
  >> /tmp/agent-backend.log 2>&1 &
echo "$(date) [STARTUP] Backend started (PID $!)" >> /tmp/agent-watchdog.log

# ── Frontend ──────────────────────────────────────────────────────────────────
sleep 3
cd /home/ubuntu/AGENT
nohup npx next start -H 0.0.0.0 \
  >> /tmp/agent-frontend.log 2>&1 &
echo "$(date) [STARTUP] Frontend started (PID $!)" >> /tmp/agent-watchdog.log
