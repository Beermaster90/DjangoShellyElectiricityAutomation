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
    pip install --no-cache-dir -r DjangoShellyElectiricityAutomation/requirements.txt

# Collect static files (if needed)
RUN python DjangoShellyElectiricityAutomation/manage.py collectstatic --noinput

# Expose port 8000 for Django
EXPOSE 8000

# Start the Django server
CMD ["python", "DjangoShellyElectiricityAutomation/manage.py", "runserver", "0.0.0.0:8000"]
