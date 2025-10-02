import time
from functools import wraps
from django.db import OperationalError, connection
from django.db.transaction import atomic
from app.logger import log_device_event

def with_db_retries(max_attempts=5, delay=2, backoff_factor=1.5):
    """
    Enhanced decorator that handles SQLite database locks with exponential backoff.
    
    Args:
        max_attempts (int): Maximum number of retry attempts
        delay (int): Initial delay in seconds between retries
        backoff_factor (float): Factor to increase delay between retries
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 1
            current_delay = delay
            last_error = None
            
            while attempt <= max_attempts:
                try:
                    # Close any existing connections
                    connection.close_if_unusable_or_obsolete()
                    
                    # Get a fresh connection
                    connection.connect()
                    
                    # Set higher timeout for SQLite
                    if connection.vendor == 'sqlite':
                        cursor = connection.cursor()
                        cursor.execute('PRAGMA busy_timeout = 30000;')  # 30 second timeout
                    
                    # Execute function within transaction with retry logic
                    with atomic():
                        try:
                            result = func(*args, **kwargs)
                            return result
                        except Exception as e:
                            # Rollback transaction on error
                            if connection.in_atomic_block:
                                connection.set_rollback(True)
                            raise
                            
                except OperationalError as e:
                    last_error = e
                    if "database is locked" in str(e) and attempt < max_attempts:
                        log_device_event(
                            None,
                            f"Database locked, attempt {attempt} of {max_attempts}. "
                            f"Retrying in {current_delay:.1f} seconds...",
                            "WARN"
                        )
                        # Close all connections before retry
                        connection.close()
                        time.sleep(current_delay)
                        # Increase delay for next attempt
                        current_delay *= backoff_factor
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