docker image prune -f
echo "\nDatabase file location: $DATA_DIR/db.sqlite3"
echo "Django production server is running at: http://127.0.0.1:8000"
#!/bin/bash
# Build and run Django production Docker container

DATA_DIR="$(pwd)/data"
if [ ! -d "$DATA_DIR" ]; then
  mkdir -p "$DATA_DIR"
fi
sudo chown 999:999 "$DATA_DIR"
VERSION=$(cat VERSION)
BUILD_DATE=$(date +%Y%m%d-%H%M%S)
TAG="$VERSION-$BUILD_DATE"
CONTAINER_NAME="django-shelly-prod"
if [ $(docker ps -a -q -f name="^/${CONTAINER_NAME}$") ]; then
  echo "Force removing existing container: $CONTAINER_NAME"
  docker rm -f $CONTAINER_NAME
fi
docker build -t django-shelly-prod:$TAG .
docker run -d \
  -p 8000:8000 \
  --name $CONTAINER_NAME \
  -v "$DATA_DIR":/data \
  django-shelly-prod:$TAG
#!/bin/bash
# Build and run Django production Docker container

DATA_DIR="$(pwd)/data"
if [ ! -d "$DATA_DIR" ]; then
  mkdir -p "$DATA_DIR"
fi
VERSION=$(cat VERSION)
BUILD_DATE=$(date +%Y%m%d-%H%M)
TAG="$VERSION-$BUILD_DATE"
docker build -t django-shelly-prod:$TAG .
docker run -d \
  -p 8000:8000 \
  --name django-shelly-prod \
  -v "$DATA_DIR":/data \
  django-shelly-prod:$TAG
