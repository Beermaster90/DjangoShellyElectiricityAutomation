from datetime import datetime
from django.shortcuts import render
from django.http import HttpRequest
from .models import ElectricityPrice,ShellyDevice,DeviceLog  # Import your models
from .price_views import get_cheapest_hours
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta

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
    # Get Logs
    logs = DeviceLog.objects.order_by("-created_at")[:50]  # Get last 50 logs
    return render(
        request,
        'app/about.html',
        {
            'title':'Logs',
            'message':'SHOW ME THE LOGS',
            'year': datetime.now().year,
            "logs": logs,
        }
    )

def get_common_context(request):
    """Helper function to fetch shared context data for views."""


    now = datetime.now()  # No need for timezone conversion
    start_range = now - timedelta(hours=12)
    end_range = now + timedelta(hours=12)

    prices = list(
        ElectricityPrice.objects.filter(start_time__range=(start_range, end_range))
        .order_by("start_time")
        .values("start_time", "end_time", "price_kwh")
    )


    devices = ShellyDevice.objects.all()
    selected_device = devices.first()

    selected_device_id = request.GET.get("device_id")
    if selected_device_id:
        selected_device = ShellyDevice.objects.filter(device_id=selected_device_id).first()

    day_transfer_price = selected_device.day_transfer_price if selected_device else 0
    night_transfer_price = selected_device.night_transfer_price if selected_device else 0
    hours_needed = selected_device.run_hours_per_day if selected_device and hasattr(selected_device, 'run_hours_per_day') else 0

    # Compute cheapest hours per **each device**
    for device in devices:
        device_hours_needed = device.run_hours_per_day if hasattr(device, 'run_hours_per_day') else 0
        device_cheapest_hours = get_cheapest_hours(prices, device.day_transfer_price, device.night_transfer_price, device_hours_needed)
        device.cheapest_hours = [dt.strftime("%H:%M") for dt in device_cheapest_hours]

    # **Ensure the current hour is passed**
    current_hour = datetime.now().strftime("%H")  # Get current hour in "HH" format

    return {
        "prices": prices,
        "devices": devices,
        "selected_device": selected_device,
        "day_transfer_price": day_transfer_price,
        "night_transfer_price": night_transfer_price,
        "hours_needed": hours_needed,
        "current_hour": current_hour, 
        "title": "Landing Page",
        "year": datetime.now().year,
    }


@login_required(login_url='/login/')  # Apply restriction to index
def home(request):
    #"""Landing page view."""
    return render(request, "app/index.html", get_common_context(request))

@login_required(login_url='/login/')  # Apply restriction to index
def index(request):
    #"""ShellyApp index view."""
    return render(request, "app/index.html", get_common_context(request))


