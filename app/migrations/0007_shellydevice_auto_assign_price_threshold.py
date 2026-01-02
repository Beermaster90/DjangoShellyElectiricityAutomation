from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0006_temperature_reading"),
    ]

    operations = [
        migrations.AddField(
            model_name="shellydevice",
            name="auto_assign_price_threshold",
            field=models.DecimalField(
                decimal_places=5,
                default=0,
                help_text=(
                    "Always assign periods when total price is at or below this threshold (c/kWh)"
                ),
                max_digits=6,
            ),
        ),
    ]
