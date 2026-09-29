import math
import time
from collections import defaultdict, deque


class SlidingWindowRateLimiter:
    def __init__(self, max_requests: int, window_seconds: int):
        self._max_requests = max_requests
        self._window = window_seconds
        self._hits: defaultdict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str) -> int | None:
        now = time.monotonic()
        hits = self._hits[key]

        while hits and hits[0] <= now - self._window:
            hits.popleft()

        if len(hits) >= self._max_requests:
            return max(1, math.ceil(hits[0] + self._window - now))

        hits.append(now)
        return None
