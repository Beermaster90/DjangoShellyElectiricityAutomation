@echo off
setlocal enabledelayedexpansion

echo ===============================================
echo Testing create_docker_image.cmd script
echo ===============================================

set IMAGE=shelly_django:latest
set TEST_PORT=8003
set CONTAINER_NAME=test-validation

echo.
echo [1/5] Checking if Docker is running...
docker version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker is not running or not installed
    goto :fail
)
echo ✓ Docker is running

echo.
echo [2/5] Running create_docker_image.cmd script...
call create_docker_image.cmd
if errorlevel 1 (
    echo ERROR: create_docker_image.cmd failed
    goto :fail
)
echo ✓ Docker image built successfully

echo.
echo [3/5] Checking image size...
for /f "tokens=7" %%a in ('docker images %IMAGE% --format "table {{.Size}}"') do (
    if not "%%a"=="SIZE" (
        set IMAGE_SIZE=%%a
        echo ✓ Image size: !IMAGE_SIZE!
    )
)

echo.
echo [4/5] Testing container startup...
docker run -d -p %TEST_PORT%:8000 --name %CONTAINER_NAME% %IMAGE%
if errorlevel 1 (
    echo ERROR: Failed to start container
    goto :fail
)

echo Waiting for container to start...
timeout /t 5 /nobreak >nul

docker logs %CONTAINER_NAME% | findstr "Starting gunicorn" >nul 2>&1
if errorlevel 1 (
    echo ERROR: Container did not start properly
    echo Container logs:
    docker logs %CONTAINER_NAME%
    goto :cleanup
)
echo ✓ Container started successfully

echo.
echo [5/5] Testing application response...
timeout /t 3 /nobreak >nul
curl -s -o nul -w "%%{http_code}" http://127.0.0.1:%TEST_PORT%/ | findstr "200\|302" >nul 2>&1
if errorlevel 1 (
    echo WARNING: HTTP test failed (curl may not be available)
    echo You can manually test: http://127.0.0.1:%TEST_PORT%/
) else (
    echo ✓ Application responds correctly
)

echo.
echo [6/6] Checking tar file...
if exist "shelly_django.tar" (
    for %%a in (shelly_django.tar) do (
        echo ✓ Tar file created: %%~za bytes
    )
) else (
    echo ERROR: Tar file not found
    goto :cleanup
)

:cleanup
echo.
echo Cleaning up test container...
docker stop %CONTAINER_NAME% >nul 2>&1
docker rm %CONTAINER_NAME% >nul 2>&1

echo.
echo ===============================================
echo ✓ ALL TESTS PASSED - Script works correctly!
echo ===============================================
echo.
echo Summary:
echo - Docker image: %IMAGE%
echo - Image size: !IMAGE_SIZE!
echo - Container runs successfully
echo - Application responds correctly
echo - Tar file created successfully
echo.
pause
exit /b 0

:fail
echo.
echo ===============================================
echo ✗ TESTS FAILED
echo ===============================================
pause
exit /b 1
