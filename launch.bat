@echo off
title OrgScan  --  Close this window to stop the server
cd /d "%~dp0"

echo.
echo  OrgScan starting...
echo  Browser will open automatically in a few seconds.
echo  Close this window to stop the server.
echo.

:: Open the browser after the server has had 3 seconds to start
start "" cmd /c "timeout /t 3 /nobreak >nul && start http://localhost:8000"

:: Start the server (blocks until closed)
"C:\Users\reggi\AppData\Local\Programs\Python\Python313\Scripts\uvicorn.exe" main:app --port 8000 --log-level warning

echo.
echo  OrgScan stopped.  Press any key to close.
pause >nul
