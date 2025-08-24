#!/usr/bin/env python
"""
Script to create UserProfile instances for existing users who don't have one.
This ensures all users have timezone settings.
"""
import os
import sys
import django

# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")
django.setup()

from django.contrib.auth.models import User
from app.models import UserProfile


def create_missing_profiles():
    """Create UserProfile for users who don't have one."""
    users_without_profiles = User.objects.filter(profile__isnull=True)
    created_count = 0

    print(f"Found {users_without_profiles.count()} users without profiles")

    for user in users_without_profiles:
        profile = UserProfile.objects.create(
            user=user, timezone="Europe/Helsinki"  # Default timezone
        )
        print(
            f"Created profile for user: {user.username} with timezone: {profile.timezone}"
        )
        created_count += 1

    print(f"Created {created_count} user profiles")

    # List all users and their timezones
    print("\nAll users and their timezone settings:")
    for user in User.objects.all():
        try:
            tz = user.profile.timezone
        except:
            tz = "No profile!"
        print(f"  {user.username}: {tz}")


if __name__ == "__main__":
    create_missing_profiles()
