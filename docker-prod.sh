
#!/bin/bash
# Build and run Django production Docker container

# Create data directory in user's home directory
DATA_DIR="$HOME/DjangoShellyElectiricityAutomation/data"
if [ ! -d "$DATA_DIR" ]; then
  mkdir -p "$DATA_DIR"
fi
sudo chown 999:999 "$DATA_DIR"

docker image prune -f

echo "Database file location: $DATA_DIR/db.sqlite3"
echo "Django production server is running at: http://127.0.0.1:8000"

VERSION=$(cat VERSION)
BUILD_DATE=$(date +%Y%m%d-%H%M%S)
TAG="$VERSION-$BUILD_DATE"
CONTAINER_NAME="django-shelly-prod"
if [ $(docker ps -a -q -f name="^/${CONTAINER_NAME}$") ]; then
  echo "Force removing existing container: $CONTAINER_NAME"
  docker rm -f $CONTAINER_NAME
fi
echo "Building with VERSION=$VERSION and BUILD_DATE=$BUILD_DATE"
docker build --build-arg VERSION=$VERSION --build-arg BUILD_DATE=$BUILD_DATE -t django-shelly-prod:$TAG .
# Run the container
docker run -d \
  -p 8000:8000 \
  --name $CONTAINER_NAME \
  -v "$DATA_DIR":/data \
  django-shelly-prod:$TAG
