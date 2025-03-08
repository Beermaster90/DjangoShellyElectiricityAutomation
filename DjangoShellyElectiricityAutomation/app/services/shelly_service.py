import requests
from ..models import ShellyDevice  # Import the ShellyDevice model

class ShellyService:
    def __init__(self, device_id):
        """Initialize ShellyService with the correct auth_key based on device_id."""
        self.base_cloud_url = 'https://shelly-137-eu.shelly.cloud'

        # Fetch Shelly device data dynamically
        shelly_device = ShellyDevice.objects.filter(device_id=device_id).first()
        
        if shelly_device:
            self.auth_key = shelly_device.shelly_api_key
            self.device_name = shelly_device.shelly_device_name
        else:
            self.auth_key = None
            self.device_name = "Unknown Device"

    def get_device_status(self, device_id):
        """Fetches the status of a Shelly device using its auth_key."""
        if not self.auth_key:
            return {"error": "Auth key is required for cloud requests."}

        url = f'{self.base_cloud_url}/device/status'
        params = {
            "id": self.device_name,
            "auth_key": self.auth_key,  # Auth key fetched dynamically
        }

        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            status_data = response.json()

            # Optionally, add the device name in the response
            status_data["shelly_device_name"] = self.device_name

            return status_data
        except requests.RequestException as e:
            return {"error": str(e)}



    def set_device_output(self, device_id, state, channel=0):
        """Sets the output state of a Shelly device to 'on' or 'off'."""
        if not self.auth_key:
            return {"error": "Auth key is required for cloud requests."}

        url = f'{self.base_cloud_url}/device/relay/control'
        
        # Parameters to be included in the POST body
        data = {
            "turn": state,  # 'on' or 'off'
            "channel": channel  # Set to 0 by default for `switch:0`
        }

        # Params to be included in the URL
        params = {
            "id": device_id,
            "auth_key": self.auth_key
        }

        try:
            # Make a POST request with URL parameters and data in the body
            response = requests.post(url, params=params, data=data)
            response.raise_for_status()
            return response.json()  # Parse JSON response
        except requests.RequestException as e:
            return {"error": str(e)}