# shellyapp/shelly_views.py
from django.http import JsonResponse
from .services.shelly_service import ShellyService
from .models import ShellyDevice

import logging

logger = logging.getLogger(__name__)  # Django logging

from django.http import JsonResponse
from .services.shelly_service import ShellyService
from .models import ShellyDevice
import logging

logger = logging.getLogger(__name__)  # Django logging

from django.http import JsonResponse
from .services.shelly_service import ShellyService
from .models import ShellyDevice
import logging

logger = logging.getLogger(__name__)  # Django logging

def fetch_device_status(request):
    device_id = request.GET.get("device_id")

    if not device_id:
        return JsonResponse({"error": "Device ID not provided"}, status=400)

    # Fetch Shelly status
    shelly_service = ShellyService(device_id=device_id)
    raw_status = shelly_service.get_device_status(device_id)

    # Fetch device name from database
    shelly_device = ShellyDevice.objects.filter(device_id=device_id).first()
    device_name = shelly_device.familiar_name if shelly_device else "Unknown Device"

    # If there's an error, return response immediately
    if "error" in raw_status:
        return JsonResponse({
            "device_id": device_id,
            "device_name": device_name,
            "online": False,
            "running": "unknown",
            "error": raw_status["error"]
        }, status=500)

    # Extract the relevant data
    device_data = raw_status.get("data", {})
    is_online = device_data.get("online", False)

    # Extract relay state from `switch:0` `output`
    is_running = "unknown"
    if "device_status" in device_data:
        status_data = device_data["device_status"]

        if "switch:0" in status_data:
            switch_data = status_data["switch:0"]
            
            # **Ensure the `output` field is properly checked**
            if "output" in switch_data and switch_data["output"]:  
                is_running = "Running"
            else:
                is_running = "Stopped"

    # DEBUGGING LOGS
    logger.info(f"Device Status for {device_id}: Online={is_online}, Running={is_running}")
    print(f"DEBUG: Device {device_id} - Online: {is_online}, Running: {is_running}")

    return JsonResponse({
        "device_id": device_id,
        "device_name": device_name,
        "online": is_online,
        "running": is_running
    })


def toggle_device_output(request):
    device_id = request.GET.get("device_id")
    state = request.GET.get("state")  # 'on' or 'off'

    if not device_id:
        return JsonResponse({"error": "Device ID not provided"}, status=400)
    if state not in ['on', 'off']:
        return JsonResponse({"error": "Invalid state. Use 'on' or 'off'."}, status=400)

    # Initialize ShellyService with device_id
    shelly_service = ShellyService(device_id=device_id)
    result = shelly_service.set_device_output(device_id, state)

    # Check if the result contains an error
    if "error" in result:
        return JsonResponse(result, status=500)

    return JsonResponse(result, safe=False)
