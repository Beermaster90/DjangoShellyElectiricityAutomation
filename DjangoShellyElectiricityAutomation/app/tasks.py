import requests,time
from datetime import datetime,timedelta
from django.urls import reverse
from django.utils.timezone import now
from django.conf import settings
from django.test import RequestFactory
from django.http import JsonResponse
from app.models import ShellyDevice, ElectricityPrice, DeviceLog, DeviceAssignment  # Include DeviceLog
from app.shelly_views import toggle_device_output, fetch_device_status
from app.services.shelly_service import ShellyService
from app.price_views import call_fetch_prices,get_cheapest_hours
from .logger import log_device_event
from app.utils.time_utils import TimeUtils  # Import for UTC handling
import pytz


def fetch_electricity_prices():
    """
    Calls the Django view to fetch electricity prices internally.
    """
    try:
        response = call_fetch_prices(None)  # Call the view function directly

        if isinstance(response, JsonResponse) and response.status_code != 200:
            log_device_event(None, f"Schedule failed to fetch electricity prices. Response: {response.content}", "ERROR")

    except Exception as e:
        log_device_event(None, f"Error calling fetch-prices: {e}", "ERROR")

def control_shelly_devices():
    """
    Loops through all Shelly devices and toggles them based on pre-assigned cheapest hours.
    Runs on fixed UTC+2 time.
    """
    try:
        # Get current time in UTC
        current_time = TimeUtils.now_utc()

        # Ensure we're fetching prices for the current hour
        start_of_hour = current_time.replace(minute=0, second=0, microsecond=0)
        end_of_hour = start_of_hour + timedelta(minutes=59, seconds=59)

        print(f"Checking devices for {current_time} (UTC) Querying UTC Hour: {start_of_hour.hour}")

        # Fetch ElectricityPrice entries for the correct hour
        active_prices = ElectricityPrice.objects.filter(
            start_time__range=(start_of_hour, end_of_hour)
        )

        print(f"Active Prices Found: {len(active_prices)}")
        for price in active_prices:
            print(f" - ID: {price.id}, Start Time: {price.start_time} (TZ: {price.start_time.tzinfo})")

        # Convert active_prices to a list of IDs for filtering
        active_price_ids = list(active_prices.values_list("id", flat=True))

        # Fetch all devices
        devices = ShellyDevice.objects.all()

        for device in devices:
            print(f"Processing device: {device.device_id} ({device.familiar_name})")

            # Check if the device is assigned to any active price using IDs
            assigned = DeviceAssignment.objects.filter(
                device=device,
                electricity_price_id__in=active_price_ids  # Use ID comparison instead of object comparison
            ).exists()

            print(f"Assigned status for device {device.familiar_name}: {assigned}")

            if not assigned:
                print(f"Device {device.familiar_name} is NOT assigned for this hour. Stopping it.")
                toggle_shelly_device(device, "off")
                continue  # Skip further checks for this device

            # Device is assigned, ensure it is running
            toggle_shelly_device(device, "on")

    except Exception as e:
        log_device_event(None, f"Error controlling Shelly devices: {e}", "ERROR")


def toggle_shelly_device(device, action):
    """
    Helper function to toggle a Shelly device ON or OFF.
    """
    shelly_service = ShellyService(device.device_id)
    device_status = shelly_service.get_device_status()

    if "error" in device_status:
        log_device_event(device, f"Error fetching status: {device_status['error']}", "ERROR")
        return

    is_running = device_status.get("data", {}).get("device_status", {}).get("switch:0", {}).get("output", False)

    if (action == "off" and is_running) or (action == "on" and not is_running):
        print(f"Toggling {action.upper()} device {device.device_id} ({device.familiar_name})")
        request_factory = RequestFactory()
        request = request_factory.get("/toggle-device-output/", {"device_id": device.device_id, "state": action})
        response = toggle_device_output(request)

        if isinstance(response, JsonResponse) and response.status_code == 200:
            log_device_event(device, f"Device turned {action.upper()}", "INFO")
            time.sleep(2)  # Prevent rapid API calls
        else:
            log_device_event(device, f"Failed to turn {action.upper()} device. Response: {response.content}", "ERROR")

    else:
        log_device_event(device, f"Device is already {action.upper()}. No action needed.", "DEBUG")






