from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore
from django.conf import settings
from django.db import connection

def get_scheduler():
    """
    Configure and return the APScheduler instance with optimized settings.
    """
    scheduler = BackgroundScheduler(timezone=settings.TIME_ZONE)
    
    # Use our custom jobstore with optimized connection handling
    scheduler.add_jobstore(DjangoJobStore(), 'default', {
        'isolation_level': None,  # Disable transaction isolation for less locking
    })
    
    # Configure the scheduler for better SQLite compatibility
    scheduler.configure(
        job_defaults={
            'coalesce': True,  # Combine multiple pending runs into a single run
            'max_instances': 1,  # Only allow one instance of each job
            'misfire_grace_time': 60,  # Allow jobs to fire a bit late
        },
    )
    
    return scheduler