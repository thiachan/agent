@echo off
echo Starting GSSE AI Center Backend Server...
echo This will bind to 0.0.0.0:8000 (accessible from network)
echo.
cd /d %~dp0
call venv\Scripts\activate
echo.
echo Starting server on 0.0.0.0:8000...
python main.py
pause

