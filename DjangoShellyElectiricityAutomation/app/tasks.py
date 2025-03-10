import requests,time
from datetime import datetime,timedelta
from django.urls import reverse
from django.utils.timezone import now
from django.conf import settings
from django.test import RequestFactory
from django.http import JsonResponse
from app.models import ShellyDevice, ElectricityPrice, DeviceLog  # Include DeviceLog
from app.shelly_views import toggle_device_output, fetch_device_status
from app.services.shelly_service import ShellyService
from app.price_views import call_fetch_prices,get_cheapest_hours

def log_device_event(device, message, status="INFO"):
    """
    Logs events related to a Shelly device or system-wide events.
    """
    DeviceLog.objects.create(device=device if device else None, message=message, status=status)


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
    """
    try:
        current_time = datetime.now()  # Local time
        current_hour = current_time.hour

        print(f"Checking devices for {current_time} (Hour: {current_hour})")  # Debugging log

        # Fetch ElectricityPrice entries for the current hour
        active_prices = ElectricityPrice.objects.filter(
            start_time__hour=current_hour,
            start_time__date=current_time.date()
        )

        # Fetch all devices
        devices = ShellyDevice.objects.all()

        for device in devices:
            print(f"Processing device: {device.device_id} ({device.familiar_name})")

            assigned = False  # Flag to check if the device is assigned

            # Loop through electricity prices and check if the device is assigned
            for price_entry in active_prices:
                if not price_entry.assigned_devices:
                    continue  # Skip if there are no assigned devices

                assigned_devices = [x.strip() for x in price_entry.assigned_devices.split(",")]  # Convert to list and strip spaces

                if str(device.device_id) in assigned_devices:
                    assigned = True
                    break  # No need to check further

            if not assigned:
                print(f"Device {device.familiar_name} is NOT assigned for this hour. Stopping it.")
                toggle_shelly_device(device, "off")
                continue  # Skip further checks for this device

            # Device is assigned, check if it is already running
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
        log_device_event(device, f"Device is already {action.upper()}. No action needed.", "INFO")






