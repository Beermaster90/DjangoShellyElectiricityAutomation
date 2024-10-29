# shellyapp/shelly_views.py
from django.http import JsonResponse
from .services.shelly_service import ShellyService

auth_key = "Y2Q2MzR1aWQC021EE7FEBA39F38AA563E06CD33FC4BF7BFA35A33585673FBE80259A37F3B92FE0F9D8A14D546F2"

def fetch_device_status(request):
    device_id = request.GET.get("device_id")

    if not device_id:
        return JsonResponse({"error": "Device ID not provided"}, status=400)

    shelly_service = ShellyService(auth_key=auth_key)
    device_status = shelly_service.get_device_status(device_id)
    
    return JsonResponse(device_status)

def toggle_device_output(request):
    device_id = request.GET.get("device_id")
    state = request.GET.get("state")  # 'on' or 'off'

    if not device_id:
        return JsonResponse({"error": "Device ID not provided"}, status=400)
    if state not in ['on', 'off']:
        return JsonResponse({"error": "Invalid state. Use 'on' or 'off'."}, status=400)

    shelly_service = ShellyService(auth_key=auth_key)
    result = shelly_service.set_device_output(device_id, state)

    # Check if the result is a valid JSON
    if "error" in result:
        # Return a JSON error response if an error occurred
        return JsonResponse(result, status=500)

    # If the response isn't JSON, return the result as is
    return JsonResponse(result, safe=False)