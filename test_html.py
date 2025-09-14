#!/usr/bin/env python
import os
import sys
import django

# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")
django.setup()

from django.test import Client
from django.contrib.auth.models import User


def test_html_output():
    """Test the actual HTML output to see if current-hour class is applied."""

    # Get the admin user
    user = User.objects.filter(username="admin").first()
    if not user:
        print("No admin user found!")
        return

    # Create a test client and log in
    client = Client()
    client.force_login(user)

    # Get the index page
    response = client.get("/")

    if response.status_code == 200:
        html_content = response.content.decode("utf-8")

        # Look for current-hour class
        if "current-hour" in html_content:
            print("✅ SUCCESS: 'current-hour' class found in HTML!")

            # Extract the lines with current-hour
            lines = html_content.split("\n")
            for i, line in enumerate(lines):
                if "current-hour" in line:
                    print(f"Line {i+1}: {line.strip()}")
        else:
            print("❌ PROBLEM: 'current-hour' class NOT found in HTML")

        # Look for data-hour attributes
        print("\nChecking data-hour attributes:")
        lines = html_content.split("\n")
        data_hour_lines = []
        for line in lines:
            if "data-hour=" in line:
                data_hour_lines.append(line.strip())

        for line in data_hour_lines[:5]:  # Show first 5
            print(f"  {line}")

        if len(data_hour_lines) > 5:
            print(f"  ... and {len(data_hour_lines) - 5} more")

    else:
        print(f"Failed to get page: HTTP {response.status_code}")


if __name__ == "__main__":
    test_html_output()
