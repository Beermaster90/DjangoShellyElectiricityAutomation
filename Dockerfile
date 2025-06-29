# Use an official Python runtime as a parent image
FROM python:3.11

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Set the working directory in the container
WORKDIR /app

# Copy the project files into the container
COPY . /app/

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r DjangoShellyElectiricityAutomation/requirements.txt && \
    pip install --no-cache-dir whitenoise gunicorn

# Collect static files
RUN python DjangoShellyElectiricityAutomation/manage.py collectstatic --noinput

# Expose port 8000
EXPOSE 8000

# Start Django server
CMD ["gunicorn", "--chdir", "DjangoShellyElectiricityAutomation", "DjangoShellyElectiricityAutomation.wsgi:application", "--bind", "0.0.0.0:8000"]
#CMD ["python", "DjangoShellyElectiricityAutomation/manage.py", "runserver", "0.0.0.0:8000"]