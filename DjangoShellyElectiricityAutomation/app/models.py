from django.db import models
from django.contrib.auth.models import User
from app.utils.time_utils import TimeUtils

# Create your models here.

class ShellyDevice(models.Model):
    device_id = models.AutoField(primary_key=True)  # Auto-generated device ID
    familiar_name = models.CharField(max_length=255)  # User-defined familiar name
    shelly_api_key = models.CharField(max_length=255)  # API key for the device
    shelly_device_name = models.CharField(max_length=255, blank=True, null=True)  # Device name from the API

    # Automatically store the creation time in UTC
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Automatically store the last modification time in UTC
    updated_at = models.DateTimeField(auto_now=True)

    # Django User and Shelly relationship
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    status = models.IntegerField(default=0)
    last_contact = models.DateTimeField(default=TimeUtils.now_utc)  # Ensure UTC storage

    # New field for how many hours the device should run daily
    run_hours_per_day = models.IntegerField(
        default=0,
        help_text="Set how many hours the device should run daily (0-24)"
    )

    # New fields for transfer prices
    day_transfer_price = models.DecimalField(
        max_digits=6, decimal_places=5,
        help_text="Transfer price during the day (c/kWh)"
    )

    night_transfer_price = models.DecimalField(
        max_digits=6, decimal_places=5,
        help_text="Transfer price during the night (c/kWh)"
    )

    relay_channel = models.IntegerField(
        default=0,
        help_text="Default relay channel for the Shelly device (e.g., 0 for switch:0)"
    )

    shelly_server = models.URLField(
    max_length=512,
    default="https://yourapiaddress.shelly.cloud",
    help_text="Base URL of the Shelly server used for device communication"
    )

    def __str__(self):
        return self.familiar_name

class ElectricityPrice(models.Model):
    id = models.AutoField(primary_key=True)  # Explicit ID field
    start_time = models.DateTimeField(default=TimeUtils.now_utc)  # Store in UTC
    end_time = models.DateTimeField(default=TimeUtils.now_utc)  # Store in UTC
    price_kwh = models.DecimalField(max_digits=12, decimal_places=5)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.price_kwh} e/kWh from {self.start_time} to {self.end_time}"

class DeviceLog(models.Model):
    STATUS_CHOICES = [
        ('INFO', 'Info'),
        ('WARN', 'Warning'),
        ('ERROR', 'Error'),
    ]

    device = models.ForeignKey(
        'ShellyDevice',
        on_delete=models.CASCADE,
        null=True,  # Allow NULL values
        blank=True   # Allow empty values in forms
    )
    message = models.TextField()
    status = models.CharField(max_length=5, choices=STATUS_CHOICES, default='INFO')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Log for {self.device.familiar_name if self.device else 'System'} - {self.status}"

class DeviceAssignment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    device = models.ForeignKey(ShellyDevice, on_delete=models.CASCADE)
    electricity_price = models.ForeignKey(ElectricityPrice, on_delete=models.CASCADE)
    assigned_at = models.DateTimeField(auto_now_add=True)  # Timestamp of assignment

    def __str__(self):
        return f"{self.device.familiar_name} assigned at {self.electricity_price.start_time} by {self.user.username}"
