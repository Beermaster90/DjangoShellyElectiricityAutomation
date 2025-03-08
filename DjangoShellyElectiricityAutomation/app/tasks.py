import requests
from datetime import datetime
from django.urls import reverse
from django.utils.timezone import now
from django.conf import settings
from django.test import RequestFactory
from django.http import JsonResponse
from app.models import ShellyDevice, ElectricityPrice
from app.shelly_views import toggle_device_output, fetch_device_status
from app.services.shelly_service import ShellyService
from app.price_views import call_fetch_prices


def fetch_electricity_prices():
    """
    Calls the Django view to fetch electricity prices internally.
    """
    try:
        response = call_fetch_prices(None)  # Call the view function directly

        if isinstance(response, JsonResponse) and response.status_code == 200:
            print("Electricity prices fetched successfully.")
        else:
            print(f"Failed to fetch electricity prices. Response: {response.content}")

    except Exception as e:
        print(f"Error calling fetch-prices: {e}")


def control_shelly_devices():
    """
    Loops through all Shelly devices, fetches their current status, and toggles them based on electricity price.
    """
    try:
        # Get the cheapest electricity price for the day
        cheapest_price = ElectricityPrice.objects.order_by("price_kwh").first()

        if not cheapest_price:
            print("No electricity price data available.")
            return

        current_hour = now().hour
        device_list = ShellyDevice.objects.all()

        for device in device_list:
            if not device.shelly_api_key:
                print(f"Skipping device {device.device_id} (Missing API Key)")
                continue  # Skip this device if no auth key is present

            # Fetch the current status of the device before toggling
            shelly_service = ShellyService(device_id=device.device_id)
            device_status = shelly_service.get_device_status(device.device_id)

            if "error" in device_status:
                print(f"Error fetching status for Device {device.device_id}: {device_status['error']}")
                continue  # Skip this device if the status couldn't be retrieved

            is_online = device_status.get("data", {}).get("online", False)
            switch_data = device_status.get("data", {}).get("device_status", {}).get("switch:0", {})
            is_running = switch_data.get("output", False)  # Check if it's already running

            print(f"Device {device.device_id} Status: Online={is_online}, Running={is_running}")

            # Determine if we should toggle the device ON or OFF
            if current_hour == cheapest_price.start_time.hour and not is_running:
                state = "on"
            elif current_hour != cheapest_price.start_time.hour and is_running:
                state = "off"
            else:
                print(f"Device {device.device_id} is already in the correct state.")
                continue  # No need to toggle

            # Send request to toggle the device via Shelly Cloud API
            request_factory = RequestFactory()
            request = request_factory.get("/toggle-device-output/", {"device_id": device.device_id, "state": state})
            response = toggle_device_output(request)

            if isinstance(response, JsonResponse) and response.status_code == 200:
                print(f"Device {device.device_id} toggled {state} successfully.")
            else:
                print(f"Failed to toggle device {device.device_id}. Response: {response.content}")

    except Exception as e:
        print(f"Error controlling Shelly devices: {e}")
