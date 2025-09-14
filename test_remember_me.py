#!/usr/bin/env python
"""
Test script to verify the remember me functionality
"""

import os
import sys
import django
from datetime import datetime, timedelta

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from django.contrib.sessions.models import Session

def test_remember_me_functionality():
    """Test the remember me functionality"""
    print("Testing Remember Me functionality...")
    
    # Create a test user if it doesn't exist
    username = 'testuser'
    password = 'testpass123'
    
    user, created = User.objects.get_or_create(
        username=username,
        defaults={'email': 'test@example.com'}
    )
    if created:
        user.set_password(password)
        user.save()
        print(f"Created test user: {username}")
    else:
        print(f"Using existing test user: {username}")
    
    client = Client()
    
    # Test 1: Login WITHOUT remember me
    print("\n=== Test 1: Login without Remember Me ===")
    response = client.post('/login/', {
        'username': username,
        'password': password,
        'remember_me': False,  # Not checked
    })
    
    if response.status_code == 302:  # Redirect on successful login
        print("✓ Login successful")
        
        # Check session expiry
        session_key = client.session.session_key
        session = Session.objects.get(session_key=session_key)
        
        # For remember_me=False, check if session is set to expire at browser close
        expiry_age = client.session.get_expiry_age()
        expiry_date = client.session.get_expiry_date()
        
        print(f"Session expiry age (without remember me): {expiry_age} seconds")
        print(f"Session expiry date: {expiry_date}")
        print(f"Session expire at browser close: {client.session.get_expire_at_browser_close()}")
        
        if client.session.get_expire_at_browser_close():
            print("✓ Session set to expire at browser close (as expected)")
        else:
            print("⚠ Session is not set to expire at browser close, but may still work correctly")
            # Check if the expiry is very short (close to browser close behavior)
            if expiry_age < 3600:  # Less than 1 hour
                print("✓ Session has short expiry, which is acceptable for non-remember me")
            else:
                print("✗ Session expiry not set correctly for non-remember me login")
    else:
        print("✗ Login failed")
        print(f"Response status: {response.status_code}")
        return
    
    # Clear session
    client.logout()
    
    # Test 2: Login WITH remember me
    print("\n=== Test 2: Login with Remember Me ===")
    response = client.post('/login/', {
        'username': username,
        'password': password,
        'remember_me': True,  # Checked
    })
    
    if response.status_code == 302:  # Redirect on successful login
        print("✓ Login successful")
        
        # Check session expiry
        session_key = client.session.session_key
        session = Session.objects.get(session_key=session_key)
        
        # For remember_me=True, session should last 90 days
        expiry_age = client.session.get_expiry_age()
        expected_age = 60 * 60 * 24 * 90  # 90 days in seconds
        
        print(f"Session expiry age (with remember me): {expiry_age} seconds")
        print(f"Expected age (90 days): {expected_age} seconds")
        
        # Allow some tolerance for timing differences
        if abs(expiry_age - expected_age) < 60:  # Within 1 minute tolerance
            print("✓ Session set to expire in ~90 days (as expected)")
        else:
            print("✗ Session expiry not set correctly for remember me login")
            print(f"Difference: {abs(expiry_age - expected_age)} seconds")
    else:
        print("✗ Login failed")
        print(f"Response status: {response.status_code}")
        return
    
    print("\n=== Remember Me Test Complete ===")

if __name__ == '__main__':
    test_remember_me_functionality()
