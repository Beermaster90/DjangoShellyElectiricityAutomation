from datetime import datetime
from django.shortcuts import render
from django.http import HttpRequest
from .models import ElectricityPrice  # Import your model

def home(request):
    """Renders the home page."""
    assert isinstance(request, HttpRequest)
    return render(
        request,
        'app/index.html',
        {
            'title':'Home Page',
            'year': datetime.now().year,
        }
    )

def contact(request):
    """Renders the contact page."""
    assert isinstance(request, HttpRequest)
    return render(
        request,
        'app/contact.html',
        {
            'title':'Contact',
            'message':'Your contact page.',
            'year': datetime.now().year,
        }
    )

def about(request):
    """Renders the about page."""
    assert isinstance(request, HttpRequest)
    return render(
        request,
        'app/about.html',
        {
            'title':'About',
            'message':'Your application description page.',
            'year': datetime.now().year,
        }
    )


def home(request):
    # Fetch all prices ordered by start_time (no conversion needed)
    prices = ElectricityPrice.objects.all().order_by('start_time')

    context = {
        'prices': prices,
        'title': 'Landing Page',
        'year': datetime.now().year,
    }
    return render(request, "app/index.html", context)

def index(request):
    # Fetch all prices ordered by start_time (no conversion needed)
    prices = ElectricityPrice.objects.all().order_by('start_time')

    context = {
        'prices': prices,
        'title': 'ShellyApp Index',
        'year': datetime.now().year,
    }
    return render(request, "app/index.html", context)


