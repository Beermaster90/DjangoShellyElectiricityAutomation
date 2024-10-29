# shellyapp/services/shelly_service.py
import requests

class ShellyService:
    def __init__(self, auth_key=None):
        self.auth_key = auth_key
        self.base_cloud_url = 'https://shelly-33-eu.shelly.cloud'  # Updated to match the working endpoint

    def get_device_status(self, device_id):
        """Fetches the status of a Shelly device using auth_key in query parameters."""
        if not self.auth_key:
            return {"error": "Auth key is required for cloud requests."}

        url = f'{self.base_cloud_url}/device/status'
        params = {
            "id": device_id,
            "auth_key": self.auth_key  # Add auth_key as a query parameter
        }

        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
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