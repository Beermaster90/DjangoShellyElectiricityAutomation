from django.db import migrations

def add_entsoe_api_key(apps, schema_editor):
    AppSetting = apps.get_model('app', 'AppSetting')
    if not AppSetting.objects.filter(key='ENTSOE_API_KEY').exists():
        AppSetting.objects.create(key='ENTSOE_API_KEY', value='ABC123')

class Migration(migrations.Migration):
    dependencies = [
        ('app', '0001_initial'), # Update this if your initial migration has a different name
    ]
    operations = [
        migrations.RunPython(add_entsoe_api_key),
    ]
