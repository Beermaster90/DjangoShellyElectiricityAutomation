#!/bin/bash
set -e

IMAGE_NAME="shelly_django:latest"
CONTAINER_NAME="shelly_django_container"
HOST_DATA_DIR="/home/megaman/shelly_data"  # Host directory instead of Docker volume
TAR_PATH="/home/megaman/shelly_django.tar"
DB_PATH="/data/db.sqlite3"
# Django settings module path (NEW structure)
SETTINGS_MODULE="project.settings"

echo "🛑 Stopping/removing container..."
docker stop "$CONTAINER_NAME" 2>/dev/null || true
docker rm "$CONTAINER_NAME" 2>/dev/null || true

echo "🗑️ Removing old image (if any)..."
docker rmi "$IMAGE_NAME" 2>/dev/null || true

echo "📦 Loading image from tar..."
docker load -i "$TAR_PATH"

echo "🔍 Verifying image contains /data/db.sqlite3 in settings.py..."
docker run --rm "$IMAGE_NAME" \
  sh -c "grep -q '/data/db.sqlite3' /app/project/settings.py" \
  || { echo "❌ Loaded image is stale; aborting."; exit 1; }

echo "ℹ️ Image details:"
docker image inspect "$IMAGE_NAME" --format 'Created={{.Created}} Id={{.Id}} Tags={{.RepoTags}}'

echo "📁 Ensuring host data directory exists with proper permissions..."
mkdir -p "$HOST_DATA_DIR"
# Set ownership to UID 999 (django user in container)
sudo chown 999:999 "$HOST_DATA_DIR"
sudo chmod 755 "$HOST_DATA_DIR"
echo "   Directory: $HOST_DATA_DIR (Owner: 999:999)"

echo "🚀 Starting container..."
docker run -d --restart=always --name "$CONTAINER_NAME" \
  -p 35789:8000 \
  -v "$HOST_DATA_DIR":/data:rw \
  -e DJANGO_SETTINGS_MODULE="$SETTINGS_MODULE" \
  -e DJANGO_SQLITE_PATH="$DB_PATH" \
  "$IMAGE_NAME"

# Wait a moment and check if container started successfully
sleep 5
if ! docker ps --format "table {{.Names}}" | grep -q "^$CONTAINER_NAME$"; then
  echo "⚠️ Container failed to start with django user, trying as root..."
  docker rm "$CONTAINER_NAME" 2>/dev/null || true
  
  docker run -d --restart=always --name "$CONTAINER_NAME" \
    --user root \
    -p 35789:8000 \
    -v "$HOST_DATA_DIR":/data:rw \
    -e DJANGO_SETTINGS_MODULE="$SETTINGS_MODULE" \
    -e DJANGO_SQLITE_PATH="$DB_PATH" \
    "$IMAGE_NAME"
    
  echo "✅ Container started as root (will auto-fix permissions)"
fi

echo "✅ Container started successfully on port 35789!"

echo "🔍 Quick verification:"
docker inspect -f '{{range .Mounts}}{{.Destination}} -> {{.Source}}{{println}}{{end}}' "$CONTAINER_NAME"

echo "🧪 Testing Django configuration..."
docker exec -i \
  -e DJANGO_SETTINGS_MODULE="$SETTINGS_MODULE" \
  "$CONTAINER_NAME" sh -lc 'python - << "PY"
import os, django, importlib
print("DJANGO_SETTINGS_MODULE =", os.environ["DJANGO_SETTINGS_MODULE"])
importlib.import_module("app"); print("import app: OK")
django.setup(); from django.conf import settings
print("DB =", settings.DATABASES["default"]["NAME"])
PY'

echo "👤 Ensuring admin user exists..."
docker exec -i \
  -e DJANGO_SETTINGS_MODULE="$SETTINGS_MODULE" \
  "$CONTAINER_NAME" python create_test_user.py

echo "🔐 Verifying admin user login..."
docker exec -i \
  -e DJANGO_SETTINGS_MODULE="$SETTINGS_MODULE" \
  "$CONTAINER_NAME" sh -lc 'python - << "PY"
import django
django.setup()
from django.contrib.auth.models import User
admin = User.objects.filter(username="admin").first()
if admin:
    print("✅ Admin user exists:", admin.username)
    print("✅ Admin is superuser:", admin.is_superuser)
else:
    print("❌ Admin user not found!")
PY'

echo ""
echo "🎉 Deployment completed successfully!"
echo "    Application URL: http://localhost:35789"
echo "    Default login: admin/admin123"
echo "    Host data directory: $HOST_DATA_DIR"
