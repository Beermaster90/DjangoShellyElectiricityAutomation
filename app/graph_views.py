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


@login_required(login_url='/login/')
def graphs(request: HttpRequest):
    """Renders the graphs page with cost comparison functionality."""
    
    # Default values
    fixed_price = request.GET.get('fixed_price', '7.0')  # cents per kWh
    watts = request.GET.get('watts', '1500')  # watts
    
    try:
        fixed_price = float(fixed_price)
        watts = int(watts)
    except (ValueError, TypeError):
        fixed_price = 7.0
        watts = 1500
    
    # Get all available historical data (flexible time period)
    # First, check what data we actually have
    earliest_price = ElectricityPrice.objects.order_by('start_time').first()
    latest_price = ElectricityPrice.objects.order_by('-start_time').first()
    
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
        start_time__gte=start_date,
        start_time__lte=end_date
    ).order_by('start_time')
    
    # Calculate costs for both scenarios
    graph_data = calculate_cost_comparison(
        historical_prices, 
        fixed_price, 
        watts, 
        request.user
    )
    
    context = {
        'title': 'Cost Graphs',
        'year': datetime.now().year,
        'fixed_price': fixed_price,
        'watts': watts,
        'graph_data': json.dumps(graph_data),
    }
    
    return render(request, 'app/graphs.html', context)


@login_required
def get_graph_data(request: HttpRequest):
    """AJAX endpoint to get updated graph data."""
    
    fixed_price = request.GET.get('fixed_price', '7.0')
    watts = request.GET.get('watts', '1500')
    
    try:
        fixed_price = float(fixed_price)
        watts = int(watts)
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Invalid input values'}, status=400)
    
    # Get all available historical data (flexible time period)
    # First, check what data we actually have
    earliest_price = ElectricityPrice.objects.order_by('start_time').first()
    latest_price = ElectricityPrice.objects.order_by('-start_time').first()
    
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
        start_time__gte=start_date,
        start_time__lte=end_date
    ).order_by('start_time')
    
    # Calculate costs for both scenarios
    graph_data = calculate_cost_comparison(
        historical_prices, 
        fixed_price, 
        watts, 
        request.user
    )
    
    return JsonResponse({'graph_data': graph_data})


def calculate_cost_comparison(
    historical_prices, 
    fixed_price_cents: float, 
    watts: int, 
    user
) -> Dict[str, Any]:
    """
    Calculate cost comparison between current dynamic pricing and fixed pricing.
    
    Args:
        historical_prices: QuerySet of ElectricityPrice objects
        fixed_price_cents: Fixed price in cents per kWh
        watts: Power consumption in watts
        user: Current user for device assignments
        
    Returns:
        Dictionary containing graph data
    """
    
    # Convert cents to euros and watts to kWh (assuming 1 hour periods)
    fixed_price_euro_per_kwh = Decimal(str(fixed_price_cents / 100))
    kwh_per_hour = Decimal(str(watts / 1000))
    
    # Get user's device assignments to understand when devices were actually running
    if user.is_superuser:
        assignments = DeviceAssignment.objects.select_related('electricity_price').all()
    else:
        assignments = DeviceAssignment.objects.filter(user=user).select_related('electricity_price')
    
    # Create a mapping of price periods to assigned devices
    assigned_periods = set()
    for assignment in assignments:
        assigned_periods.add(assignment.electricity_price.id)
    
    # If no device assignments exist, simulate usage for all periods to show what costs would be
    simulate_full_usage = len(assigned_periods) == 0
    
    # Prepare data for the graph
    labels = []
    dynamic_costs = []
    fixed_costs = []
    dynamic_cumulative = Decimal('0')
    fixed_cumulative = Decimal('0')
    
    for price in historical_prices:
        # Format date for display
        date_label = price.start_time.strftime('%Y-%m-%d %H:%M')
        labels.append(date_label)
        
        # Check if this period had device assignments (actual usage) OR simulate full usage
        if price.id in assigned_periods or simulate_full_usage:
            # Calculate actual dynamic cost for this hour
            dynamic_cost = price.price_kwh * kwh_per_hour
            dynamic_cumulative += dynamic_cost
            
            # Calculate what fixed price would have cost
            fixed_cost = fixed_price_euro_per_kwh * kwh_per_hour
            fixed_cumulative += fixed_cost
        else:
            # No device was running during this period
            dynamic_cost = Decimal('0')
            fixed_cost = Decimal('0')
        
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
        'labels': labels,
        'dynamic_costs': dynamic_costs,
        'fixed_costs': fixed_costs,
        'total_dynamic': total_dynamic,
        'total_fixed': total_fixed,
        'savings': savings,
        'savings_percentage': round(savings_percentage, 2),
        'fixed_price': fixed_price_cents,
        'watts': watts,
        'periods_with_usage': actual_usage_periods if not simulate_full_usage else total_periods,
        'is_simulated': simulate_full_usage,
        'total_periods': total_periods
    }
