# app/urls.py

from django.urls import path
from . import views
from .shelly_views import fetch_device_status,toggle_device_output
from .price_views import call_fetch_prices
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.index, name='index'),  # /shellyapp/ calls index()

    # path('fetch-device-status/', fetch_device_status, name='fetch_device_status'),  # Specific shelly view
    # path('toggle-device-output/', toggle_device_output, name='toggle_device_output'),  # page to toggle shelly device output on / off]
    # path('fetch-prices/', call_fetch_prices, name='fetch_prices'),  # fetch electricity prices
]