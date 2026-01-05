"""
Definition of urls for ShellySmartEnergy.
"""

from datetime import datetime
from django.urls import path, include  # Import `include` for app URLs
from django.contrib import admin
from django.contrib.auth.views import LogoutView
from app import forms, views
from app.graph_views import graphs


urlpatterns = [
    path("", views.index, name="home"),  # Changed from views.home to views.index
    path("contact/", views.contact, name="contact"),
    path("about/", views.about, name="about"),
    path("graphs/", graphs, name="graphs"),  # Add graphs page
    path(
        "login/",
        views.CustomLoginView.as_view(
            extra_context={
                "title": "Log in",
                "year": datetime.now().year,
            }
        ),
        name="login",
    ),
    path("logout/", LogoutView.as_view(next_page="/login/"), name="logout"),
    path("admin/", admin.site.urls),
    path(
        "shellyapp/", include("app.urls")
    ),  # Add this line to include app-specific URLs
    path("admin-test/", views.admin_test_page, name="admin_test_page"),
]
