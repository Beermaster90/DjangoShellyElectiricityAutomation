from .models import DeviceLog
from .utils.security_utils import SecurityUtils


def log_device_event(device, message, status="INFO"):
    """
    Logs events related to a Shelly device in the DeviceLog model.
    Automatically sanitizes sensitive information from the message.
    """
    # Sanitize the message to hide sensitive tokens/keys
    safe_message = SecurityUtils.sanitize_message(message)

    DeviceLog.objects.create(device=device, message=safe_message, status=status)
