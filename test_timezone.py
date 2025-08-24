#!/usr/bin/env python
import os
import sys
import django

# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")
django.setup()

from app.views import get_common_context
from django.contrib.auth.models import User
from django.test import RequestFactory
from datetime import datetime, UTC
import pytz


def test_timezone_highlighting():
    """Test if timezone conversion is working correctly for highlighting."""

    # Get the admin user
    user = User.objects.filter(username="admin").first()
    if not user:
        print("No admin user found!")
        return

    # Create a fake request
    factory = RequestFactory()
    request = factory.get("/")
    request.user = user

    # Get the context data
    context = get_common_context(request)

    # Check current times
    utc_now = datetime.now(UTC)
    finnish_tz = pytz.timezone("Europe/Helsinki")
    finnish_now = utc_now.astimezone(finnish_tz)

    print(f"Current UTC time: {utc_now}")
    print(f"Current Finnish time: {finnish_now}")
    print(f"UTC hour: {utc_now.hour}")
    print(f"Finnish hour: {finnish_now.hour}")
    print(f"Hour from context: {context.get('current_hour')}")
    print(f"Match with Finnish: {str(finnish_now.hour) == context.get('current_hour')}")
    print()

    prices = context.get("prices", [])
    print(f"Found {len(prices)} price entries")

    highlighted_count = 0
    current_hour_from_context = context.get("current_hour")

    for i, price in enumerate(prices[:5]):  # Show first 5
        hour = price.get("hour")
        is_current = hour == current_hour_from_context
        if is_current:
            highlighted_count += 1
        print(
            f"Price {i+1}: Hour={hour} (Finnish), Start={price.get('start_time')} (UTC), Current={is_current}"
        )

    print(f"... and {len(prices) - 5} more") if len(prices) > 5 else None
    print(f"\nTotal prices that should be highlighted: {highlighted_count}")


if __name__ == "__main__":
    test_timezone_highlighting()
