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
from app.utils.db_utils import with_db_retries
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
    @with_db_retries(max_attempts=3, delay=1)
    def control_shelly_devices() -> None:
        """Loops through all Shelly devices and toggles them based on pre-assigned cheapest 15-minute periods."""
        try:
            current_time = TimeUtils.now_utc()
            
            # Find the current 15-minute period
            current_minutes = current_time.minute
            period_start_minutes = (current_minutes // 15) * 15
            
            # Calculate start and end of current period
            start_time = current_time.replace(
                minute=period_start_minutes,
                second=0,
                microsecond=0
            )
            end_time = start_time + timedelta(minutes=14, seconds=59)
            
            # Log period boundaries for debugging
            log_device_event(
                None,
                f"Checking device states for period {start_time.strftime('%Y-%m-%d %H:%M')} to {end_time.strftime('%Y-%m-%d %H:%M')}",
                "INFO"
            )
            
            # Get active price period and any assignments for this period
            active_prices = ElectricityPrice.objects.filter(
                start_time__range=(start_time, end_time)
            )
            active_price_ids = list(active_prices.values_list("id", flat=True))
            
            # Only process devices with automation enabled (status = 1)
            devices = ShellyDevice.objects.filter(status=1)
            
            if not devices.exists():
                log_device_event(None, "No devices with automation enabled found", "INFO")
                return
            
            # Check for new price assignments and update device states accordingly
            assignment_updates = []
            for device in devices:
                # Check if this 15-minute period is assigned
                assigned = DeviceAssignment.objects.filter(
                    device=device,
                    electricity_price_id__in=active_price_ids
                ).exists()
                
                # Get the device's current running state to minimize unnecessary toggles
                shelly_service = ShellyService(device.device_id)
                device_status = shelly_service.get_device_status()
                
                if "error" in device_status:
                    log_device_event(
                        device,
                        f"Error fetching status during period check: {device_status['error']}",
                        "ERROR"
                    )
                    continue
                
                is_running = (
                    device_status.get("data", {})
                    .get("device_status", {})
                    .get("switch:0", {})
                    .get("output", False)
                )
                
                # Log the current state and assignment
                log_device_event(
                    device,
                    f"Period {start_time.strftime('%Y-%m-%d %H:%M')} - "
                    f"Assigned: {assigned}, Currently Running: {is_running}",
                    "INFO"
                )
                
                # Store the update info to process after all checks
                assignment_updates.append({
                    'device': device,
                    'assigned': assigned,
                    'is_running': is_running
                })
            
            # Process all updates after checking all devices
            for update in assignment_updates:
                device = update['device']
                assigned = update['assigned']
                is_running = update['is_running']
                
                # Only toggle if the current state doesn't match the desired state
                if assigned and not is_running:
                    DeviceController.toggle_shelly_device(device, "on")
                    time.sleep(2)  # Add delay between device operations
                elif not assigned and is_running:
                    DeviceController.toggle_shelly_device(device, "off")
                    time.sleep(2)  # Add delay between device operations
        except Exception as e:
            log_device_event(None, f"Error controlling Shelly devices: {e}", "ERROR")

    @staticmethod
    def toggle_shelly_device(device: ShellyDevice, action: str) -> None:
        """Helper function to toggle a Shelly device ON or OFF."""
        # Get the last logged state to minimize API calls
        last_log = DeviceLog.objects.filter(device=device).order_by('-created_at').first()
        last_action = None
        if last_log and (datetime.now(pytz.UTC) - last_log.created_at).total_seconds() < 60:  # Only trust state if recent
            message = last_log.message.lower()
            if "turned on" in message:
                last_action = "on"
            elif "turned off" in message:
                last_action = "off"
                
        # If the last action matches what we want to do, skip the API call
        if last_action == action:
            log_device_event(
                device,
                f"Skipping {action} command - device already in desired state",
                "INFO"
            )
            return

        shelly_service = ShellyService(device.device_id)
        device_status = shelly_service.get_device_status()
        
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
