"""
ESAJ fallback service with response caching.

Provides graceful degradation when ESAJ API is unavailable,
using cached responses to continue operation.
"""

import time
from typing import Any, Dict, Optional
from datetime import datetime


class FallbackService:
    """
    Fallback service for ESAJ API with response caching.

    When the API is unavailable (circuit breaker open), returns cached
    responses to allow graceful degradation of service.
    """

    def __init__(self, cache_ttl_seconds: int = 3600):
        """
        Initialize fallback service.

        Args:
            cache_ttl_seconds: Time-to-live for cached responses (default: 1 hour)
        """
        self.cache_ttl_seconds = cache_ttl_seconds
        self._cache: Dict[str, Dict[str, Any]] = {}

    def cache_response(self, key: str, response: Dict[str, Any]) -> None:
        """
        Cache an API response.

        Args:
            key: Cache key (usually CNJ number)
            response: Response data to cache
        """
        self._cache[key] = {
            "data": response,
            "timestamp": time.time(),
            "expires_at": time.time() + self.cache_ttl_seconds,
        }

    def get_cached_response(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached response if available and not expired.

        Args:
            key: Cache key (usually CNJ number)

        Returns:
            Cached response data or None if not found/expired
        """
        if key not in self._cache:
            return None

        entry = self._cache[key]
        if time.time() > entry["expires_at"]:
            # Expired, remove and return None
            del self._cache[key]
            return None

        return entry["data"]

    def get_fallback_response(self, key: str) -> Dict[str, Any]:
        """
        Get fallback response when service is unavailable.

        Returns cached response if available, otherwise returns
        generic unavailable message.

        Args:
            key: Cache key (usually CNJ number)

        Returns:
            Cached response or unavailable message
        """
        cached = self.get_cached_response(key)

        if cached is not None:
            # Return cached response with stale indicator
            return {
                **cached,
                "_cached": True,
                "_stale": True,
                "_cache_note": "This is cached data. The ESAJ service may be unavailable.",
            }

        # No cached response available
        return {
            "status": "service_unavailable",
            "message": "ESAJ service is temporarily unavailable. No cached data found.",
            "timestamp": datetime.utcnow().isoformat(),
            "_fallback": True,
        }

    def clear_cache(self) -> None:
        """Clear all cached responses."""
        self._cache.clear()

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache metrics
        """
        # Remove expired entries before reporting
        current_time = time.time()
        valid_keys = [
            k for k, v in self._cache.items() if current_time <= v["expires_at"]
        ]

        return {
            "cached_items": len(valid_keys),
            "keys": valid_keys,
            "total_capacity": len(self._cache),
            "ttl_seconds": self.cache_ttl_seconds,
        }

    def get_stale_entries(self) -> Dict[str, Any]:
        """
        Get all stale (expired) cache entries.

        Returns:
            Dictionary of expired cache entries
        """
        current_time = time.time()
        stale = {}

        for key, entry in self._cache.items():
            if current_time > entry["expires_at"]:
                stale[key] = {
                    "data": entry["data"],
                    "expired_at": datetime.fromtimestamp(
                        entry["expires_at"]
                    ).isoformat(),
                }

        return stale
