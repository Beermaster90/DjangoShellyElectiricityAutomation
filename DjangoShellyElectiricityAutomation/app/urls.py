# app/urls.py

from django.urls import path
from . import views
from .shelly_views import fetch_device_status,toggle_device_output
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.index, name='index'),  # Index view
    # Remove or use a different view for devices if needed
    # path('devices/', views.device_view, name='device_view'), 

    path('fetch-device-status/', fetch_device_status, name='fetch_device_status'),  # Specific shelly view
    path('toggle-device-ouput/', toggle_device_output, name='toggle_device_output'),  # New route for output control]

]