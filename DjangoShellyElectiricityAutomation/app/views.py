from datetime import datetime, timedelta
from django.shortcuts import render
from django.http import HttpRequest, JsonResponse
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import ElectricityPrice, ShellyDevice, DeviceLog, DeviceAssignment
from .price_views import get_cheapest_hours
from .device_assignment_manager import DeviceAssignmentManager
from app.utils.time_utils import TimeUtils
from typing import Dict, Any
from django.contrib.admin.views.decorators import staff_member_required
from django.urls import reverse
import json
import pytz

def get_common_context(request: HttpRequest) -> Dict[str, Any]:
    """Fetches shared context data, keeping timestamps in UTC (conversion happens in frontend)."""
    now_utc = TimeUtils.now_utc()
    start_range = now_utc - timedelta(hours=12)
    end_range = now_utc + timedelta(hours=24)

    prices = list(
        ElectricityPrice.objects.filter(start_time__range=(start_range, end_range))
        .order_by("start_time")
        .values("id", "start_time", "end_time", "price_kwh")
    )

    if request.user.is_superuser:
        devices = ShellyDevice.objects.all()
        assignments = DeviceAssignment.objects.select_related('device', 'electricity_price').all()
    else:
        devices = ShellyDevice.objects.filter(user=request.user)
        assignments = DeviceAssignment.objects.filter(user=request.user)
    selected_device = devices.first()

    selected_device_id = request.GET.get("device_id")
    if selected_device_id:
        selected_device = devices.filter(device_id=selected_device_id).first()

    day_transfer_price = selected_device.day_transfer_price if selected_device else 0
    night_transfer_price = selected_device.night_transfer_price if selected_device else 0
    hours_needed = selected_device.run_hours_per_day if selected_device else 0

    # Build a map of price_id -> list of assigned device_ids
    assigned_devices_map = {}
    for assignment in assignments:
        price_id = assignment.electricity_price.id
        device_id = assignment.device.device_id
        if price_id not in assigned_devices_map:
            assigned_devices_map[price_id] = []
        assigned_devices_map[price_id].append(str(device_id))

    for price in prices:
        price["assigned_devices"] = ",".join(assigned_devices_map.get(price["id"], []))
        price["start_time"] = price["start_time"].isoformat()
        price["end_time"] = price["end_time"].isoformat()

    assignment_manager = DeviceAssignmentManager(request.user)
    devices = assignment_manager.get_device_cheapest_hours(devices)
    current_hour = now_utc.strftime("%Y-%m-%d %H:%M")

    return {
        "prices": prices,
        "devices": devices,
        "selected_device": selected_device,
        "day_transfer_price": day_transfer_price,
        "night_transfer_price": night_transfer_price,
        "hours_needed": hours_needed,
        "current_time": current_hour,
        "title": "Landing Page",
        "year": now_utc.year,
    }

@login_required(login_url='/login/')
def index(request: HttpRequest):
    """Landing page view."""
    return render(request, "app/index.html", get_common_context(request))

@login_required
def about(request: HttpRequest):
    """Renders the about page with device logs."""
    logs = DeviceLog.objects.all() if request.user.is_superuser else DeviceLog.objects.filter(device__user=request.user)
    status_filter = request.GET.get('status', '')
    if status_filter:
        logs = logs.filter(status=status_filter)
    logs = logs.order_by("-created_at")[:100]
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

def contact(request: HttpRequest):
    """Renders the contact page."""
    return render(
        request,
        'app/contact.html',
        {
            'title':'Contact',
            'message':'Your contact page.',
            'year': datetime.now().year,
        }
    )

@staff_member_required
def admin_test_page(request: HttpRequest):
    """Admin test page for triggering backend functionalities."""
    result = None
    assigned_hours = None
    devices = ShellyDevice.objects.all()
    prices = ElectricityPrice.objects.order_by("start_time")[:48]  # Show next 48 hours
    time_format = request.POST.get("time_format", "utc")
    local_tz = pytz.timezone("Europe/Helsinki")
    if request.method == "POST":
        action = request.POST.get("action")
        device_id = request.POST.get("device_id")
        if action == "fetch_prices":
            from .price_views import call_fetch_prices
            response = call_fetch_prices(request)
            if hasattr(response, 'content'):
                result = response.content.decode('utf-8')
            else:
                result = str(response)
        elif action == "get_status" and device_id:
            from .shelly_views import fetch_device_status
            from django.test import RequestFactory
            rf = RequestFactory()
            fake_request = rf.get("/fake", {"device_id": device_id})
            response = fetch_device_status(fake_request)
            if hasattr(response, 'content'):
                result = response.content.decode('utf-8')
            else:
                result = str(response)
            # Show assigned hours for the selected device
            device = devices.filter(device_id=device_id).first()
            if device:
                assignment_manager = DeviceAssignmentManager(device.user)
                hours = assignment_manager.get_device_cheapest_hours([device])[0].cheapest_hours
                if time_format == "local":
                    assigned_hours = [local_tz.localize(datetime.strptime(h, "%H:%M")).astimezone(local_tz).strftime("%H:%M") for h in hours]
                else:
                    assigned_hours = hours
        elif action == "assign_device":
            assign_device_id = request.POST.get("assign_device_id")
            assign_price_id = request.POST.get("assign_price_id")
            device = devices.filter(device_id=assign_device_id).first()
            price = prices.filter(id=assign_price_id).first()
            if device and price:
                assignment, created = DeviceAssignment.objects.get_or_create(
                    user=device.user,  # assign to device owner
                    device=device,
                    electricity_price=price
                )
                if created:
                    result = f"Device {device.familiar_name} assigned to {price.start_time} for user {device.user.username}"
                else:
                    result = f"Device {device.familiar_name} was already assigned to {price.start_time} for user {device.user.username}"
            else:
                result = "Invalid device or price selection."
        elif action == "assign_cheapest_hours":
            cheapest_device_id = request.POST.get("cheapest_device_id")
            device = devices.filter(device_id=cheapest_device_id).first()
            if device:
                assignment_manager = DeviceAssignmentManager(device.user)
                prices_list = list(ElectricityPrice.objects.order_by("start_time").values("start_time", "price_kwh", "id"))
                cheapest_hours = get_cheapest_hours(
                    prices_list,
                    device.day_transfer_price,
                    device.night_transfer_price,
                    device.run_hours_per_day,
                    local_tz
                )
                assigned_count = 0
                for hour in cheapest_hours:
                    price_entry = next((p for p in prices_list if TimeUtils.to_utc(p["start_time"]).strftime("%Y-%m-%d %H:%M") == hour.strftime("%Y-%m-%d %H:%M")), None)
                    if price_entry:
                        assignment, created = DeviceAssignment.objects.get_or_create(
                            user=device.user,  # assign to device owner
                            device=device,
                            electricity_price_id=price_entry["id"]
                        )
                        if created:
                            assigned_count += 1
                result = f"Assigned {assigned_count} cheapest hours to {device.familiar_name} for user {device.user.username} (override 24h check)"
            else:
                result = "Invalid device selection for cheapest hours assignment."
    return render(request, "app/admin_test_page.html", {
        "devices": devices,
        "prices": prices,
        "result": result,
        "assigned_hours": assigned_hours,
    })


