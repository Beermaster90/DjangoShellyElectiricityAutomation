"""
Definition of models.
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# Create your models here.

class ShellyDevice(models.Model):
    device_id = models.AutoField(primary_key=True)  # Auto-generated device ID
    familiar_name = models.CharField(max_length=255)  # User-defined familiar name
    shelly_api_key = models.CharField(max_length=255)  # API key for the device
    shelly_device_name = models.CharField(max_length=255, blank=True, null=True)  # Device name from the API

    # Automatically store the creation time
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Automatically store the last modification time
    updated_at = models.DateTimeField(auto_now=True)

    # Django User and Shelly relationship
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    status = models.IntegerField(default=0)
    last_contact = models.DateTimeField(default=timezone.now)  # Use a callable for the default

    # New field for how many hours the device should run daily
    run_hours_per_day = models.IntegerField(
        default=0,
        help_text="Set how many hours the device should run daily (0-24)"
    )

    # New fields for transfer prices
    day_transfer_price = models.DecimalField(
        max_digits=6, decimal_places=5,
        help_text="Transfer price during the day (e/kWh)"
    )

    night_transfer_price = models.DecimalField(
        max_digits=6, decimal_places=5,
        help_text="Transfer price during the night (e/kWh)"
    )

    def __str__(self):
        return self.familiar_name

class ElectricityPrice(models.Model):
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField(default=timezone.now)
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

    device = models.ForeignKey(ShellyDevice, on_delete=models.CASCADE)
    message = models.TextField()  # To store the log message
    status = models.CharField(max_length=5, choices=STATUS_CHOICES, default='INFO')
    created_at = models.DateTimeField(auto_now_add=True)  # Automatically store log creation time

    def __str__(self):
        return f"Log for {self.device.familiar_name} - {self.status}"