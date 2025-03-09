import requests
from ..models import ShellyDevice  # Import the ShellyDevice model

class ShellyService:
    def __init__(self, device_id):
        """Initialize ShellyService with the correct auth_key and device_name based on device_id."""
        self.base_cloud_url = 'https://shelly-137-eu.shelly.cloud'

        # Fetch Shelly device data dynamically
        shelly_device = ShellyDevice.objects.filter(device_id=device_id).first()
        
        if shelly_device:
            self.auth_key = shelly_device.shelly_api_key  #  Fetch API key from DB
            self.device_name = shelly_device.shelly_device_name  #  Fetch device name
        else:
            self.auth_key = None
            self.device_name = "Unknown Device"

    def get_device_status(self):
        """Fetches the status of a Shelly device using its auth_key and device_name."""
        if not self.auth_key:
            return {"error": "Auth key is required for cloud requests."}
        if not self.device_name:
            return {"error": "Device name is missing for status request."}

        url = f'{self.base_cloud_url}/device/status'
        params = {
            "id": self.device_name,  #  Use `device_name` for status request
            "auth_key": self.auth_key,  #  API Key from DB
        }

        try:
            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            status_data = response.json()

            # Extract the correct Shelly Cloud ID from the status response
            self.shelly_cloud_id = status_data.get("data", {}).get("id")  #  Fetch correct ID

            # Add additional details for consistency
            status_data["shelly_device_name"] = self.device_name
            return status_data
        except requests.RequestException as e:
            return {"error": str(e)}

    def set_device_output(self, state, channel=0):

        """Sets the output state of a Shelly device to 'on' or 'off'."""
        if not self.auth_key:
            return {"error": "Auth key is required for cloud requests."}
        if not self.device_name:
            return {"error": "Device name is missing for status request."}

        url = f'{self.base_cloud_url}/device/relay/control'
        
        # Parameters for the API request
        params = {
            "id": self.device_name,  #  Use `device_name` for status request
            "auth_key": self.auth_key,  #  API Key from DB
        }
        data = {
            "turn": state,  # 'on' or 'off'
            "channel": channel  # Defaults to channel 0 (switch:0)
        }

        try:
            response = requests.post(url, params=params, data=data, timeout=5)
            response.raise_for_status()
            return response.json()  # Parse JSON response
        except requests.RequestException as e:
            return {"error": str(e)}
