from datetime import datetime
from django.shortcuts import render
from django.http import HttpRequest
from .models import ElectricityPrice,ShellyDevice,DeviceLog  # Import your models
from .price_views import get_cheapest_hours
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
from .device_assignment_manager import DeviceAssignmentManager  # Import the manager
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from app.utils.time_utils import TimeUtils
from app.models import DeviceAssignment

def home(request):
    """Renders the home page."""
    assert isinstance(request, HttpRequest)
    return render(
        request,
        'app/index.html',
        {
            'title':'Home Page',
            'year': datetime.now().year,
        }
    )

def contact(request):
    """Renders the contact page."""
    assert isinstance(request, HttpRequest)
    return render(
        request,
        'app/contact.html',
        {
            'title':'Contact',
            'message':'Your contact page.',
            'year': datetime.now().year,
        }
    )

def about(request):
    """Renders the about page."""
    assert isinstance(request, HttpRequest)
    
    # Base queryset: Admins see all logs, users see only their own devices' logs
    logs = DeviceLog.objects.all() if request.user.is_superuser else DeviceLog.objects.filter(device__user=request.user)
    
    # Apply status filtering (if status filter is set)
    status_filter = request.GET.get('status', '')
    if status_filter:
        logs = logs.filter(status=status_filter)

    # Order by latest first & limit results
    logs = logs.order_by("-created_at")[:100]  # Slicing happens after filtering

    return render(
        request,
        'app/about.html',
        {
            'title': 'Logs',
            'message': 'SHOW ME THE LOGS',
            'year': datetime.now().year,
            "logs": logs,
        }
    )


def get_common_context(request):
    """Fetches shared context data, keeping timestamps in UTC (conversion happens in frontend)."""

    # Get current time in UTC
    now_utc = TimeUtils.now_utc()
    start_range = now_utc - timedelta(hours=12)
    end_range = now_utc + timedelta(hours=24)

    # Fetch electricity prices in UTC
    prices = list(
        ElectricityPrice.objects.filter(start_time__range=(start_range, end_range))
        .order_by("start_time")
        .values("id", "start_time", "end_time", "price_kwh")
    )

    # Fetch user's devices
    if request.user.is_superuser:
        devices = ShellyDevice.objects.all()  # Admins see all devices
    else:
        devices = ShellyDevice.objects.filter(user=request.user)  # Users see only their own devices
    selected_device = devices.first()

    # Check if a specific device is selected
    selected_device_id = request.GET.get("device_id")
    if selected_device_id:
        selected_device = devices.filter(device_id=selected_device_id).first()

    # Get user's transfer prices and hours needed
    day_transfer_price = selected_device.day_transfer_price if selected_device else 0
    night_transfer_price = selected_device.night_transfer_price if selected_device else 0
    hours_needed = selected_device.run_hours_per_day if selected_device else 0

    # Fetch assignments and map them to prices
    assignments = DeviceAssignment.objects.filter(user=request.user)
    assigned_devices_map = {}

    for assignment in assignments:
        price_id = assignment.electricity_price.id
        device_id = assignment.device.device_id
        if price_id not in assigned_devices_map:
            assigned_devices_map[price_id] = []
        assigned_devices_map[price_id].append(str(device_id))  # Store as string for JS

    # Add assigned device IDs to price data
    for price in prices:
        price["assigned_devices"] = ",".join(assigned_devices_map.get(price["id"], []))
        price["start_time"] = price["start_time"].isoformat()  # Pass as ISO 8601 (UTC)
        price["end_time"] = price["end_time"].isoformat()  # Pass as ISO 8601 (UTC)

    # Debugging logs
    print(f"Request user: {request.user} ({request.user.is_authenticated})")
    print(f"Devices for user: {devices}")

    # Fetch cheapest hours for user's devices
    assignment_manager = DeviceAssignmentManager(request.user)
    devices = assignment_manager.get_device_cheapest_hours(devices)

    #Set current hour

    current_hour = now_utc.strftime("%Y-%m-%d %H:%M")

    # Pass UTC current time as ISO format for frontend conversion
    return {
        "prices": prices,  # Prices remain in UTC (JS will convert them)
        "devices": devices,
        "selected_device": selected_device,
        "day_transfer_price": day_transfer_price,
        "night_transfer_price": night_transfer_price,
        "hours_needed": hours_needed,
        "current_time": current_hour,  # Example: "2025-03-14 16:00"
        "title": "Landing Page",
        "year": now_utc.year,  # No conversion needed for year
    }

@login_required(login_url='/login/')  # Apply restriction to index
def home(request):
    #"""Landing page view."""
    return render(request, "app/index.html", get_common_context(request))

@login_required(login_url='/login/')  # Apply restriction to index
def index(request):
    #"""ShellyApp index view."""
    return render(request, "app/index.html", get_common_context(request))


