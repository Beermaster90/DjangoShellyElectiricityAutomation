import time
from functools import wraps
from django.db import OperationalError, connection
from django.db.transaction import atomic
from app.logger import log_device_event

def with_db_retries(max_attempts=3, delay=1):
    """
    Decorator that handles SQLite database locks by retrying operations.
    
    Args:
        max_attempts (int): Maximum number of retry attempts
        delay (int): Delay in seconds between retries
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 1
            while attempt <= max_attempts:
                try:
                    # Ensure connection is usable
                    connection.ensure_connection()
                    
                    # Execute function within transaction
                    with atomic():
                        return func(*args, **kwargs)
                        
                except OperationalError as e:
                    if "database is locked" in str(e) and attempt < max_attempts:
                        log_device_event(
                            None,
                            f"Database locked, attempt {attempt} of {max_attempts}. Retrying in {delay} seconds...",
                            "WARN"
                        )
                        # Close the connection before retry
                        connection.close()
                        time.sleep(delay)
                        attempt += 1
                    else:
                        log_device_event(
                            None,
                            f"Database error after {attempt} attempts: {str(e)}",
                            "ERROR"
                        )
                        raise
                        
                except Exception as e:
                    log_device_event(
                        None,
                        f"Unexpected error in database operation: {str(e)}",
                        "ERROR"
                    )
                    raise
                    
        return wrapper
    return decorator