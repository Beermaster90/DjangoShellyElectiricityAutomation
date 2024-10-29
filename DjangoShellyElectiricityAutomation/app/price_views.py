from django.http import JsonResponse
from .services.electricity_service import EntsoDataFetcher
from datetime import datetime, timedelta

def call_fetch_prices(request):
    api_key = "a028771e-97fc-4c26-af02-4eaf6f8a7d49"  # Replace with your actual ENTSO-E API key
    start_time = (datetime.utcnow() - timedelta(days=1)).strftime("%Y%m%d%H%M")
    end_time = datetime.utcnow().strftime("%Y%m%d%H%M")
    area_code = "10YFI-1--------U"  # Finland, modify as needed

    electricity_service = EntsoDataFetcher(api_key=api_key)
    prices = electricity_service.fetch_prices(start_time, end_time, area_code)

    return JsonResponse({"prices": prices})


