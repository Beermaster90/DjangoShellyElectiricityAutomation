#!/usr/bin/env python
"""
Test the comprehensive timezone management system.
"""
import os
import sys
import django

# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")
django.setup()

from django.contrib.auth.models import User
from app.models import UserProfile
from app.utils.time_utils import TimeUtils
from datetime import datetime, UTC
import pytz


def test_timezone_system():
    """Test the comprehensive timezone system."""

    print("=== COMPREHENSIVE TIMEZONE SYSTEM TEST ===\n")

    # Get admin user
    admin_user = User.objects.get(username="admin")
    print(f"Testing with user: {admin_user.username}")

    # Test 1: Check if user profile exists and works
    print(f"1. User Profile: {admin_user.profile}")
    print(f"   Timezone: {admin_user.profile.timezone}")
    print(f"   Timezone Object: {admin_user.profile.get_timezone()}")

    # Test 2: Test TimeUtils methods
    print("\n2. TimeUtils Methods:")

    current_utc = TimeUtils.now_utc()
    user_tz = TimeUtils.get_user_timezone(admin_user)
    user_tz_name = TimeUtils.get_user_timezone_name(admin_user)
    current_user_tz = TimeUtils.to_user_timezone(current_utc, admin_user)
    formatted_time = TimeUtils.format_datetime(current_utc, admin_user)
    formatted_with_tz = TimeUtils.format_datetime_with_tz(current_utc, admin_user)
    current_hour = TimeUtils.current_hour_in_user_timezone(admin_user)

    print(f"   Current UTC: {current_utc}")
    print(f"   User Timezone: {user_tz}")
    print(f"   User Timezone Name: {user_tz_name}")
    print(f"   Current in User TZ: {current_user_tz}")
    print(f"   Formatted: {formatted_time}")
    print(f"   Formatted with TZ: {formatted_with_tz}")
    print(f"   Current Hour: {current_hour}")

    # Test 3: Test with different timezones
    print("\n3. Testing Different Timezones:")

    test_timezones = ["UTC", "America/New_York", "Asia/Tokyo"]

    for tz_name in test_timezones:
        # Temporarily change user timezone
        admin_user.profile.timezone = tz_name
        admin_user.profile.save()

        user_time = TimeUtils.to_user_timezone(current_utc, admin_user)
        hour = TimeUtils.current_hour_in_user_timezone(admin_user)
        formatted = TimeUtils.format_datetime_with_tz(current_utc, admin_user)

        print(f"   {tz_name}: {formatted} (Hour: {hour})")

    # Restore original timezone
    admin_user.profile.timezone = "Europe/Helsinki"
    admin_user.profile.save()

    # Test 4: Test view context
    print("\n4. Testing View Context:")
    from app.views import get_common_context
    from django.test import RequestFactory

    factory = RequestFactory()
    request = factory.get("/")
    request.user = admin_user

    context = get_common_context(request)
    print(f"   Current Hour from Context: {context.get('current_hour')}")
    print(f"   User Timezone from Context: {context.get('user_timezone')}")
    print(f"   Number of Prices: {len(context.get('prices', []))}")

    # Show timezone-adjusted price hours
    prices = context.get("prices", [])
    if prices:
        print(f"   First Price Hour (User TZ): {prices[0].get('hour')}")
        print(f"   First Price Start Time: {prices[0].get('start_time')}")

    print("\n=== ALL TESTS COMPLETED ===")


if __name__ == "__main__":
    test_timezone_system()
