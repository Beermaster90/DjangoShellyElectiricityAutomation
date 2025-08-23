from datetime import datetime
import pytz
from django.utils.timezone import get_current_timezone
from django.conf import settings

class TimeUtils:
    """Utility class for handling timezone conversions in Django."""

    UTC = pytz.utc  # Standard UTC timezone
    DEFAULT_TZ = pytz.timezone("Europe/Helsinki")  # Default if user timezone is unknown

    @staticmethod
    def now_utc():
        """Returns the current time in UTC."""
        return datetime.utcnow().replace(tzinfo=TimeUtils.UTC)

    @staticmethod
    def to_utc(dt):
        """Converts a naive or non-UTC aware datetime to UTC."""
        if dt.tzinfo is None:
            return TimeUtils.UTC.localize(dt)
        return dt.astimezone(TimeUtils.UTC)

    @staticmethod
    def get_user_timezone(request):
        """Fetches the user's timezone from the session, defaults to Helsinki if not found."""
        return request.session.get("user_timezone", "Europe/Helsinki")

    @staticmethod
    def to_user_timezone(dt, request):
        """
        Converts a UTC datetime to the user's local timezone.
        If no user timezone is set, defaults to Helsinki.
        """
        if dt.tzinfo is None:
            dt = TimeUtils.UTC.localize(dt)

        user_tz = TimeUtils.get_user_timezone(request)
        timezone = pytz.timezone(user_tz)
        return dt.astimezone(timezone)

    @staticmethod
    def format_datetime(dt, request, fmt="%Y-%m-%d %H:%M"):
        """
        Formats a datetime object into a string in the user's local timezone.
        """
        dt = TimeUtils.to_user_timezone(dt, request)
        return dt.strftime(fmt)
