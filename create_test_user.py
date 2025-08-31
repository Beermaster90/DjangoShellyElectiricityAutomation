#!/usr/bin/env python
import os
import sys
import django

# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")
django.setup()

from django.contrib.auth.models import User


def create_test_user():
    """Create a simple test user for testing the UI."""

    # Try to get existing admin user and print info
    admin_user = User.objects.filter(username="admin").first()
    if admin_user:
        print(f"✅ Admin user already exists: {admin_user.username}")
        print("✅ Skipping password reset to preserve existing password")
    else:
        print("👤 Creating new admin user")
        User.objects.create_superuser("admin", "admin@example.com", "admin123")
        print("✅ Created admin user with password 'admin123'")


if __name__ == "__main__":
    create_test_user()
