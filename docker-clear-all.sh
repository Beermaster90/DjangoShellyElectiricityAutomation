#!/bin/bash
# Clear all Docker containers and images

echo "Stopping and removing all running containers..."
docker ps -q | xargs -r docker stop

docker ps -a -q | xargs -r docker rm

echo "Removing all Docker images..."
docker images -q | xargs -r docker rmi -f

echo "Docker cleanup complete."
