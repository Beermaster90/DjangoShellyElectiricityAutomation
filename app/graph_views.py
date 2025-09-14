from datetime import datetime, timedelta
from django.shortcuts import render
from django.http import HttpRequest, JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from .models import ElectricityPrice, ShellyDevice, DeviceAssignment
from app.utils.time_utils import TimeUtils
import json
from decimal import Decimal
from typing import List, Dict, Any


@login_required(login_url="/login/")
def graphs(request: HttpRequest):
    """Renders the graphs page with cost comparison functionality."""

    # Default values
    fixed_price = request.GET.get("fixed_price", "7.0")  # cents per kWh
    watts = request.GET.get("watts", "1500")  # watts

    try:
        fixed_price = float(fixed_price)
        watts = int(watts)
    except (ValueError, TypeError):
        fixed_price = 7.0
        watts = 1500

    # Get all available historical data (flexible time period)
    # First, check what data we actually have
    earliest_price = ElectricityPrice.objects.order_by("start_time").first()
    latest_price = ElectricityPrice.objects.order_by("-start_time").first()

    if earliest_price and latest_price:
        # Use actual data range instead of fixed 365 days
        start_date = earliest_price.start_time
        end_date = latest_price.start_time
    else:
        # Fallback to past year if no data
        end_date = TimeUtils.now_utc()
        start_date = end_date - timedelta(days=365)

    # Fetch all available electricity prices
    historical_prices = ElectricityPrice.objects.filter(
        start_time__gte=start_date, start_time__lte=end_date
    ).order_by("start_time")

    # Calculate costs for both scenarios
    graph_data = calculate_cost_comparison(
        historical_prices, fixed_price, watts, request.user
    )

    context = {
        "title": "Cost Graphs",
        "year": datetime.now().year,
        "fixed_price": fixed_price,
        "watts": watts,
        "graph_data": json.dumps(graph_data),
    }

    return render(request, "app/graphs.html", context)


@login_required
def get_graph_data(request: HttpRequest):
    """AJAX endpoint to get updated graph data."""

    fixed_price = request.GET.get("fixed_price", "7.0")
    watts = request.GET.get("watts", "1500")

    try:
        fixed_price = float(fixed_price)
        watts = int(watts)
    except (ValueError, TypeError):
        return JsonResponse({"error": "Invalid input values"}, status=400)

    # Get all available historical data (flexible time period)
    # First, check what data we actually have
    earliest_price = ElectricityPrice.objects.order_by("start_time").first()
    latest_price = ElectricityPrice.objects.order_by("-start_time").first()

    if earliest_price and latest_price:
        # Use actual data range instead of fixed 365 days
        start_date = earliest_price.start_time
        end_date = latest_price.start_time
    else:
        # Fallback to past year if no data
        end_date = TimeUtils.now_utc()
        start_date = end_date - timedelta(days=365)

    # Fetch all available electricity prices
    historical_prices = ElectricityPrice.objects.filter(
        start_time__gte=start_date, start_time__lte=end_date
    ).order_by("start_time")

    # Calculate costs for both scenarios
    graph_data = calculate_cost_comparison(
        historical_prices, fixed_price, watts, request.user
    )

    return JsonResponse({"graph_data": graph_data})


def calculate_cost_comparison(
    historical_prices, fixed_price_cents: float, watts: int, user
) -> Dict[str, Any]:
    """
    Calculate cost comparison between current dynamic pricing and fixed pricing.
    Includes VAT (25.5%) and transfer costs for both scenarios.

    Args:
        historical_prices: QuerySet of ElectricityPrice objects
        fixed_price_cents: Fixed price in cents per kWh (base price, VAT will be added)
        watts: Power consumption in watts
        user: Current user for device assignments

    Returns:
        Dictionary containing graph data with proper cost calculations
    """

    # Constants
    VAT_MULTIPLIER = Decimal("1.255")  # 25.5% VAT
    kwh_per_hour = Decimal(str(watts / 1000))  # Convert watts to kWh

    # Get user's device assignments to understand when devices were actually running
    if user.is_superuser:
        assignments = DeviceAssignment.objects.select_related(
            "electricity_price", "device"
        ).all()
    else:
        assignments = DeviceAssignment.objects.filter(user=user).select_related(
            "electricity_price", "device"
        )

    # Create a mapping of price periods to assigned devices with their transfer costs
    assigned_periods = {}
    for assignment in assignments:
        price_id = assignment.electricity_price.id
        device = assignment.device
        
        # Determine if this is day or night pricing based on hour
        price_start = assignment.electricity_price.start_time
        hour = price_start.hour
        
        # Day: 07:00 - 21:59, Night: 22:00 - 06:59
        if 7 <= hour < 22:
            transfer_cost = device.day_transfer_price
        else:
            transfer_cost = device.night_transfer_price
            
        assigned_periods[price_id] = {
            'device': device,
            'transfer_cost': transfer_cost
        }

    # If no device assignments exist, simulate usage for demonstration
    simulate_full_usage = len(assigned_periods) == 0
    
    # For simulation, use default transfer costs (we'll need a representative device)
    default_day_transfer = Decimal("3.0")  # Default day transfer cost c/kWh
    default_night_transfer = Decimal("1.5")  # Default night transfer cost c/kWh

    # Prepare data for the graph
    labels = []
    dynamic_costs = []
    fixed_costs = []
    dynamic_cumulative = Decimal("0")
    fixed_cumulative = Decimal("0")

    for price in historical_prices:
        # Convert price start time to user timezone for display
        user_tz_time = TimeUtils.to_user_timezone(price.start_time, user)
        date_label = user_tz_time.strftime("%m-%d %H:%M")
        labels.append(date_label)

        # Check if this period had device assignments (actual usage) OR simulate full usage
        if price.id in assigned_periods or simulate_full_usage:
            # Get transfer costs
            if price.id in assigned_periods:
                # Use actual device transfer costs
                transfer_cost = assigned_periods[price.id]['transfer_cost']
            else:
                # Use default transfer costs for simulation
                hour = price.start_time.hour
                transfer_cost = default_day_transfer if 7 <= hour < 22 else default_night_transfer
            
            # Calculate actual dynamic cost for this hour (base price + transfer + VAT)
            base_electricity_price = Decimal(str(price.price_kwh)) / 100  # Convert c/kWh to €/kWh
            transfer_cost_euro = transfer_cost / 100  # Convert c/kWh to €/kWh
            
            # Total cost per kWh before VAT
            total_cost_per_kwh = base_electricity_price + transfer_cost_euro
            
            # Apply VAT and multiply by consumption
            dynamic_cost = total_cost_per_kwh * VAT_MULTIPLIER * kwh_per_hour
            dynamic_cumulative += dynamic_cost

            # Calculate what fixed price would have cost (fixed price + same transfer costs + VAT)
            fixed_base_price = Decimal(str(fixed_price_cents)) / 100  # Convert c/kWh to €/kWh
            fixed_total_per_kwh = fixed_base_price + transfer_cost_euro
            fixed_cost = fixed_total_per_kwh * VAT_MULTIPLIER * kwh_per_hour
            fixed_cumulative += fixed_cost
        else:
            # No device was running during this period
            dynamic_cost = Decimal("0")
            fixed_cost = Decimal("0")

        # Store cumulative costs
        dynamic_costs.append(float(dynamic_cumulative))
        fixed_costs.append(float(fixed_cumulative))

    # Calculate total savings
    total_dynamic = float(dynamic_cumulative)
    total_fixed = float(fixed_cumulative)
    savings = total_fixed - total_dynamic
    savings_percentage = (savings / total_fixed * 100) if total_fixed > 0 else 0

    # Count actual usage periods vs simulated
    actual_usage_periods = len(assigned_periods) if not simulate_full_usage else 0
    total_periods = len(historical_prices)

    return {
        "labels": labels,
        "dynamic_costs": dynamic_costs,
        "fixed_costs": fixed_costs,
        "total_dynamic": total_dynamic,
        "total_fixed": total_fixed,
        "savings": savings,
        "savings_percentage": round(savings_percentage, 2),
        "fixed_price": fixed_price_cents,
        "watts": watts,
        "periods_with_usage": (
            actual_usage_periods if not simulate_full_usage else total_periods
        ),
        "is_simulated": simulate_full_usage,
        "total_periods": total_periods,
    }
