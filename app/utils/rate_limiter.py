import time
from datetime import datetime, timedelta
from typing import Dict, List
import threading

class RateLimiter:
    """
    Advanced rate limiter for Shelly API calls.
    Implements adaptive rate limiting with exponential backoff and request tracking.
    """
    def __init__(self):
        self.last_request: Dict[str, datetime] = {}
        self.failed_requests: Dict[str, int] = {}  # Track consecutive failures
        self.base_delay = 2.0  # Base delay in seconds
        self.max_delay = 30.0  # Maximum delay between requests
        self.lock = threading.Lock()

    def _get_wait_time(self, device_id: str, current_time: datetime) -> float:
        """Calculate the time to wait before next request using exponential backoff."""
        if device_id not in self.last_request:
            return self.base_delay

        elapsed = (current_time - self.last_request[device_id]).total_seconds()
        failures = self.failed_requests.get(device_id, 0)
        
        # Calculate delay with exponential backoff
        if failures > 0:
            delay = min(self.base_delay * (2 ** failures), self.max_delay)
        else:
            delay = self.base_delay

        if elapsed < delay:
            return delay - elapsed
        return 0

    def wait_if_needed(self, device_id: str):
        """
        Wait if necessary using adaptive rate limiting.
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

    def record_failure(self, device_id: str):
        """Record a failed request to increase backoff time."""
        with self.lock:
            self.failed_requests[device_id] = self.failed_requests.get(device_id, 0) + 1

    def record_success(self, device_id: str):
        """Record a successful request to reset backoff time."""
        with self.lock:
            self.failed_requests[device_id] = 0

# Global rate limiter instance
shelly_rate_limiter = RateLimiter()  # Enforces 1 request per second per device