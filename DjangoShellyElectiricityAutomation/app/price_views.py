#    api_key = "a028771e-97fc-4c26-af02-4eaf6f8a7d49"  # Replace with your actual ENTSO-E API key
from django.http import JsonResponse
from decimal import Decimal, InvalidOperation
from datetime import datetime, timedelta, timezone
from .models import ElectricityPrice, ShellyDevice, DeviceLog, DeviceAssignment
import pandas as pd
from entsoe import EntsoePandasClient
from django.shortcuts import render
from django.utils.timezone import now
from datetime import timedelta
from .logger import log_device_event
from .device_assignment_manager import DeviceAssignmentManager  # Import the class
from app.utils.time_utils import TimeUtils



def call_fetch_prices(request):
    api_key = "a028771e-97fc-4c26-af02-4eaf6f8a7d49"  # Replace with your actual ENTSO-E API key
    area_code = "10YFI-1--------U"  # Finland, modify as needed

    # Get current UTC time and align it to the current hour
    now = TimeUtils.now_utc()
    aligned_now = TimeUtils.to_utc(datetime(now.year, now.month, now.day, now.hour))

    future_cutoff = now + timedelta(hours=12)

    future_prices_exist = ElectricityPrice.objects.filter(start_time__gt=future_cutoff).exists()
    if future_prices_exist:
        print(f"Skipping fetch: Prices already exist beyond {future_cutoff}.")
        return JsonResponse({"message": "Prices already up-to-date."}, status=200)

    # Convert to Pandas Timestamp (ensuring UTC consistency)
    start = pd.Timestamp(aligned_now) 
    end = pd.Timestamp(aligned_now + timedelta(days=1))

    client = EntsoePandasClient(api_key=api_key)

    # Query day‑ahead prices (returns a Pandas Series with a datetime index)
    price_series = client.query_day_ahead_prices(country_code=area_code, start=start, end=end)

    # **Ensure price_series is not empty before proceeding**
    if price_series.empty:
        return JsonResponse({"error": "Price series is empty"}, status=400)

    # Get the first timestamp from the price series
    period_start = TimeUtils.to_utc(price_series.index[0]) 

    # Convert `period_start` to string format for database saving
    period_start_str = period_start.strftime("%Y%m%d%H%M")

    # Build a list of price points from the series.
    price_points = [
        {"position": i, "price": price}  # in e/MWh
        for i, (timestamp, price) in enumerate(price_series.items(), start=1)
    ]

    # Save prices to the database (converted to cents/kWh)
    save_prices_for_period(period_start_str, price_points)

    # Convert price timestamps to UTC formatted strings
    prices_dict = {
        TimeUtils.to_utc(ts).strftime("%Y-%m-%dT%H:%M:%SZ"): price
        for ts, price in price_series.items()
    }

    # Return the raw prices as JSON (converted to a dict)
    return JsonResponse({"prices": prices_dict})



def save_prices_for_period(period_start_str, price_points):
    """
    Save price points to the database, converting from €/MWh to cents/kWh.
    
    Only calls `set_cheapest_hours()` if new price entries were added.
    """
    period_start = datetime.strptime(period_start_str, "%Y%m%d%H%M")
    conversion_factor = Decimal("0.1")

    new_entries_added = False  # Track if we add any new entries

    for point in price_points:
        position = point.get('position')
        try:
            price_e_per_mwh = Decimal(str(point.get('price')))
        except InvalidOperation:
            continue  # Skip invalid price entries
        
        price_c_per_kwh = price_e_per_mwh * conversion_factor
        start_time = TimeUtils.to_utc(period_start + timedelta(hours=position - 1))
        end_time = TimeUtils.to_utc(start_time + timedelta(hours=1))

        # Check if this price record already exists
        obj, created = ElectricityPrice.objects.update_or_create(
            start_time=start_time,
            end_time=end_time,
            defaults={'price_kwh': price_c_per_kwh}  # Store as c/kWh
        )

        if created:
            new_entries_added = True  # Mark that we inserted new data

    # **Only call `set_cheapest_hours()` if new prices were added**
    if new_entries_added:
        log_device_event(None, "New electricity prices fetched. Updating cheapest hours.", "INFO")
        if len(price_points) <= 24:  # Ensure more than 24 price points exist
            print(f"Skipping cheapest hour assignment: Only {len(price_points)} prices received, expected more than 24.")
            log_device_event(None, "Incomplete price data received. Skipping cheapest hour assignment.", "WARN")
        else:
            set_cheapest_hours()
    # else:
    #     print("No new price data inserted. Skipping cheapest hours update.")
    #     log_device_event(None, "No new prices detected. Skipping cheapest hour assignment.", "INFO")

def set_cheapest_hours():
    """Assigns devices to the cheapest hours for the next 24 hours."""
    try:
        # Get current UTC time
        current_time = TimeUtils.now_utc()
        print("Current Time:", current_time)

        print("Fetching electricity prices...")
        # Fetch electricity prices starting from the current time
        prices = list(ElectricityPrice.objects.filter(start_time__gte=current_time)
                      .order_by("start_time")
                      .values("start_time", "price_kwh", "id"))

        print("Found", len(prices), "prices.")

        if not prices:
            log_device_event(None, "No electricity prices available. Skipping assignment.", "WARN")
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
                device.run_hours_per_day
            )

            # Create an assignment manager for the device's user
            assignment_manager = DeviceAssignmentManager(device.user)

            for hour in cheapest_hours:
                # Normalize both timestamps to ensure minute-level matching
                price_entry = next(
                    (p for p in prices if TimeUtils.to_utc(p["start_time"]).strftime("%Y-%m-%d %H:%M") ==
                                          TimeUtils.to_utc(hour).strftime("%Y-%m-%d %H:%M")), None
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
                        print(f"Error: `get_assignments_next_24h(device)` returned invalid data for device {device.device_id}")
                        existing_assignment = False

                    if not existing_assignment:
                        assignment_manager.log_assignment(device, ElectricityPrice.objects.get(id=price_entry["id"]))

        print("Assignments successfully updated at", current_time)
        log_device_event(None, f"Assignments successfully updated at {current_time}", "INFO")

    except Exception as e:
        print("Error in set_cheapest_hours:", e)
        log_device_event(None, f"Error in set_cheapest_hours: {str(e)}", "ERROR")


def get_cheapest_hours(prices, day_transfer_price, night_transfer_price, hours_needed):
    """
    Determine the cheapest hours to run a device based on its own electricity prices.

    :param prices: List of dictionaries with 'start_time' and 'price_kwh'
    :param day_transfer_price: Additional price during the day (c/kWh)
    :param night_transfer_price: Additional price during the night (c/kWh)
    :param hours_needed: Number of hours required to run the device per day
    :return: List of cheapest time slots (datetime objects)
    """

    # Ensure prices include total price (electricity + transfer cost)
    for entry in prices:
        entry["start_time"] = TimeUtils.to_utc(entry["start_time"])  # Ensure UTC timezone
        hour = entry["start_time"].hour  # Extract the hour

        if 7 <= hour <= 22:  # Daytime hours (7:00-22:00)
            entry['total_price'] = entry['price_kwh'] + day_transfer_price
        else:  # Nighttime hours
            entry['total_price'] = entry['price_kwh'] + night_transfer_price

    # Sort by total price (ascending order)
    sorted_prices = sorted(prices, key=lambda x: x['total_price'])

    # Select **exactly** `hours_needed` hours
    cheapest_slots = [entry['start_time'] for entry in sorted_prices[:hours_needed]]

    return cheapest_slots
