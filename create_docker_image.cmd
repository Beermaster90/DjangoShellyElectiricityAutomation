@echo off
echo Building Docker image...
docker build -t shelly_django .

echo Saving Docker image to tar file...
docker save -o shelly_django.tar shelly_django

echo Done! Image saved as shelly_django.tar
pause