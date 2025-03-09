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
    Save price points to the database, converting from e/MWh to cents/kWh.
    
    period_start_str: e.g. "202503070745" (format: YYYYMMDDHHMM)
    price_points: list of dicts with keys 'position' and 'price' (in e/MWh)
    """
    # Parse the period start time using the provided format
    period_start = datetime.strptime(period_start_str, "%Y%m%d%H%M")
    
    # Conversion factor: 1 €/MWh = 0.1 c/kWh
    conversion_factor = Decimal("0.1")
    
    for point in price_points:
        position = point.get('position')
        try:
            # Convert the price to a Decimal from €/MWh
            price_e_per_mwh = Decimal(str(point.get('price')))
        except InvalidOperation:
            # Skip this price if conversion fails
            continue
        
        # Convert price from €/MWh to c/kWh
        price_c_per_kwh = price_e_per_mwh * conversion_factor
        
        # Calculate the exact hourly interval
        start_time = period_start + timedelta(hours=position - 1)
        end_time = start_time + timedelta(hours=1)
        
        # Update or create the ElectricityPrice record
        ElectricityPrice.objects.update_or_create(
            start_time=start_time,
            end_time=end_time,
            defaults={'price_kwh': price_c_per_kwh}  # Now stored in c/kWh directly
        )

def set_cheapest_hours():

    #Assigns devices to the cheapest hours for the next 24 hours.

    try:

        current_time = now()
        print("Current Time:", current_time)

        start_time = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(days=1)
        last_24_hours = current_time - timedelta(hours=24)

        print("Checking if an assignment exists in the past 24 hours...")
        recent_assignment = ElectricityPrice.objects.filter(last_assigned_at__gte=last_24_hours).exists()
        print("Recent Assignment Exists:", recent_assignment)

        if recent_assignment:
            print("Assignments already exist. Skipping reassignment.")
            log_device_event(None, "Assignments already made in the past 24 hours. Skipping reassignment.", "INFO")
            return

        print("Fetching electricity prices...")
        prices = list(ElectricityPrice.objects.filter(start_time__range=(start_time, end_time))
                      .order_by("start_time")
                      .values("start_time", "price_kwh", "id", "last_assigned_at"))

        print("Found", len(prices), "prices.")

        if not prices:
            print("No electricity prices available. Skipping assignment.")
            log_device_event(None, "No electricity prices available. Skipping assignment.", "WARN")
            return

        device_assignments = {entry['id']: [] for entry in prices}
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
                price_entry = next((p for p in prices if p['start_time'] == hour), None)
                if price_entry:
                    device_assignments[price_entry['id']].append(str(device.device_id))

        # Update database with assigned devices
        for price_id, assigned in device_assignments.items():
            ElectricityPrice.objects.filter(id=price_id).update(
                assigned_devices=",".join(assigned),
                last_assigned_at=current_time
            )

        print("Assignments successfully updated at", current_time)
        log_device_event(None, "Assignments successfully updated at " + str(current_time), "INFO")

    except Exception as e:
        print("Error in assign_cheapest_hours:", e)
        log_device_event(None, "Error in assign_cheapest_hours: " + str(e), "ERROR")


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

