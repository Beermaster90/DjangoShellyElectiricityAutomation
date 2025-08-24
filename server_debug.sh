#!/bin/bash
echo "=== Server Docker Debug ==="
echo ""
echo "1. Docker containers:"
docker ps -a

echo ""
echo "2. Docker images:"
docker images | grep shelly

echo ""
echo "3. If container is running, check logs:"
read -p "Enter container name/ID (or press Enter to skip): " container_id
if [ ! -z "$container_id" ]; then
    echo "Container logs:"
    docker logs "$container_id"
    
    echo ""
    echo "4. Check permissions inside container:"
    docker exec "$container_id" ls -la /data/
    
    echo ""
    echo "5. Check write permissions:"
    docker exec "$container_id" touch /data/.test_write && echo "Write OK" || echo "Write FAILED"
    docker exec "$container_id" rm -f /data/.test_write
fi

echo ""
echo "6. Check host directory permissions (if using volume mount):"
echo "What's your host data directory path?"
read -p "Host directory (e.g., /home/user/docker/data): " host_dir
if [ ! -z "$host_dir" ] && [ -d "$host_dir" ]; then
    echo "Host directory permissions:"
    ls -la "$host_dir"
    echo "Owner ID should be 999:999 for django user in container"
fi
