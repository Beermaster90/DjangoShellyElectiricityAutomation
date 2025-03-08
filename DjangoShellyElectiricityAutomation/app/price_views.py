#    api_key = "a028771e-97fc-4c26-af02-4eaf6f8a7d49"  # Replace with your actual ENTSO-E API key
from django.http import JsonResponse
from decimal import Decimal, InvalidOperation
from datetime import datetime, timedelta
from .models import ElectricityPrice
import pandas as pd
from entsoe import EntsoePandasClient
from django.shortcuts import render

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
