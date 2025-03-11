from .models import DeviceLog

def log_device_event(device, message, status="INFO"):
    """
    Logs events related to a Shelly device in the DeviceLog model.
    """
    DeviceLog.objects.create(device=device, message=message, status=status)