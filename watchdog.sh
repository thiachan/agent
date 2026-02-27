#!/bin/bash
# Watchdog: restart AGENT services if they are not responding
# Called by cron every minute

LOGFILE="/tmp/agent-watchdog.log"
timestamp() { date '+%Y-%m-%d %H:%M:%S'; }

# ── Backend (port 8000) ───────────────────────────────────────────────────────
if ! curl -sf http://localhost:8000/openapi.json -o /dev/null 2>/dev/null; then
  echo "$(timestamp) [WATCHDOG] Backend not responding — restarting..." >> "$LOGFILE"
  pkill -f "uvicorn main:app" 2>/dev/null
  sleep 2
  cd /home/ubuntu/AGENT/backend
  source venv/bin/activate
  nohup python -m uvicorn main:app \
    --host 0.0.0.0 --port 8000 \
    --limit-concurrency 1000 --timeout-keep-alive 5 --ws-max-size 16777216 \
    >> /tmp/agent-backend.log 2>&1 &
  echo "$(timestamp) [WATCHDOG] Backend restarted (PID $!)" >> "$LOGFILE"
else
  echo "$(timestamp) [WATCHDOG] Backend OK" >> "$LOGFILE"
fi

# ── Frontend (port 3000) ──────────────────────────────────────────────────────
if ! curl -sf http://localhost:3000 -o /dev/null 2>/dev/null; then
  echo "$(timestamp) [WATCHDOG] Frontend not responding — restarting..." >> "$LOGFILE"
  pkill -f "next-server" 2>/dev/null
  pkill -f "npx next start" 2>/dev/null
  sleep 2
  cd /home/ubuntu/AGENT
  nohup npx next start -H 0.0.0.0 \
    >> /tmp/agent-frontend.log 2>&1 &
  echo "$(timestamp) [WATCHDOG] Frontend restarted (PID $!)" >> "$LOGFILE"
else
  echo "$(timestamp) [WATCHDOG] Frontend OK" >> "$LOGFILE"
fi
