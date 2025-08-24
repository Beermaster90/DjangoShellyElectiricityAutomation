#!/usr/bin/env python
import os
import sys
import django

# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")
django.setup()

from django.test import Client
from django.contrib.auth.models import User


def test_final_highlighting():
    """Test the final HTML output with timezone fix."""

    user = User.objects.filter(username="admin").first()
    client = Client()
    client.force_login(user)

    response = client.get("/")

    if response.status_code == 200:
        html_content = response.content.decode("utf-8")

        # Look for current-hour class in table rows
        if 'class="current-hour"' in html_content:
            print("✅ SUCCESS: Row with 'current-hour' class found!")

            # Find the highlighted row
            lines = html_content.split("\n")
            for i, line in enumerate(lines):
                if 'class="current-hour"' in line and "<tr" in line:
                    print(f"Highlighted row: {line.strip()}")
                    # Try to find the time in the next few lines
                    for j in range(i + 1, min(i + 5, len(lines))):
                        if "data-utc=" in lines[j]:
                            print(f"Time data: {lines[j].strip()}")
                            break
        else:
            print("❌ No 'current-hour' class found in table rows")

        # Check what hours are present
        print("\nAll data-hour values found:")
        lines = html_content.split("\n")
        for line in lines:
            if "data-hour=" in line:
                # Extract hour value
                import re

                match = re.search(r'data-hour="(\d+)"', line)
                if match:
                    hour = match.group(1)
                    print(f"  Hour: {hour}")

    else:
        print(f"Failed to get page: HTTP {response.status_code}")


if __name__ == "__main__":
    test_final_highlighting()
