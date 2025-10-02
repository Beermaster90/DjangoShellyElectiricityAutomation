from apscheduler.triggers.cron import CronTrigger
from django.db import connection
from app.tasks import DeviceController
from app.scheduler_config import get_scheduler
import logging

logger = logging.getLogger(__name__)

def start_scheduler():
    # Check if the APScheduler tables exist before starting the scheduler
    with connection.cursor() as cursor:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='django_apscheduler_djangojob';")
        if cursor.fetchone() is None:
            logger.warning("APScheduler tables not found! Skipping scheduler startup until migrations are applied.")
            return

    # Get the optimized scheduler configuration
    scheduler = get_scheduler()

    # Schedule the fetch electricity prices task (Every hour at HH:00 and HH:03)
    # HH:00 for regular updates, HH:03 as a backup in case the first attempt fails
    scheduler.add_job(
        DeviceController.fetch_electricity_prices,
        trigger=CronTrigger(hour="*", minute="0,3"),
        id="fetch_prices",
        max_instances=1,
        replace_existing=True,
    )

    # Schedule device control only for non-price-fetch times (15, 30, 45 minutes)
    # Price fetching at 00 already includes device control
    scheduler.add_job(
        DeviceController.control_shelly_devices,
        trigger=CronTrigger(minute="15,30,45"),  # Skip minute 0 as price fetch handles it
        id="control_shelly",
        max_instances=1,
        replace_existing=True,
    )

    logger.info("APScheduler started successfully.")
    scheduler.start()

