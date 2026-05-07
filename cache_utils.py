# cache_utils.py
import time
from typing import Any, Dict, Tuple


class TTLCache:
    """
    Very simple in-memory cache with TTL (seconds).

    Usage:
        cache = TTLCache(ttl_seconds=600)
        cache.set(value, "key-part-1", "key-part-2")
        result = cache.get("key-part-1", "key-part-2")
    """

    def __init__(self, ttl_seconds: int = 600):
        self.ttl = ttl_seconds
        self._data: Dict[Tuple[Any, ...], Tuple[float, Any]] = {}

    def _make_key(self, *parts: Any) -> Tuple[Any, ...]:
        return tuple(parts)

    def get(self, *parts: Any) -> Any:
        key = self._make_key(*parts)
        entry = self._data.get(key)
        if not entry:
            return None
        expires_at, value = entry
        now = time.time()
        if now > expires_at:
            # expired: delete and miss
            self._data.pop(key, None)
            return None
        return value

    def set(self, value: Any, *parts: Any) -> None:
        key = self._make_key(*parts)
        expires_at = time.time() + self.ttl
        self._data[key] = (expires_at, value)
