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


def test_current_hour_highlighting():
    """Test if current hour highlighting data is correctly generated."""

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

    current_utc_hour = datetime.now(UTC).hour
    current_hour_from_context = context.get("current_hour")

    print(f"Current UTC hour (actual): {current_utc_hour}")
    print(f"Current hour from context: {current_hour_from_context}")
    print(f"Match: {str(current_utc_hour) == current_hour_from_context}")
    print()

    prices = context.get("prices", [])
    print(f"Found {len(prices)} price entries")

    highlighted_count = 0
    for i, price in enumerate(prices):
        hour = price.get("hour")
        is_current = hour == current_hour_from_context
        if is_current:
            highlighted_count += 1
        print(
            f"Price {i+1}: Hour={hour}, Start={price.get('start_time')}, Current={is_current}"
        )

    print(f"\nTotal prices that should be highlighted: {highlighted_count}")


if __name__ == "__main__":
    test_current_hour_highlighting()
