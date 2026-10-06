"""Tiny in-memory TTL cache.

Designed for low-resource local use. No database or background thread is
required. A future BlackBox integration can replace this with its shared
cache without changing the intelligence API.
"""
import time


class TTLCache:
    def __init__(self, ttl_seconds=300):
        self.ttl_seconds = max(1, int(ttl_seconds))
        self._items = {}


    def get(self, key):
        item = self._items.get(key)
        if not item:
            return None
        if time.monotonic() - item["time"] > self.ttl_seconds:
            self._items.pop(key, None)
            return None
        return item["value"]


    def set(self, key, value):
        self._items[key] = {"time": time.monotonic(), "value": value}


    def clear(self):
        self._items.clear()
