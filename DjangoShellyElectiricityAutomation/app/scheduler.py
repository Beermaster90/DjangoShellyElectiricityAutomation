from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from django_apscheduler.jobstores import DjangoJobStore
from django.db import connection
from app.tasks import fetch_electricity_prices,control_shelly_devices
import logging

logger = logging.getLogger(__name__)

def start_scheduler():
    # Check if the APScheduler tables exist before starting the scheduler
    with connection.cursor() as cursor:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='django_apscheduler_djangojob';")
        if cursor.fetchone() is None:
            logger.warning("APScheduler tables not found! Skipping scheduler startup until migrations are applied.")
            return

    scheduler = BackgroundScheduler()
    scheduler.add_jobstore(DjangoJobStore(), "default")

    # Schedule the fetch electricity prices task (Every hour at HH:00)
    scheduler.add_job(
        fetch_electricity_prices,
        trigger=CronTrigger(hour="*", minute=59),
        id="fetch_prices",
        max_instances=1,
        replace_existing=True,
    )

    # Schedule the Shelly device control task (Every 15 minutes)
    scheduler.add_job(
        control_shelly_devices,
        trigger=CronTrigger(minute="04,16,39,45"),  # Runs at these exact minutes
        id="control_shelly",
        max_instances=1,
        replace_existing=True,
    )

    logger.info("APScheduler started successfully.")
    scheduler.start()

