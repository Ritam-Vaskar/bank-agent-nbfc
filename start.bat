@echo off
echo.
echo Starting Bank Agent System...
echo.

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo Docker is not running. Please start Docker Desktop first.
    exit /b 1
)

echo Building and starting services...
docker-compose up --build -d

echo.
echo Waiting for services to be ready...
timeout /t 10 /nobreak >nul

echo.
echo ═══════════════════════════════════════════════════
echo Bank Agent is ready!
echo ═══════════════════════════════════════════════════
echo.
echo Frontend:  http://localhost:3000
echo Backend:   http://localhost:5000
echo Agents:    http://localhost:8000
echo.
echo Demo Login:
echo   Email:    demo@example.com
echo   Password: demo123
echo.
echo ═══════════════════════════════════════════════════
echo.
echo Useful commands:
echo   View logs:    docker-compose logs -f
echo   Stop all:     docker-compose down
echo   Restart:      docker-compose restart
echo.
pause
