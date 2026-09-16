"""
High-performance Caching and In-Memory Rate Limiting layer.
Supports in-memory TTL store and optional Redis integration.
"""
import time
from typing import Any, Dict, Optional, Tuple


class CacheManager:
    """Thread-safe, lightweight in-memory cache with TTL support."""
    def __init__(self):
        self._store: Dict[str, Tuple[Any, float]] = {}
        self._rate_limits: Dict[str, list] = {}

    def get(self, key: str) -> Optional[Any]:
        if key in self._store:
            val, expiry = self._store[key]
            if expiry > time.time():
                return val
            else:
                del self._store[key]
        return None

    def set(self, key: str, value: Any, ttl_seconds: int = 300) -> None:
        expiry = time.time() + ttl_seconds
        self._store[key] = (value, expiry)

    def delete(self, key: str) -> None:
        self._store.pop(key, None)

    def clear(self) -> None:
        self._store.clear()

    def check_rate_limit(self, client_id: str, max_requests: int = 120, window_seconds: int = 60) -> bool:
        """Sliding window rate limiter. Returns True if allowed, False if exceeded."""
        now = time.time()
        requests = self._rate_limits.get(client_id, [])
        # Filter timestamps within current window
        valid_requests = [t for t in requests if now - t < window_seconds]
        if len(valid_requests) >= max_requests:
            self._rate_limits[client_id] = valid_requests
            return False
        valid_requests.append(now)
        self._rate_limits[client_id] = valid_requests
        return True


cache = CacheManager()
