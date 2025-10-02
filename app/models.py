from django.db import models
from django.contrib.auth.models import User
from app.utils.time_utils import TimeUtils
from django.conf import settings
import pytz
from django.db.models.signals import post_save
from django.dispatch import receiver


class AppSetting(models.Model):
    key = models.CharField(max_length=128, unique=True)
    value = models.TextField()

    def __str__(self):
        return f"{self.key}: {self.value[:16]}..."

    class Meta:
        verbose_name = "App Setting"
        verbose_name_plural = "App Settings"


# Create your models here.


class ShellyDevice(models.Model):
    device_id = models.AutoField(primary_key=True)  # Auto-generated device ID
    familiar_name = models.CharField(max_length=255)  # User-defined familiar name
    shelly_api_key = models.CharField(max_length=255)  # API key for the device
    shelly_device_name = models.CharField(
        max_length=255, blank=True, null=True
    )  # Device name from the API

    # Automatically store the creation time in UTC
    created_at = models.DateTimeField(auto_now_add=True)

    # Automatically store the last modification time in UTC
    updated_at = models.DateTimeField(auto_now=True)

    # Django User and Shelly relationship
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    status = models.IntegerField(default=1)  # 1 = automation enabled, 0 = automation disabled
    last_contact = models.DateTimeField(default=TimeUtils.now_utc)  # Ensure UTC storage

    # New field for how many hours the device should run daily
    run_hours_per_day = models.IntegerField(
        default=0, help_text="Set how many hours the device should run daily (0-24)"
    )

    # New fields for transfer prices
    day_transfer_price = models.DecimalField(
        max_digits=6,
        decimal_places=5,
        help_text="Transfer price during the day (c/kWh)",
    )

    night_transfer_price = models.DecimalField(
        max_digits=6,
        decimal_places=5,
        help_text="Transfer price during the night (c/kWh)",
    )

    relay_channel = models.IntegerField(
        default=0,
        help_text="Default relay channel for the Shelly device (e.g., 0 for switch:0)",
    )

    shelly_server = models.URLField(
        max_length=512,
        default="https://yourapiaddress.shelly.cloud",
        help_text="Base URL of the Shelly server used for device communication",
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
        # Handle case where price is not set yet
        if self.price_kwh is None:
            return f"No price set from {self.start_time} to {self.end_time}"
        # The prices are already stored in c/kWh format, not €/MWh
        return f"{float(self.price_kwh):.3f} c/kWh from {self.start_time} to {self.end_time}"


class DeviceLog(models.Model):
    STATUS_CHOICES = [
        ("INFO", "Info"),
        ("WARN", "Warning"),
        ("ERROR", "Error"),
    ]

    device = models.ForeignKey(
        "ShellyDevice",
        on_delete=models.CASCADE,
        null=True,  # Allow NULL values
        blank=True,  # Allow empty values in forms
    )
    message = models.TextField()
    status = models.CharField(max_length=5, choices=STATUS_CHOICES, default="INFO")
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


class UserProfile(models.Model):
    """Extended user profile with timezone and other preferences."""

    TIMEZONE_CHOICES = [
        ("UTC", "UTC (Coordinated Universal Time)"),
        ("Europe/Helsinki", "Helsinki (Finland)"),
        ("Europe/Stockholm", "Stockholm (Sweden)"),
        ("Europe/Oslo", "Oslo (Norway)"),
        ("Europe/Copenhagen", "Copenhagen (Denmark)"),
        ("Europe/London", "London (UK)"),
        ("Europe/Berlin", "Berlin (Germany)"),
        ("Europe/Paris", "Paris (France)"),
        ("Europe/Rome", "Rome (Italy)"),
        ("Europe/Madrid", "Madrid (Spain)"),
        ("America/New_York", "New York (EST/EDT)"),
        ("America/Chicago", "Chicago (CST/CDT)"),
        ("America/Denver", "Denver (MST/MDT)"),
        ("America/Los_Angeles", "Los Angeles (PST/PDT)"),
        ("Asia/Tokyo", "Tokyo (Japan)"),
        ("Asia/Shanghai", "Shanghai (China)"),
        ("Asia/Kolkata", "Mumbai/Delhi (India)"),
        ("Australia/Sydney", "Sydney (Australia)"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    timezone = models.CharField(
        max_length=50,
        choices=TIMEZONE_CHOICES,
        default="Europe/Helsinki",
        help_text="User's preferred timezone for displaying dates and times",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.timezone}"

    def get_timezone(self):
        """Returns the pytz timezone object for this user."""
        return pytz.timezone(self.timezone)

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"



# Signal to automatically create UserProfile and add user to 'commoneers' group as staff
@receiver(post_save, sender=User)
def create_or_update_user_profile_and_group(sender, instance, created, **kwargs):
    """Create or update user profile and add to commoneers group as staff when user is saved."""
    if created:
        UserProfile.objects.create(user=instance)
        # Add to commoneers group and set as staff
        from django.contrib.auth.models import Group
        group, _ = Group.objects.get_or_create(name="commoneers")
        instance.groups.add(group)
        instance.is_staff = True
        instance.save()
    else:
        # Update existing profile if it exists
        if hasattr(instance, "profile"):
            instance.profile.save()
        else:
            # Create profile if it doesn't exist (for existing users)
            UserProfile.objects.create(user=instance)
