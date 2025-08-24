# Add this to your app/models.py - User Profile Extension with Timezone

from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
import pytz


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


# Signal to automatically create UserProfile when User is created
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """Create or update user profile when user is saved."""
    if created:
        UserProfile.objects.create(user=instance)
    else:
        # Update existing profile if it exists
        if hasattr(instance, "profile"):
            instance.profile.save()
        else:
            # Create profile if it doesn't exist (for existing users)
            UserProfile.objects.create(user=instance)
