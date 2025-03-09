#    api_key = "a028771e-97fc-4c26-af02-4eaf6f8a7d49"  # Replace with your actual ENTSO-E API key
from django.http import JsonResponse
from decimal import Decimal, InvalidOperation
from datetime import datetime, timedelta
from .models import ElectricityPrice, ShellyDevice, DeviceLog
import pandas as pd
from entsoe import EntsoePandasClient
from django.shortcuts import render
from django.utils.timezone import now
from datetime import timedelta

def log_device_event(device, message, status="INFO"):
    """
    Logs events related to a Shelly device or system-wide events.
    """
    DeviceLog.objects.create(device=device if device else None, message=message, status=status)

def call_fetch_prices(request):
    api_key = "a028771e-97fc-4c26-af02-4eaf6f8a7d49"  # Replace with your actual ENTSO-E API key
    area_code = "10YFI-1--------U"  # Finland, modify as needed
    
    # For example, fetch tomorrow's day-ahead prices:
    # Get current UTC time and align it to the current hour
    utc_now = datetime.utcnow()
    aligned_now = datetime(utc_now.year, utc_now.month, utc_now.day, utc_now.hour)
    start = pd.Timestamp(aligned_now, tz='UTC')
    # Set end time to 24 hours later
    end = pd.Timestamp(aligned_now + timedelta(days=1), tz='UTC')
    
    client = EntsoePandasClient(api_key=api_key)
    # Query day‑ahead prices; this returns a Pandas Series with a datetime index
    price_series = client.query_day_ahead_prices(country_code=area_code, start=start, end=end)
    #Note gets price data already in UTC+2 finnish time
    
    # Use the first timestamp as the period start and format it as "YYYYMMDDHHMM"
    period_start = price_series.index[0]
    period_start_str = period_start.strftime("%Y%m%d%H%M")
    
    # Build a list of price points from the series.
    # Each point is a dict with 'position' (1-indexed) and 'price' (in e/MWh)
    price_points = []
    for i, (timestamp, price) in enumerate(price_series.items(), start=1):
        price_points.append({
            'position': i,
            'price': price  # in e/MWh
        })
    
    # Save prices to the database (converted to cents/kWh)
    save_prices_for_period(period_start_str, price_points)
    
    prices_dict = {
        ts.strftime("%Y-%m-%dT%H:%M:%SZ"): price 
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
        start_time = period_start + timedelta(hours=position - 1)
        end_time = start_time + timedelta(hours=1)

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
        print("New prices inserted. Calling set_cheapest_hours()...")
        log_device_event(None, "New electricity prices fetched. Updating cheapest hours.", "INFO")
        set_cheapest_hours()
    else:
        print("No new price data inserted. Skipping cheapest hours update.")
        log_device_event(None, "No new prices detected. Skipping cheapest hour assignment.", "INFO")

def set_cheapest_hours():
    """Assigns devices to the cheapest hours for the next 24 hours."""
    try:
        current_time = datetime.now()
        print("Current Time:", current_time)

        print("Fetching electricity prices...")
        prices = list(ElectricityPrice.objects.filter(start_time__gte=current_time)
                      .order_by("start_time")
                      .values("start_time", "price_kwh", "id", "assigned_devices"))

        print("Found", len(prices), "prices.")

        if not prices:
            print("No electricity prices available. Skipping assignment.")
            log_device_event(None, "No electricity prices available. Skipping assignment.", "WARN")
            return

        device_assignments = {entry["id"]: set(entry["assigned_devices"].split(",")) if entry["assigned_devices"] else set() for entry in prices}
        devices = ShellyDevice.objects.all()

        print("Found", len(devices), "devices.")

        for device in devices:
            print("Processing device:", device.device_id, "(", device.familiar_name, ")")

            cheapest_hours = get_cheapest_hours(
                prices,
                device.day_transfer_price,
                device.night_transfer_price,
                device.run_hours_per_day
            )

            for hour in cheapest_hours:
                price_entry = next((p for p in prices if p["start_time"] == hour), None)
                if price_entry:
                    # Ensure the device is not already assigned to this slot
                    if str(device.device_id) not in device_assignments[price_entry["id"]]:
                        device_assignments[price_entry["id"]].add(str(device.device_id))

        # Update database with assigned devices
        for price_id, assigned in device_assignments.items():
            ElectricityPrice.objects.filter(id=price_id).update(
                assigned_devices=",".join(assigned),
                last_assigned_at=current_time
            )

        print("Assignments successfully updated at", current_time)
        log_device_event(None, "Assignments successfully updated at " + str(current_time), "INFO")

    except Exception as e:
        print("Error in set_cheapest_hours:", e)
        log_device_event(None, "Error in set_cheapest_hours: " + str(e), "ERROR")



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
        hour = entry['start_time'].hour
        if 7 <= hour < 22:  # Daytime hours (7:00-22:00)
            entry['total_price'] = entry['price_kwh'] + day_transfer_price
        else:  # Nighttime hours
            entry['total_price'] = entry['price_kwh'] + night_transfer_price

    # Sort by total price (ascending order)
    sorted_prices = sorted(prices, key=lambda x: x['total_price'])

    # Select **exactly** `hours_needed` hours
    cheapest_slots = [entry['start_time'] for entry in sorted_prices[:hours_needed]]

    return cheapest_slots

