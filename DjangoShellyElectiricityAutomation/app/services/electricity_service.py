# services/entso_data_fetcher.py

import requests
from datetime import datetime, timedelta
from django.utils.timezone import make_aware, get_current_timezone
from ..models import ElectricityPrice
import xml.etree.ElementTree as ET

class EntsoDataFetcher:
    def __init__(self, api_key=None):
        self.api_key = api_key
        self.base_url = "https://web-api.tp.entsoe.eu/api"

    def fetch_prices(self, start_time, end_time, area_code="10YFI-1--------U"):
        """Fetches the electricity prices for a specified time interval."""
        params = {
            "securityToken": self.api_key,
            "documentType": "A44",
            "in_Domain": area_code,
            "out_Domain": area_code,
            "periodStart": start_time,
            "periodEnd": end_time,
        }

        try:
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            return self.parse_prices(response.content)
        except requests.RequestException as e:
            return {"error": str(e)}

    def parse_prices(self, xml_data):
        """Parses the XML response from ENTSO-E to extract prices."""
        prices = []
        try:
            root = ET.fromstring(xml_data)
            ns = {"ns": "urn:iec62325.351:tc57wg16:451-3:publicationdocument:7:3"}
            for point in root.findall(".//ns:Point", ns):
                position = point.find("ns:position", ns).text
                price_amount = point.find("ns:price.amount", ns).text
                prices.append({
                    "position": int(position),
                    "price": float(price_amount),
                })
            return prices
        except ET.ParseError as e:
            return {"error": f"XML Parse Error: {str(e)}"}