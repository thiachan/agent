#!/bin/bash

echo "🚀 Starting AGENT Services..."
echo ""

# Start Backend
echo "📦 Starting Backend..."
cd /home/ubuntu/AGENT/backend
source venv/bin/activate
nohup uvicorn main:app --host 0.0.0.0 --port 8000 > backend.log 2>&1 &
BACKEND_PID=$!
echo "   Backend started (PID: $BACKEND_PID)"
echo "   Logs: /home/ubuntu/AGENT/backend/backend.log"
echo ""

# Wait for backend to start
sleep 3

# Start Frontend
echo "🎨 Starting Frontend..."
cd /home/ubuntu/AGENT
nohup npm run dev > frontend.log 2>&1 &
FRONTEND_PID=$!
echo "   Frontend started (PID: $FRONTEND_PID)"
echo "   Logs: /home/ubuntu/AGENT/frontend.log"
echo ""

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check status
echo "✅ Service Status:"
echo ""

# Check backend
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "   ✅ Backend: http://localhost:8000 (RUNNING)"
    echo "      API Docs: http://localhost:8000/docs"
else
    echo "   ❌ Backend: Not responding"
fi

# Check frontend
if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo "   ✅ Frontend: http://localhost:3000 (RUNNING)"
else
    echo "   ❌ Frontend: Not responding"
fi

echo ""
echo "📝 To view logs:"
echo "   Backend:  tail -f /home/ubuntu/AGENT/backend/backend.log"
echo "   Frontend: tail -f /home/ubuntu/AGENT/frontend.log"
echo ""
echo "🛑 To stop services:"
echo "   pkill -f 'uvicorn main:app'"
echo "   pkill -f 'next dev'"
