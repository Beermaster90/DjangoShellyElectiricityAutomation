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


def find_current_hour():
    """Find if there's a price entry for the current Finnish hour."""

    user = User.objects.filter(username="admin").first()
    factory = RequestFactory()
    request = factory.get("/")
    request.user = user

    context = get_common_context(request)
    current_hour_from_context = context.get("current_hour")
    prices = context.get("prices", [])

    print(f"Looking for hour: {current_hour_from_context}")
    print(f"Total prices: {len(prices)}")

    for i, price in enumerate(prices):
        hour = price.get("hour")
        if hour == current_hour_from_context:
            print(
                f"FOUND MATCH! Price {i+1}: Hour={hour} (Finnish), Start={price.get('start_time')} (UTC)"
            )
            return

    print("No price entry found for current Finnish hour")
    print("\nAll available hours:")
    for i, price in enumerate(prices):
        hour = price.get("hour")
        print(f"  Price {i+1}: Hour={hour}")


if __name__ == "__main__":
    find_current_hour()
