@echo off
echo Starting MediRisk Application...

:: Open the UI in the default web browser
echo Opening frontend UI...
start "" "%~dp0ui\hospital-login.html"

:: Activate virtual environment and run the backend
echo Starting backend server on http://127.0.0.1:5000...
echo (Press CTRL+C to stop the server)
call "%~dp0venv\Scripts\activate.bat"
python "%~dp0backend\app.py"
pause
