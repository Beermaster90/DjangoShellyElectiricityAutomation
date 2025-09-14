import requests
import time
from datetime import datetime, timedelta
from django.urls import reverse
from django.utils.timezone import now
from django.conf import settings
from django.test import RequestFactory
from django.http import JsonResponse
from app.models import ShellyDevice, ElectricityPrice, DeviceLog, DeviceAssignment
from app.shelly_views import toggle_device_output, fetch_device_status
from app.services.shelly_service import ShellyService
from app.price_views import call_fetch_prices, get_cheapest_hours
from .logger import log_device_event
from app.utils.time_utils import TimeUtils
import pytz
from typing import Optional


class DeviceController:
    """Controller for scheduled device and price operations."""

    @staticmethod
    def fetch_electricity_prices() -> None:
        """Calls the Django view to fetch electricity prices internally."""
        try:
            response = call_fetch_prices(None)
            if isinstance(response, JsonResponse) and response.status_code != 200:
                log_device_event(
                    None,
                    f"Schedule failed to fetch electricity prices. Response: {response.content}",
                    "ERROR",
                )
        except Exception as e:
            log_device_event(None, f"Error calling fetch-prices: {e}", "ERROR")

    @staticmethod
    def control_shelly_devices() -> None:
        """Loops through all Shelly devices and toggles them based on pre-assigned cheapest hours."""
        try:
            current_time = TimeUtils.now_utc()
            start_of_hour = current_time.replace(minute=0, second=0, microsecond=0)
            end_of_hour = start_of_hour + timedelta(minutes=59, seconds=59)
            active_prices = ElectricityPrice.objects.filter(
                start_time__range=(start_of_hour, end_of_hour)
            )
            active_price_ids = list(active_prices.values_list("id", flat=True))
            # Only process devices with automation enabled (status = 1)
            devices = ShellyDevice.objects.filter(status=1)
            
            if not devices.exists():
                log_device_event(None, "No devices with automation enabled found", "INFO")
                return
            
            for device in devices:
                assigned = DeviceAssignment.objects.filter(
                    device=device, electricity_price_id__in=active_price_ids
                ).exists()
                if not assigned:
                    DeviceController.toggle_shelly_device(device, "off")
                    continue
                DeviceController.toggle_shelly_device(device, "on")
        except Exception as e:
            log_device_event(None, f"Error controlling Shelly devices: {e}", "ERROR")

    @staticmethod
    def toggle_shelly_device(device: ShellyDevice, action: str) -> None:
        """Helper function to toggle a Shelly device ON or OFF."""
        shelly_service = ShellyService(device.device_id)
        device_status = shelly_service.get_device_status()
        time.sleep(1.2)
        if "error" in device_status:
            log_device_event(
                device, f"Error fetching status: {device_status['error']}", "ERROR"
            )
            return
        is_running = (
            device_status.get("data", {})
            .get("device_status", {})
            .get("switch:0", {})
            .get("output", False)
        )
        time.sleep(1.2)
        if (action == "off" and is_running) or (action == "on" and not is_running):
            request_factory = RequestFactory()
            request = request_factory.get(
                "/toggle-device-output/",
                {"device_id": device.device_id, "state": action},
            )
            response = toggle_device_output(request)
            if isinstance(response, JsonResponse) and response.status_code == 200:
                # Check if the response was blocked by debug setting
                try:
                    response_data = response.json() if hasattr(response, "json") else {}
                except:
                    response_data = {}

                if response_data.get("status") == "blocked":
                    log_device_event(
                        device,
                        f"Device toggle BLOCKED by SHELLY_STOP_REST_DEBUG: {response_data.get('message', 'No message')}",
                        "INFO",
                    )
                else:
                    log_device_event(device, f"Device turned {action.upper()}", "INFO")
                time.sleep(2)
            else:
                log_device_event(
                    device,
                    f"Failed to turn {action.upper()} device. Response: {response.content}",
                    "ERROR",
                )
