#!/usr/bin/env python
import os
import sys
import django

# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")
django.setup()

from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType


def setup_commoneers_group():
    """Create 'commoneers' group and assign permissions if not exists."""
    group_name = "commoneers"
    group, created = Group.objects.get_or_create(name=group_name)
    if created:
        print(f"✅ Created group: {group_name}")
    else:
        print(f"✅ Group already exists: {group_name}")

    # Assign permissions for device assignments, Shelly devices, and electricity prices
    models_and_perms = [
        ("deviceassignment", ["add_deviceassignment", "change_deviceassignment", "delete_deviceassignment", "view_deviceassignment"]),
        ("shellydevice", ["add_shellydevice", "change_shellydevice", "delete_shellydevice", "view_shellydevice"]),
        ("electricityprice", ["view_electricityprice"]),
    ]
    for model, perm_codenames in models_and_perms:
        ct = ContentType.objects.get(app_label="app", model=model)
        for codename in perm_codenames:
            try:
                perm = Permission.objects.get(content_type=ct, codename=codename)
                group.permissions.add(perm)
                print(f"  - Added permission: {codename} to group {group_name}")
            except Permission.DoesNotExist:
                print(f"  - Permission not found: {codename} for model {model}")

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
    setup_commoneers_group()
    create_test_user()
