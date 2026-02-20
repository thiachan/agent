# 📋 Log Files Guide - Debugging & Troubleshooting

## Log File Locations

### Primary Log Files
1. **Backend API Log**: `/home/ubuntu/AGENT/backend/backend.log` (165KB)
2. **Frontend Log**: `/home/ubuntu/AGENT/frontend.log` (520 bytes)

---

## Quick Commands

### 🔴 Most Important - Real-time Backend Monitoring
```bash
tail -f /home/ubuntu/AGENT/backend/backend.log
```
This is your **primary debugging log** - monitors all API calls, errors, and backend operations in real-time.

### 🎨 Real-time Frontend Monitoring
```bash
tail -f /home/ubuntu/AGENT/frontend.log
```
Monitors Next.js compilation and frontend issues.

### 📊 Monitor Both Simultaneously
```bash
tail -f /home/ubuntu/AGENT/backend/backend.log /home/ubuntu/AGENT/frontend.log
```

---

## Interactive Log Monitor (Recommended!)

I've created an interactive log monitoring tool for you:

```bash
/home/ubuntu/AGENT/MONITOR_LOGS.sh
```

This provides a menu with options to:
- Tail logs in real-time
- Search for specific events (errors, auth, RAG)
- View log file sizes
- Backup and clear logs
- And more!

---

## Common Debugging Scenarios

### 🔍 Scenario 1: User Can't Login
```bash
# Monitor authentication events
grep -i "auth\|login\|token" /home/ubuntu/AGENT/backend/backend.log | tail -20

# Or watch in real-time
tail -f /home/ubuntu/AGENT/backend/backend.log | grep --color=auto -i "auth\|login"
```

### 🔍 Scenario 2: Knowledge Base Not Loading
```bash
# Search for knowledge base and RAG events
grep -i "knowledge\|rag\|document" /home/ubuntu/AGENT/backend/backend.log | tail -30
```

### 🔍 Scenario 3: File Upload Issues
```bash
# Monitor upload events
grep -i "upload\|file" /home/ubuntu/AGENT/backend/backend.log | tail -20
```

### 🔍 Scenario 4: API Errors
```bash
# Find all errors and exceptions
grep -i "error\|exception\|failed\|traceback" /home/ubuntu/AGENT/backend/backend.log | tail -30

# With context (5 lines before and after each error)
grep -i -B 5 -A 5 "error" /home/ubuntu/AGENT/backend/backend.log | tail -50
```

### 🔍 Scenario 5: Chat Not Working
```bash
# Monitor chat operations
grep -i "chat\|message\|gpt" /home/ubuntu/AGENT/backend/backend.log | tail -20
```

### 🔍 Scenario 6: Database Issues
```bash
# Monitor database operations
grep -i "database\|sqlite\|query\|sql" /home/ubuntu/AGENT/backend/backend.log | tail -20
```

---

## Understanding Log Entries

### Backend Log Format
The backend log typically contains:
- **Timestamp**: When the event occurred
- **Log Level**: INFO, WARNING, ERROR, DEBUG
- **Module**: Which part of the code generated the log
- **Message**: Details about the event

Example:
```
2026-01-07 09:21:45,123 - INFO - uvicorn.access - "POST /api/auth/login HTTP/1.1" 200
2026-01-07 09:21:46,456 - ERROR - app.api.documents - Failed to upload file: Permission denied
```

---

## Advanced Monitoring

### Monitor with Colored Output
```bash
tail -f /home/ubuntu/AGENT/backend/backend.log | grep --color=auto -E "ERROR|WARNING|INFO|$"
```

### Monitor Multiple Patterns
```bash
tail -f /home/ubuntu/AGENT/backend/backend.log | grep --color=auto -E "error|exception|auth|login|upload|$"
```

### Save Filtered Logs to File
```bash
# Save last 100 error lines to a file
grep -i "error" /home/ubuntu/AGENT/backend/backend.log | tail -100 > /tmp/errors.log
cat /tmp/errors.log
```

### Monitor with Timestamps
```bash
tail -f /home/ubuntu/AGENT/backend/backend.log | while read line; do echo "$(date '+%Y-%m-%d %H:%M:%S') - $line"; done
```

---

## Log Management

### View Log Sizes
```bash
ls -lh /home/ubuntu/AGENT/backend/backend.log /home/ubuntu/AGENT/frontend.log
```

### Backup Logs
```bash
# Backup backend log with timestamp
cp /home/ubuntu/AGENT/backend/backend.log \
   /home/ubuntu/AGENT/backend/backend.log.backup.$(date +%Y%m%d_%H%M%S)

# Backup frontend log
cp /home/ubuntu/AGENT/frontend.log \
   /home/ubuntu/AGENT/frontend.log.backup.$(date +%Y%m%d_%H%M%S)
```

### Clear Logs (with backup)
```bash
# Backup and clear backend log
cp /home/ubuntu/AGENT/backend/backend.log \
   /home/ubuntu/AGENT/backend/backend.log.backup.$(date +%Y%m%d_%H%M%S)
> /home/ubuntu/AGENT/backend/backend.log

# Backup and clear frontend log
cp /home/ubuntu/AGENT/frontend.log \
   /home/ubuntu/AGENT/frontend.log.backup.$(date +%Y%m%d_%H%M%S)
> /home/ubuntu/AGENT/frontend.log
```

### Rotate Logs (keep last 5)
```bash
# For backend log
cd /home/ubuntu/AGENT/backend
ls -t backend.log.backup.* | tail -n +6 | xargs -r rm
```

---

## System-Level Logs

### Check System Logs (if services fail to start)
```bash
# Check recent system logs
sudo journalctl -xe | tail -50

# Check logs for specific service
sudo journalctl -u nginx -n 50

# Check for Python errors
sudo journalctl | grep -i python | tail -20
```

### Check Process Status
```bash
# Check if services are running
ps aux | grep -E "(uvicorn|next dev)" | grep -v grep

# Check listening ports
sudo netstat -tulpn | grep -E "(8000|3000)"
```

---

## Tips for Effective Debugging

1. **Always start with backend log** - Most issues are logged here
2. **Use real-time monitoring** (`tail -f`) when testing features
3. **Filter logs** using `grep` to focus on specific areas
4. **Keep logs backed up** before clearing them
5. **Check timestamps** to correlate events with user actions
6. **Look for stack traces** - they show exactly where errors occur

---

## Common Log Patterns to Look For

### ✅ Successful Operations
```
"POST /api/auth/login HTTP/1.1" 200
"GET /api/knowledge-bases HTTP/1.1" 200
Successfully uploaded document
```

### ⚠️ Warnings
```
WARNING - Token expired
WARNING - Rate limit approaching
```

### ❌ Errors
```
ERROR - Database connection failed
ERROR - File not found
EXCEPTION - ValueError: invalid input
Traceback (most recent call last):
```

---

## Quick Reference Card

```bash
# Real-time monitoring (MOST USED)
tail -f /home/ubuntu/AGENT/backend/backend.log

# Interactive menu
/home/ubuntu/AGENT/MONITOR_LOGS.sh

# Last 50 lines
tail -50 /home/ubuntu/AGENT/backend/backend.log

# Search for errors
grep -i "error" /home/ubuntu/AGENT/backend/backend.log | tail -20

# Search with context
grep -i -B 5 -A 5 "error" /home/ubuntu/AGENT/backend/backend.log

# Monitor specific event
tail -f /home/ubuntu/AGENT/backend/backend.log | grep "login"
```

---

**Pro Tip**: Keep a terminal window open with `tail -f` running while testing your application. This gives you immediate visibility into what's happening behind the scenes!




