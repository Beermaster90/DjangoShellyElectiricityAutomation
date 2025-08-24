import requests
from ..models import (
    ShellyDevice,
    AppSetting,
)  # Import the ShellyDevice model and AppSetting
from ..utils.security_utils import SecurityUtils
import time


class ShellyService:
    def __init__(self, device_id):
        """Initialize ShellyService with the correct auth_key and device_name based on device_id."""
        # Fetch Shelly device data dynamically
        shelly_device = ShellyDevice.objects.filter(device_id=device_id).first()

        if shelly_device:
            self.auth_key = shelly_device.shelly_api_key  #  Fetch API key from DB
            self.device_name = shelly_device.shelly_device_name  #  Fetch device name
            self.base_cloud_url = (
                shelly_device.shelly_server
            )  # Fetch Configured API Server
            self.relay_channel = shelly_device.relay_channel or 0
        else:
            self.auth_key = None
            self.device_name = "Unknown Device"
            self.base_cloud_url = "Unknown"
            self.relay_channel = 0

    def get_device_status(self):
        """Fetches the status of a Shelly device using its auth_key and device_name."""
        if not self.auth_key:
            return {"error": "Auth key is required for cloud requests."}
        if not self.device_name:
            return {"error": "Device name is missing for status request."}

        url = f"{self.base_cloud_url}/device/status"
        params = {
            "id": self.device_name,  #  Use `device_name` for status request
            "auth_key": self.auth_key,  #  API Key from DB
        }

        try:
            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            status_data = response.json()

            # Extract the correct Shelly Cloud ID from the status response
            self.shelly_cloud_id = status_data.get("data", {}).get(
                "id"
            )  #  Fetch correct ID

            # Add additional details for consistency
            status_data["shelly_device_name"] = self.device_name
            return status_data
        except requests.RequestException as e:
            # Sanitize error message to hide sensitive information
            safe_error = SecurityUtils.get_safe_error_message(
                e, "Shelly API request failed"
            )
            return {"error": safe_error}

    def set_device_output(self, state, channel=None):
        """Sets the output state of a Shelly device to 'on' or 'off'."""

        # Check if REST debugging is enabled (blocks all REST calls when value is "1")
        try:
            debug_setting = AppSetting.objects.filter(
                key="SHELLY_STOP_REST_DEBUG"
            ).first()
            if debug_setting and debug_setting.value == "1":
                return {
                    "status": "blocked",
                    "message": f"REST call blocked by SHELLY_STOP_REST_DEBUG setting. Would have turned device {state}.",
                    "device_name": self.device_name,
                    "requested_state": state,
                }
        except Exception as e:
            # If there's an issue checking the setting, log it but don't block the call
            print(f"Warning: Could not check SHELLY_STOP_REST_DEBUG setting: {e}")

        if not self.auth_key:
            return {"error": "Auth key is required for cloud requests."}
        if not self.device_name:
            return {"error": "Device name is missing for status request."}

        url = f"{self.base_cloud_url}/device/relay/control"

        # Parameters for the API request
        params = {
            "id": self.device_name,  #  Use `device_name` for status request
            "auth_key": self.auth_key,  #  API Key from DB
        }
        data = {
            "turn": state,  # 'on' or 'off'
            "channel": (
                channel if channel is not None else self.relay_channel
            ),  # Use device's default if not passed
        }

        try:
            response = requests.post(url, params=params, data=data, timeout=5)
            response.raise_for_status()
            return response.json()  # Parse JSON response
        except requests.RequestException as e:
            # Sanitize error message to hide sensitive information
            safe_error = SecurityUtils.get_safe_error_message(
                e, "Shelly device control failed"
            )
            return {"error": safe_error}
