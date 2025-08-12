@echo off
set IMAGE=shelly_django:latest

echo Building Docker image (no cache)...
docker build --no-cache -t %IMAGE% .
if errorlevel 1 goto :fail

echo Verifying settings path inside the image...
docker run --rm %IMAGE% sh -c "grep -q '/data/db.sqlite3' /app/DjangoShellyElectiricityAutomation/DjangoShellyElectiricityAutomation/settings.py"
if errorlevel 1 (
  echo ERROR: Image does not contain /data/db.sqlite3 in settings.py
  goto :fail
)

echo Saving Docker image to tar file...
docker save -o shelly_django.tar %IMAGE%
if errorlevel 1 goto :fail

echo Done! Image saved as shelly_django.tar
pause
exit /b 0

:fail
echo Build/save FAILED.
pause
exit /b 1