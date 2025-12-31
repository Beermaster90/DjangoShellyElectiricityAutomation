import requests
from ..models import (
    ShellyDevice,
    ShellyTemperature,
    AppSetting,
)  # Import the ShellyDevice model and AppSetting
from ..utils.security_utils import SecurityUtils
from ..utils.rate_limiter import shelly_rate_limiter
import time
from decimal import Decimal


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

        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # Wait if needed to comply with rate limits (per server+token combination)
                shelly_rate_limiter.wait_if_needed(self.base_cloud_url, self.auth_key)
                
                response = requests.get(url, params=params, timeout=15)  # Further increased timeout
                
                if response.status_code == 429:  # Too Many Requests
                    shelly_rate_limiter.record_failure(self.base_cloud_url, self.auth_key)
                    retry_count += 1
                    if retry_count < max_retries:
                        continue
                    else:
                        raise requests.RequestException("Rate limit exceeded after retries")
                
                response.raise_for_status()
                status_data = response.json()
                
                # Record successful request
                shelly_rate_limiter.record_success(self.base_cloud_url, self.auth_key)

                # Extract the correct Shelly Cloud ID from the status response
                self.shelly_cloud_id = status_data.get("data", {}).get(
                    "id"
                )  #  Fetch correct ID

                # Add additional details for consistency
                status_data["shelly_device_name"] = self.device_name
                return status_data
                
            except requests.RequestException as e:
                # Check if we should retry
                if retry_count < max_retries - 1:
                    shelly_rate_limiter.record_failure(self.base_cloud_url, self.auth_key)
                    retry_count += 1
                    continue
                    
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

        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # Wait if needed to comply with rate limits (per server+token combination)
                shelly_rate_limiter.wait_if_needed(self.base_cloud_url, self.auth_key)
                
                response = requests.post(url, params=params, data=data, timeout=15)
                
                if response.status_code == 429:  # Too Many Requests
                    shelly_rate_limiter.record_failure(self.base_cloud_url, self.auth_key)
                    retry_count += 1
                    if retry_count < max_retries:
                        continue
                    else:
                        raise requests.RequestException("Rate limit exceeded after retries")
                
                response.raise_for_status()
                
                # Record successful request
                shelly_rate_limiter.record_success(self.base_cloud_url, self.auth_key)
                
                return response.json()  # Parse JSON response
                
            except requests.RequestException as e:
                # Check if we should retry
                if retry_count < max_retries - 1:
                    shelly_rate_limiter.record_failure(self.base_cloud_url, self.auth_key)
                    retry_count += 1
                    continue
                    
                # Sanitize error message to hide sensitive information
                safe_error = SecurityUtils.get_safe_error_message(
                    e, "Shelly device control failed"
                )
                return {"error": safe_error}


class ShellyTemperatureService:
    def __init__(self, device_id):
        """Initialize ShellyTemperatureService with the correct auth_key and device_name."""
        temperature_device = ShellyTemperature.objects.filter(device_id=device_id).first()

        if temperature_device:
            self.auth_key = temperature_device.shelly_api_key
            self.device_name = temperature_device.shelly_device_name
            self.base_cloud_url = temperature_device.shelly_server
        else:
            self.auth_key = None
            self.device_name = "Unknown Device"
            self.base_cloud_url = "Unknown"

    def get_device_status(self):
        """Fetches the status of a Shelly temperature device."""
        if not self.auth_key:
            return {"error": "Auth key is required for cloud requests."}
        if not self.device_name:
            return {"error": "Device name is missing for status request."}

        url = f"{self.base_cloud_url}/device/status"
        params = {
            "id": self.device_name,
            "auth_key": self.auth_key,
        }

        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                shelly_rate_limiter.wait_if_needed(self.base_cloud_url, self.auth_key)
                response = requests.get(url, params=params, timeout=15)

                if response.status_code == 429:
                    shelly_rate_limiter.record_failure(self.base_cloud_url, self.auth_key)
                    retry_count += 1
                    if retry_count < max_retries:
                        continue
                    raise requests.RequestException("Rate limit exceeded after retries")

                response.raise_for_status()
                status_data = response.json()
                shelly_rate_limiter.record_success(self.base_cloud_url, self.auth_key)
                status_data["shelly_device_name"] = self.device_name
                return status_data

            except requests.RequestException as e:
                if retry_count < max_retries - 1:
                    shelly_rate_limiter.record_failure(self.base_cloud_url, self.auth_key)
                    retry_count += 1
                    continue

                safe_error = SecurityUtils.get_safe_error_message(
                    e, "Shelly temperature request failed"
                )
                return {"error": safe_error}


def extract_temperature_c(status_data):
    """Extract temperature in Celsius from a Shelly device status payload."""
    device_status = status_data.get("data", {}).get("device_status", {})

    def to_celsius(value):
        if isinstance(value, (int, float, Decimal)):
            return float(value)
        return None

    def parse_block(block):
        if isinstance(block, (int, float, Decimal)):
            return float(block)
        if not isinstance(block, dict):
            return None
        for key in ("tC", "tempC", "temperature", "value", "t"):
            if key in block:
                temp = to_celsius(block.get(key))
                if temp is not None:
                    return temp
        if "tF" in block:
            temp_f = to_celsius(block.get("tF"))
            if temp_f is not None:
                return (temp_f - 32) * 5 / 9
        return None

    for key, block in device_status.items():
        if key.startswith(("temperature:", "ht:")):
            temp = parse_block(block)
            if temp is not None:
                return temp

    for key in ("tmp", "temperature", "temperature:0", "sensor", "sensor:0", "ht", "ht:0"):
        if key in device_status:
            temp = parse_block(device_status.get(key))
            if temp is not None:
                return temp

    return None
