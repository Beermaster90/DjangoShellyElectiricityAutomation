Docker files are located next to .SLN at Project root.
DockerFile
docker-compose.yml

# Build the Docker image
docker-compose build

# Start the Django app in Docker
docker-compose up

### ---------- Create Image for other server

docker build -t shelly_django .
docker save -o shelly_django.tar shelly_django

# Transfer to other server and add in docker container repo

docker load -i /home/user/shelly_django.tar
Verify with docker images that you see your docker image

docker run -d -p 8000:8000 --name shelly_django_container shelly_django

