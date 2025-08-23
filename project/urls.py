"""
Definition of urls for DjangoShellyElectiricityAutomation.
"""

from datetime import datetime
from django.urls import path, include  # Import `include` for app URLs
from django.contrib import admin
from django.contrib.auth.views import LoginView, LogoutView
from app import forms, views


urlpatterns = [
    path("", views.index, name="home"),  # Changed from views.home to views.index
    path("contact/", views.contact, name="contact"),
    path("about/", views.about, name="about"),
    path(
        "login/",
        LoginView.as_view(
            template_name="app/login.html",
            authentication_form=forms.BootstrapAuthenticationForm,
            extra_context={
                "title": "Log in",
                "year": datetime.now().year,
            },
        ),
        name="login",
    ),
    path("logout/", LogoutView.as_view(next_page="/"), name="logout"),
    path("admin/", admin.site.urls),
    path(
        "shellyapp/", include("app.urls")
    ),  # Add this line to include app-specific URLs
    path("admin-test/", views.admin_test_page, name="admin_test_page"),
]
