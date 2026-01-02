from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0007_shellydevice_auto_assign_price_threshold"),
    ]

    operations = [
        migrations.AlterField(
            model_name="shellydevice",
            name="auto_assign_price_threshold",
            field=models.DecimalField(
                decimal_places=1,
                default=0,
                help_text=(
                    "Always assign periods when total price is at or below this threshold (c/kWh)"
                ),
                max_digits=6,
            ),
        ),
        migrations.AlterField(
            model_name="shellydevice",
            name="day_transfer_price",
            field=models.DecimalField(
                decimal_places=1,
                help_text="Transfer price during the day (c/kWh)",
                max_digits=6,
            ),
        ),
        migrations.AlterField(
            model_name="shellydevice",
            name="night_transfer_price",
            field=models.DecimalField(
                decimal_places=1,
                help_text="Transfer price during the night (c/kWh)",
                max_digits=6,
            ),
        ),
    ]
