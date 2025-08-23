from django.apps import AppConfig

class AppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "app"

    def ready(self):
        # Ensure ENTSOE_API_KEY exists at startup
        from .models import AppSetting
        if not AppSetting.objects.filter(key='ENTSOE_API_KEY').exists():
            AppSetting.objects.create(key='ENTSOE_API_KEY', value='ABC123')
        # Start the APScheduler when Django starts
        from app.scheduler import start_scheduler
        start_scheduler()
