from datetime import datetime, UTC
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
        return datetime.now(UTC).replace(tzinfo=TimeUtils.UTC)

    @staticmethod
    def to_utc(dt):
        """Converts a naive or non-UTC aware datetime to UTC."""
        if dt.tzinfo is None:
            return TimeUtils.UTC.localize(dt)
        return dt.astimezone(TimeUtils.UTC)

    @staticmethod
    def get_user_timezone(user):
        """
        Fetches the user's timezone from their profile.
        Falls back to Europe/Helsinki if not found.
        """
        try:
            if user and user.is_authenticated and hasattr(user, "profile"):
                return user.profile.get_timezone()
        except:
            pass
        return TimeUtils.DEFAULT_TZ

    @staticmethod
    def get_user_timezone_name(user):
        """
        Returns the user's timezone name as a string.
        """
        try:
            if user and user.is_authenticated and hasattr(user, "profile"):
                return user.profile.timezone
        except:
            pass
        return "Europe/Helsinki"

    @staticmethod
    def to_user_timezone(dt, user):
        """
        Converts a UTC datetime to the user's preferred timezone.
        If no user timezone is set, defaults to Helsinki.
        """
        if dt.tzinfo is None:
            dt = TimeUtils.UTC.localize(dt)

        user_tz = TimeUtils.get_user_timezone(user)
        return dt.astimezone(user_tz)

    @staticmethod
    def format_datetime(dt, user, fmt="%Y-%m-%d %H:%M"):
        """
        Formats a datetime object into a string in the user's timezone.
        """
        dt = TimeUtils.to_user_timezone(dt, user)
        return dt.strftime(fmt)

    @staticmethod
    def format_datetime_with_tz(dt, user, fmt="%Y-%m-%d %H:%M %Z"):
        """
        Formats a datetime object with timezone info in the user's timezone.
        """
        dt = TimeUtils.to_user_timezone(dt, user)
        return dt.strftime(fmt)

    @staticmethod
    def current_hour_in_user_timezone(user):
        """
        Returns the current hour in the user's timezone as integer.
        """
        now_user_tz = TimeUtils.to_user_timezone(TimeUtils.now_utc(), user)
        return now_user_tz.hour

    @staticmethod
    def datetime_hour_in_user_timezone(dt, user):
        """
        Returns the hour of a datetime in the user's timezone as integer.
        """
        dt_user_tz = TimeUtils.to_user_timezone(dt, user)
        return dt_user_tz.hour

    @staticmethod
    def parse_user_datetime(date_str, user, fmt="%Y-%m-%d %H:%M"):
        """
        Parse a datetime string in user's timezone and convert to UTC.
        """
        user_tz = TimeUtils.get_user_timezone(user)
        naive_dt = datetime.strptime(date_str, fmt)
        localized_dt = user_tz.localize(naive_dt)
        return localized_dt.astimezone(TimeUtils.UTC)
