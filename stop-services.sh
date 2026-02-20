#!/bin/bash

echo "🛑 Stopping all AGENT services..."
echo ""

# Stop Backend
echo "Stopping Backend (uvicorn)..."
pkill -f "uvicorn main:app" 2>/dev/null
sleep 2

# Stop Frontend  
echo "Stopping Frontend (Next.js)..."
pkill -f "next" 2>/dev/null
pkill -f "node.*3000" 2>/dev/null
sleep 2

# Verify all stopped
echo ""
echo "Checking remaining processes..."
BACKEND=$(pgrep -f "uvicorn main:app" | wc -l)
FRONTEND=$(pgrep -f "next|node.*3000" | wc -l)

if [ "$BACKEND" -eq 0 ] && [ "$FRONTEND" -eq 0 ]; then
    echo "✅ All services stopped successfully!"
else
    echo "⚠️  Some processes may still be running:"
    ps aux | grep -E "uvicorn|next|node.*3000" | grep -v grep
fi

echo ""
echo "Services stopped at: $(date)"
