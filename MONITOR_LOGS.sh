#!/bin/bash

# AGENT Application Log Monitor
# This script helps you monitor and debug your application logs

BACKEND_LOG="/home/ubuntu/AGENT/backend/backend.log"
FRONTEND_LOG="/home/ubuntu/AGENT/frontend.log"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}==================================================${NC}"
echo -e "${BLUE}   AGENT Application - Log Monitor${NC}"
echo -e "${BLUE}==================================================${NC}"
echo ""

# Function to show menu
show_menu() {
    echo -e "${GREEN}Choose an option:${NC}"
    echo "1. Tail backend logs (real-time)"
    echo "2. Tail frontend logs (real-time)"
    echo "3. Tail both logs (real-time)"
    echo "4. Show last 50 lines of backend log"
    echo "5. Show last 50 lines of frontend log"
    echo "6. Search for errors in backend log"
    echo "7. Search for authentication events"
    echo "8. Search for RAG/Knowledge base events"
    echo "9. Show log file sizes and locations"
    echo "10. Clear backend log (backup first)"
    echo "0. Exit"
    echo ""
}

# Main loop
while true; do
    show_menu
    read -p "Enter your choice: " choice
    echo ""
    
    case $choice in
        1)
            echo -e "${YELLOW}Monitoring backend logs (Press Ctrl+C to stop)...${NC}"
            echo ""
            tail -f "$BACKEND_LOG"
            ;;
        2)
            echo -e "${YELLOW}Monitoring frontend logs (Press Ctrl+C to stop)...${NC}"
            echo ""
            tail -f "$FRONTEND_LOG"
            ;;
        3)
            echo -e "${YELLOW}Monitoring both logs (Press Ctrl+C to stop)...${NC}"
            echo ""
            tail -f "$BACKEND_LOG" "$FRONTEND_LOG"
            ;;
        4)
            echo -e "${YELLOW}Last 50 lines of backend log:${NC}"
            echo ""
            tail -50 "$BACKEND_LOG"
            echo ""
            ;;
        5)
            echo -e "${YELLOW}Last 50 lines of frontend log:${NC}"
            echo ""
            tail -50 "$FRONTEND_LOG"
            echo ""
            ;;
        6)
            echo -e "${YELLOW}Searching for errors in backend log:${NC}"
            echo ""
            grep -i "error\|exception\|failed\|traceback" "$BACKEND_LOG" | tail -30
            echo ""
            ;;
        7)
            echo -e "${YELLOW}Authentication events:${NC}"
            echo ""
            grep -i "auth\|login\|logout\|register\|token" "$BACKEND_LOG" | tail -30
            echo ""
            ;;
        8)
            echo -e "${YELLOW}RAG/Knowledge base events:${NC}"
            echo ""
            grep -i "rag\|knowledge\|document\|upload\|embedding" "$BACKEND_LOG" | tail -30
            echo ""
            ;;
        9)
            echo -e "${YELLOW}Log file information:${NC}"
            echo ""
            echo -e "${BLUE}Backend Log:${NC}"
            ls -lh "$BACKEND_LOG" 2>/dev/null || echo "Not found"
            echo ""
            echo -e "${BLUE}Frontend Log:${NC}"
            ls -lh "$FRONTEND_LOG" 2>/dev/null || echo "Not found"
            echo ""
            echo -e "${BLUE}Total log size:${NC}"
            du -sh /home/ubuntu/AGENT/*.log /home/ubuntu/AGENT/backend/*.log 2>/dev/null
            echo ""
            ;;
        10)
            echo -e "${RED}Backing up and clearing backend log...${NC}"
            cp "$BACKEND_LOG" "${BACKEND_LOG}.backup.$(date +%Y%m%d_%H%M%S)"
            > "$BACKEND_LOG"
            echo -e "${GREEN}Done! Backup saved with timestamp.${NC}"
            echo ""
            ;;
        0)
            echo -e "${GREEN}Exiting...${NC}"
            exit 0
            ;;
        *)
            echo -e "${RED}Invalid choice. Please try again.${NC}"
            echo ""
            ;;
    esac
    
    read -p "Press Enter to continue..."
    clear
done




