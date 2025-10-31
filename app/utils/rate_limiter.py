import time
from datetime import datetime, timedelta
from typing import Dict, List
import threading

class RateLimiter:
    """
    Advanced rate limiter for Shelly API calls.
    Implements adaptive rate limiting with exponential backoff and request tracking.
    Rate limiting is per server+token combination - different combinations can run in parallel.
    """
    def __init__(self):
        self.last_request: Dict[str, datetime] = {}
        self.failed_requests: Dict[str, int] = {}  # Track consecutive failures
        self.base_delay = 1.1  # Base delay in seconds per server+token combination (1.1s to be safe with 1s API limit)
        self.max_delay = 30.0  # Maximum delay between requests
        self.lock = threading.Lock()

    def _get_server_token_key(self, server_url: str, auth_key: str) -> str:
        """Generate a unique key for server+token combination."""
        # Hash the auth_key for privacy but keep it deterministic
        import hashlib
        key_hash = hashlib.md5(auth_key.encode()).hexdigest()[:8]
        return f"{server_url}:{key_hash}"
    
    def _get_wait_time(self, server_token_key: str, current_time: datetime) -> float:
        """Calculate the time to wait before next request using exponential backoff."""
        if server_token_key not in self.last_request:
            return 0  # No delay for first request to this server+token combination

        elapsed = (current_time - self.last_request[server_token_key]).total_seconds()
        failures = self.failed_requests.get(server_token_key, 0)
        
        # Calculate delay with exponential backoff
        if failures > 0:
            delay = min(self.base_delay * (2 ** failures), self.max_delay)
        else:
            delay = self.base_delay

        if elapsed < delay:
            return delay - elapsed
        return 0

    def wait_if_needed(self, server_url: str, auth_key: str):
        """
        Wait if necessary using adaptive rate limiting per server+token combination.
        Different server+token combinations can run in parallel without waiting.
        Returns the required wait time in seconds.
        """
        with self.lock:
            current_time = datetime.now()
            server_token_key = self._get_server_token_key(server_url, auth_key)
            
            wait_time = self._get_wait_time(server_token_key, current_time)
            
            if wait_time > 0:
                time.sleep(wait_time)
                current_time = datetime.now()
            
            # Update last request time for this server+token combination
            self.last_request[server_token_key] = current_time
                
            return wait_time

    def record_failure(self, server_url: str, auth_key: str):
        """Record a failed request to increase backoff time for this server+token combination."""
        with self.lock:
            server_token_key = self._get_server_token_key(server_url, auth_key)
            self.failed_requests[server_token_key] = self.failed_requests.get(server_token_key, 0) + 1

    def record_success(self, server_url: str, auth_key: str):
        """Record a successful request to reset backoff time for this server+token combination."""
        with self.lock:
            server_token_key = self._get_server_token_key(server_url, auth_key)
            self.failed_requests[server_token_key] = 0

# Global rate limiter instance
shelly_rate_limiter = RateLimiter()  # Enforces 1 request per second per device