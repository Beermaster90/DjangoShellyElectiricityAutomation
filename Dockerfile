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

# ==== Collect static files without needing the real DB ====
# Use SQLite in-memory DB so collectstatic doesn't touch /data/db.sqlite3 during build
ENV DJANGO_SQLITE_PATH=":memory:"
RUN python DjangoShellyElectiricityAutomation/manage.py collectstatic --noinput
# Reset for runtime (will be overridden at `docker run`)
ENV DJANGO_SQLITE_PATH=""

# Expose port 8000
EXPOSE 8000

# Start Django server with Gunicorn
CMD ["gunicorn", "DjangoShellyElectiricityAutomation.wsgi:application", "--bind", "0.0.0.0:8000"]

# If you prefer Django's dev server, comment the above CMD and use:
# CMD ["python", "DjangoShellyElectiricityAutomation/manage.py", "runserver", "0.0.0.0:8000"]
