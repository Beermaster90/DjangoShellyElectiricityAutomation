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
from app.price_views import call_fetch_prices,get_cheapest_hours,set_cheapest_hours

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

        if isinstance(response, JsonResponse) and response.status_code == 200:
            log_device_event(None, "Electricity prices fetched successfully.", "INFO")
        else:
            log_device_event(None, f"Failed to fetch electricity prices. Response: {response.content}", "ERROR")

    except Exception as e:
        log_device_event(None, f"Error calling fetch-prices: {e}", "ERROR")

def control_shelly_devices():
    """
    Loops through all Shelly devices and toggles them based on pre-assigned cheapest hours.
    """
    try:

        current_time = datetime.now()  # Local time as an integer
        current_hour = datetime.now().hour  # Local time as an integer

        print(f"Checking devices for {current_time} (Hour: {current_hour})")  # Debugging log

        # Fetch all electricity prices for the current hour
        active_prices = ElectricityPrice.objects.filter(start_time__hour=current_hour)

        if not active_prices:
            print("No active price entries for this hour.")
            log_device_event(None, "No active price entries for this hour.", "INFO")
            return

        # Fetch all devices
        devices = ShellyDevice.objects.all()

        for device in devices:
            print(f"Processing device: {device.device_id} ({device.familiar_name})")

            assigned = False  # Flag to check if device is scheduled for this hour

            # Check if this device ID exists in any price entry
            for price_entry in active_prices:
                if not price_entry.assigned_devices:
                    continue  # Skip empty assignments

                assigned_devices = price_entry.assigned_devices.split(",")  # Convert to list

                if str(device.device_id) in assigned_devices:
                    assigned = True
                    break  # No need to check further

            if not assigned:
                print(f"Device {device.familiar_name} is NOT assigned for this hour.")
                log_device_event(device, f"Device is NOT assigned for this hour.", "INFO")
                continue  # Skip this device

            # Device is assigned, check if it is already running
            shelly_service = ShellyService(device.device_id)
            device_status = shelly_service.get_device_status()

            if "error" in device_status:
                log_device_event(device, f"Error fetching status: {device_status['error']}", "ERROR")
                continue  # Skip if status fetch failed

            is_running = device_status.get("data", {}).get("device_status", {}).get("switch:0", {}).get("output", False)

            if not is_running:
                # Toggle device ON
                print(f"Toggling ON device {device.device_id} ({device.familiar_name})")
                request_factory = RequestFactory()
                request = request_factory.get("/toggle-device-output/", {"device_id": device.device_id, "state": "on"})
                response = toggle_device_output(request)

                if isinstance(response, JsonResponse) and response.status_code == 200:
                    log_device_event(device, "Device turned ON", "INFO")
                    time.sleep(2) #Just in case 2 secs sleep if too often api calls
                else:
                    log_device_event(device, f"Failed to turn ON device. Response: {response.content}", "ERROR")

            else:
                print(f"Device {device.familiar_name} is already running. No action needed.")
                log_device_event(device, "Device already ON, no action needed.", "INFO")

    except Exception as e:
        log_device_event(None, f"Error controlling Shelly devices: {e}", "ERROR")



def assign_cheapest_hours():
    """
    Calls set_cheapest_hours() to assign devices to the cheapest hours.
    This avoids duplication and ensures logic is maintained in one place.
    """
    print("assign_cheapest_hours() is calling set_cheapest_hours()...")
    set_cheapest_hours()
    print("assign_cheapest_hours() completed.")




