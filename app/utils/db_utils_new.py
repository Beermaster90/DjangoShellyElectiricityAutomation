from functools import wraps
from django.db import OperationalError
import time

def with_db_retries(max_attempts=3, delay=1):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            for i in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except OperationalError as e:
                    last_error = e
                    if i < max_attempts - 1:
                        time.sleep(delay)
                    else:
                        raise last_error
            return None
        return wrapper
    return decorator