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

Stop and remove the existing container

docker stop shelly_django_container
docker rm shelly_django_container

Remove the old image (optional)

docker rmi shelly_django

Load the new image from the tar file

docker load -i shelly_django.tar

Run a new container with the updated image

docker run -d --name shelly_django_container -p 8000:8000 shelly_django