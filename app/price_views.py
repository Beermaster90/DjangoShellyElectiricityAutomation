from django.http import JsonResponse
from decimal import Decimal, InvalidOperation
from datetime import datetime, timedelta, timezone
from .models import (
    ElectricityPrice,
    ShellyDevice,
    DeviceLog,
    DeviceAssignment,
    AppSetting,
)
import pandas as pd
from entsoe import EntsoePandasClient
from django.shortcuts import render
from django.utils.timezone import now
from datetime import timedelta
from .logger import log_device_event
from .device_assignment_manager import DeviceAssignmentManager  # Import the class
from app.utils.time_utils import TimeUtils
from app.utils.security_utils import SecurityUtils
from app.utils.db_utils import with_db_retries
import pytz  # pip install pytz

LOCAL_TZ = pytz.timezone("Europe/Helsinki")  # change if needed


def get_entsoe_api_key():
    setting = AppSetting.objects.filter(key="ENTSOE_API_KEY").first()
    if not setting:
        # Create with default value if not found
        setting = AppSetting.objects.create(key="ENTSOE_API_KEY", value="ABC123")
    return setting.value


def _format_entsoe_series_preview(series, limit=3):
    if series is None:
        return "no series"
    total = len(series)
    if total == 0:
        return "count=0"

    def _format_items(items):
        return {
            TimeUtils.to_utc(ts).strftime("%Y-%m-%dT%H:%M:%SZ"): float(price)
            for ts, price in items
        }

    items = list(series.items())
    preview = {"count": total, "first": _format_items(items[:limit])}
    if total > limit:
        preview["last"] = _format_items(items[-limit:])
    return preview


def call_fetch_prices(request):
    api_key = get_entsoe_api_key()
    if not api_key:
        return JsonResponse(
            {"error": "ENTSO-E API key not set in admin settings."}, status=400
        )
    area_code = "10YFI-1--------U"  # Finland, modify as needed

    # Get current UTC time and align it to the current hour
    now = TimeUtils.now_utc()
    aligned_now = TimeUtils.to_utc(datetime(now.year, now.month, now.day, now.hour))

    future_cutoff = now + timedelta(hours=12)

    future_prices_exist = ElectricityPrice.objects.filter(
        start_time__gt=future_cutoff
    ).exists()
    if future_prices_exist:
        print(f"Skipping fetch: Prices already exist beyond {future_cutoff}.")
        return JsonResponse({"message": "Prices already up-to-date."}, status=200)

    # Convert to Pandas Timestamp (ensuring UTC consistency)
    start = pd.Timestamp(aligned_now)
    end = pd.Timestamp(aligned_now + timedelta(days=1))

    client = EntsoePandasClient(api_key=api_key)

    try:
        log_device_event(
            None,
            f"ENTSOE request: area={area_code}, start={start}, end={end}",
            "INFO",
        )
        # Query day‑ahead prices (returns a Pandas Series with a datetime index)
        price_series = client.query_day_ahead_prices(
            country_code=area_code, start=start, end=end
        )

        log_device_event(
            None,
            f"ENTSOE raw result preview: {_format_entsoe_series_preview(price_series)}",
            "INFO",
        )
        
        # Resample to 15-minute intervals using forward fill (each 15-min gets same price as the hour)
        price_series = price_series.resample('15min').ffill()

        log_device_event(
            None,
            f"ENTSOE resampled preview: {_format_entsoe_series_preview(price_series)}",
            "INFO",
        )
        
    except Exception as e:
        # Sanitize error to hide API key and other sensitive information
        safe_error = SecurityUtils.get_safe_error_message(
            e, "ENTSOE price fetch failed"
        )
        error_type = type(e).__name__
        if safe_error.endswith(":"):
            safe_error = f"{safe_error} {error_type}"
        else:
            safe_error = f"{safe_error} (type={error_type})"
        log_device_event(
            None,
            f"ENTSOE request failed for area={area_code}, start={start}, end={end}",
            "ERROR",
        )
        log_device_event(None, safe_error, "ERROR")
        return JsonResponse(
            {"error": "Failed to fetch electricity prices from ENTSOE"}, status=500
        )

    # **Ensure price_series is not empty before proceeding**
    if price_series.empty:
        return JsonResponse({"error": "Price series is empty"}, status=400)

    # Get the first timestamp from the price series
    period_start = TimeUtils.to_utc(price_series.index[0])

    # Convert `period_start` to string format for database saving
    period_start_str = period_start.strftime("%Y%m%d%H%M")

    # Save prices directly from the resampled series
    conversion_factor = Decimal("0.1")  # Convert from EUR/MWh to cents/kWh
    new_entries_added = False
    
    for timestamp, price in price_series.items():
        start_time = TimeUtils.to_utc(timestamp)
        end_time = TimeUtils.to_utc(timestamp + pd.Timedelta(minutes=15))
        price_c_per_kwh = Decimal(str(price)) * conversion_factor
        
        _, created = ElectricityPrice.objects.update_or_create(
            start_time=start_time,
            end_time=end_time,
            defaults={"price_kwh": price_c_per_kwh},
        )
        if created:
            new_entries_added = True
            
    # Update cheapest hours if new prices were added
    if new_entries_added:
        log_device_event(None, "New electricity prices fetched. Updating cheapest hours.", "INFO")
        set_cheapest_hours()
        
    # Import here to avoid circular import
    from app.tasks import DeviceController
    
    # Always run device control at the hour mark, regardless of new prices
    log_device_event(None, "Running scheduled device control check.", "INFO")
    DeviceController.control_shelly_devices()

    # Convert price timestamps to UTC formatted strings
    prices_dict = {
        TimeUtils.to_utc(ts).strftime("%Y-%m-%dT%H:%M:%SZ"): price
        for ts, price in price_series.items()
    }

    # Return the raw prices as JSON (converted to a dict)
    return JsonResponse({"prices": prices_dict})



@with_db_retries(max_attempts=3, delay=1)
def set_cheapest_hours():
    """Assigns devices to the cheapest hours for the next 24 hours."""
    try:
        # Get current UTC time
        current_time = TimeUtils.now_utc()
        print("Current Time:", current_time)

        print("Fetching electricity prices...")
        # Fetch electricity prices starting from the current time
        prices = list(
            ElectricityPrice.objects.filter(start_time__gte=current_time)
            .order_by("start_time")
            .values("start_time", "price_kwh", "id")
        )

        print("Found", len(prices), "prices.")

        if not prices:
            log_device_event(
                None, "No electricity prices available. Skipping assignment.", "WARN"
            )
            return

        devices = ShellyDevice.objects.all()
        print("Found", len(devices), "devices.")

        for device in devices:
            print(f"Processing device: {device.device_id} ({device.familiar_name})")

            # Get cheapest hours for this device
            cheapest_hours = get_cheapest_hours(
                prices,
                device.day_transfer_price,
                device.night_transfer_price,
                device.run_hours_per_day,
            )

            # Create an assignment manager for the device's user
            assignment_manager = DeviceAssignmentManager(device.user)

            for hour in cheapest_hours:
                # Normalize both timestamps to ensure minute-level matching
                price_entry = next(
                    (
                        p
                        for p in prices
                        if TimeUtils.to_utc(p["start_time"]).strftime("%Y-%m-%d %H:%M")
                        == TimeUtils.to_utc(hour).strftime("%Y-%m-%d %H:%M")
                    ),
                    None,
                )

                if price_entry:
                    # Fetch assignments for the next 24 hours
                    assignments = assignment_manager.get_assignments_next_24h(device)

                    # Ensure assignments is a valid queryset before filtering
                    if assignments is not None and hasattr(assignments, "filter"):
                        existing_assignment = assignments.filter(
                            electricity_price_id=price_entry["id"]
                        ).exists()
                    else:
                        print(
                            f"Error: `get_assignments_next_24h(device)` returned invalid data for device {device.device_id}"
                        )
                        existing_assignment = False

                    if not existing_assignment:
                        assignment_manager.log_assignment(
                            device, ElectricityPrice.objects.get(id=price_entry["id"])
                        )

        print("Assignments successfully updated at", current_time)
        log_device_event(
            None, f"Assignments successfully updated at {current_time}", "INFO"
        )

    except Exception as e:
        # Sanitize error message to hide sensitive information
        safe_error = SecurityUtils.get_safe_error_message(
            e, "Error in set_cheapest_hours"
        )
        print("Error in set_cheapest_hours:", safe_error)
        log_device_event(None, safe_error, "ERROR")


def get_cheapest_hours(
    prices: list[dict],
    day_transfer_price: float,
    night_transfer_price: float,
    hours_needed: int,
    local_tz: timezone = LOCAL_TZ,
):

    day_tp = Decimal(str(day_transfer_price))
    night_tp = Decimal(str(night_transfer_price))

    enriched: list[tuple[Decimal, datetime]] = []

    for entry in prices:
        ts: datetime = entry["start_time"]

        # 1️⃣  Make the timestamp timezone-aware *in local time*
        if ts.tzinfo is None:
            ts = local_tz.localize(ts)
        local_ts = ts.astimezone(local_tz)  # guarantees local clock time

        # 2️⃣  Day or night in *local* clock (7:00-21:59 is day time)
        is_daytime = (7 <= local_ts.hour < 22) or (local_ts.hour == 22 and local_ts.minute == 0)
        transfer = day_tp if is_daytime else night_tp

        # 3️⃣  Total price using Decimal to avoid rounding surprises
        total = Decimal(str(entry["price_kwh"])) + transfer

        enriched.append((total, ts))  # keep original tz for caller

    # 4️⃣  Pick the N cheapest 15-minute periods (hours_needed * 4)
    enriched.sort(key=lambda x: x[0])
    periods_needed = hours_needed * 4  # Convert hours to 15-minute periods
    return [slot for _, slot in enriched[:periods_needed]]
