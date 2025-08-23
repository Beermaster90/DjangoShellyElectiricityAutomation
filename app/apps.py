from django.apps import AppConfig


class AppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "app"

    def ready(self):
        # Ensure required settings exist at startup
        from .models import AppSetting

        # Ensure ENTSOE_API_KEY exists
        if not AppSetting.objects.filter(key="ENTSOE_API_KEY").exists():
            AppSetting.objects.create(key="ENTSOE_API_KEY", value="ABC123")

        # Ensure SHELLY_STOP_REST_DEBUG exists (0 = allow REST calls, 1 = block REST calls)
        if not AppSetting.objects.filter(key="SHELLY_STOP_REST_DEBUG").exists():
            AppSetting.objects.create(key="SHELLY_STOP_REST_DEBUG", value="0")

        # Start the APScheduler when Django starts
        try:
            from app.scheduler import start_scheduler

            start_scheduler()
        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Failed to start scheduler: {e}")
            # Continue without scheduler rather than crashing
