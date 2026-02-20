#!/bin/bash

echo "🚀 Starting all AGENT services..."
echo ""

# Start Backend
echo "Starting Backend (uvicorn on port 8000)..."
cd /home/ubuntu/AGENT/backend
source venv/bin/activate
nohup uvicorn main:app --host 0.0.0.0 --port 8000 > backend.log 2>&1 &
BACKEND_PID=$!
echo "   Backend started (PID: $BACKEND_PID)"
sleep 3

# Start Frontend
echo "Starting Frontend (Next.js on port 3000)..."
cd /home/ubuntu/AGENT
nohup npm run start > frontend.log 2>&1 &
FRONTEND_PID=$!
echo "   Frontend started (PID: $FRONTEND_PID)"
sleep 5

# Verify services are running
echo ""
echo "Verifying services..."
BACKEND_RUNNING=$(pgrep -f "uvicorn main:app" | wc -l)
FRONTEND_RUNNING=$(pgrep -f "next|node.*3000" | wc -l)

if [ "$BACKEND_RUNNING" -gt 0 ]; then
    echo "✅ Backend is running"
    curl -s http://localhost:8000/docs > /dev/null && echo "   API responding on http://localhost:8000" || echo "   ⚠️  API not responding yet"
else
    echo "❌ Backend failed to start"
fi

if [ "$FRONTEND_RUNNING" -gt 0 ]; then
    echo "✅ Frontend is running"
    curl -s http://localhost:3000 > /dev/null && echo "   Frontend responding on http://localhost:3000" || echo "   ⚠️  Frontend not responding yet"
else
    echo "❌ Frontend failed to start"
fi

echo ""
echo "Services started at: $(date)"
echo ""
echo "To view logs:"
echo "  Backend:  tail -f /home/ubuntu/AGENT/backend/backend.log"
echo "  Frontend: tail -f /home/ubuntu/AGENT/frontend.log"
