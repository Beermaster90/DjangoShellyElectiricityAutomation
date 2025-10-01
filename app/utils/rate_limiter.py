import time
from datetime import datetime, timedelta
from typing import Dict, List
import threading

class RateLimiter:
    """
    Rate limiter for Shelly API calls.
    Implements a strict 1 request per second limit per device.
    """
    def __init__(self):
        self.last_request: Dict[str, datetime] = {}
        self.lock = threading.Lock()

    def _get_wait_time(self, device_id: str, current_time: datetime) -> float:
        """Calculate the time to wait before next request."""
        if device_id not in self.last_request:
            return 2.0  # Initial delay
            
        elapsed = (current_time - self.last_request[device_id]).total_seconds()
        if elapsed < 2.0:  # Increased minimum time between requests
            return 2.0 - elapsed
        return 0

    def wait_if_needed(self, device_id: str):
        """
        Wait if necessary to comply with the 1 request per second limit.
        Returns the required wait time in seconds.
        """
        with self.lock:
            current_time = datetime.now()
            wait_time = self._get_wait_time(device_id, current_time)
            
            if wait_time > 0:
                time.sleep(wait_time)
                current_time = datetime.now()
            
            # Update last request time
            self.last_request[device_id] = current_time
            return wait_time

# Global rate limiter instance
shelly_rate_limiter = RateLimiter()  # Enforces 1 request per second per device