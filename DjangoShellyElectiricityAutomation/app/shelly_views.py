# shellyapp/shelly_views.py
from django.http import JsonResponse
from .services.shelly_service import ShellyService
from .models import ShellyDevice, DeviceLog

def log_device_event(device, message, status="INFO"):
    """
    Logs events related to a Shelly device in the DeviceLog model.
    """
    DeviceLog.objects.create(device=device, message=message, status=status)

def fetch_device_status(request):
    device_id = request.GET.get("device_id")

    if not device_id:
        log_device_event(None, "Device ID not provided in fetch request", "ERROR")
        return JsonResponse({"error": "Device ID not provided"}, status=400)

    try:
        # Initialize Shelly Service
        shelly_service = ShellyService(device_id)
        raw_status = shelly_service.get_device_status()

        # Fetch device from database
        device = ShellyDevice.objects.filter(device_id=device_id).first()
        device_name = device.familiar_name if device else "Unknown Device"

        if "error" in raw_status:
            log_device_event(device, f"Error fetching status: {raw_status['error']}", "ERROR")
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
        is_running = "unknown"

        if "device_status" in device_data:
            status_data = device_data["device_status"]
            if "switch:0" in status_data:
                switch_data = status_data["switch:0"]
                is_running = "Running" if switch_data.get("output", False) else "Stopped"

        # Log device status retrieval
        log_device_event(device, f"Status fetched: Online={is_online}, Running={is_running}", "INFO")

        return JsonResponse({
            "device_id": device_id,
            "device_name": device_name,
            "online": is_online,
            "running": is_running
        })

    except Exception as e:
        log_device_event(None, f"Exception in fetch_device_status: {e}", "ERROR")
        return JsonResponse({"error": "Internal Server Error"}, status=500)



def toggle_device_output(request):
    """
    Toggles a Shelly device ON or OFF, ensuring the correct Shelly Cloud ID and API key are used.
    """
    device_id = request.GET.get("device_id")
    state = request.GET.get("state")  # 'on' or 'off'

    if not device_id:
        return JsonResponse({"error": "Device ID not provided"}, status=400)
    if state not in ['on', 'off']:
        return JsonResponse({"error": "Invalid state. Use 'on' or 'off'."}, status=400)

    # Initialize Shelly Service
    shelly_service = ShellyService(device_id)
    
    # Fetch device name from the service
    device_name = shelly_service.device_name

    # Send the command to toggle the device using the correct Shelly Cloud ID
    result = shelly_service.set_device_output(state=state)

    if "error" in result:
        return JsonResponse({
            "device_id": device_id,
            "device_name": device_name,
            "error": result["error"]
        }, status=500)

    return JsonResponse({
        "device_id": device_id,
        "device_name": device_name,
        "state": state,
        "status": "success"
    }, safe=False)
