#!/bin/bash
set -e

IMAGE_NAME="shelly_django:latest"
CONTAINER_NAME="shelly_django_container"
VOLUME_NAME="shelly_django_db"
TAR_PATH="/home/megaman/shelly_django.tar"
DB_PATH="/data/db.sqlite3"
# SINGLE-NESTED module (inner package)
SETTINGS_MODULE="DjangoShellyElectiricityAutomation.settings"

echo " Stopping/removing container..."
docker stop "$CONTAINER_NAME" 2>/dev/null || true
docker rm "$CONTAINER_NAME" 2>/dev/null || true

echo " Removing old image (if any)..."
docker rmi "$IMAGE_NAME" 2>/dev/null || true

echo " Loading image from tar..."
docker load -i "$TAR_PATH"

echo "離 Verifying image contains /data/db.sqlite3 in settings.py..."
docker run --rm "$IMAGE_NAME" \
  sh -c "grep -q '/data/db.sqlite3' /app/DjangoShellyElectiricityAutomation/DjangoShellyElectiricityAutomation/settings.py" \
  || { echo "❌ Loaded image is stale; aborting."; exit 1; }

echo "ℹ️ Image details:"
docker image inspect "$IMAGE_NAME" --format 'Created={{.Created}} Id={{.Id}} Tags={{.RepoTags}}'

echo " Ensuring volume exists..."
docker volume inspect "$VOLUME_NAME" >/dev/null 2>&1 || docker volume create "$VOLUME_NAME"

echo " Starting container..."
docker run -d --restart=always --name "$CONTAINER_NAME" \
  -p 35789:8000 \
  -v "$VOLUME_NAME":/data \
  -e PYTHONPATH=/app/DjangoShellyElectiricityAutomation \
  -e DJANGO_SETTINGS_MODULE="$SETTINGS_MODULE" \
  -e DJANGO_SQLITE_PATH="$DB_PATH" \
  "$IMAGE_NAME"

echo "✅ Up and running on port 35789."

echo " Quick check:"
docker inspect -f '{{range .Mounts}}{{.Destination}} -> {{.Source}}{{println}}{{end}}' "$CONTAINER_NAME"
docker exec -it \
  -e PYTHONPATH=/app/DjangoShellyElectiricityAutomation \
  -e DJANGO_SETTINGS_MODULE="$SETTINGS_MODULE" \
  "$CONTAINER_NAME" sh -lc 'python - << "PY"
import os, django, importlib
print("DJANGO_SETTINGS_MODULE =", os.environ["DJANGO_SETTINGS_MODULE"])
importlib.import_module("app"); print("import app: OK")
django.setup(); from django.conf import settings
print("DB =", settings.DATABASES["default"]["NAME"])
PY'
