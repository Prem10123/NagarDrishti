import threading
import time
from collections import defaultdict


class RateLimiter:
    def __init__(self):
        self._lock = threading.Lock()
        self._hits: dict[str, list[float]] = defaultdict(list)

    def allow(self, key: str, limit: int, window_seconds: int) -> bool:
        now = time.time()
        with self._lock:
            times = [stamp for stamp in self._hits[key] if now - stamp < window_seconds]
            if len(times) >= limit:
                self._hits[key] = times
                return False
            times.append(now)
            self._hits[key] = times
            if len(self._hits) > 20_000:
                self._prune(now)
            return True

    def _prune(self, now: float) -> None:
        stale = [key for key, stamps in self._hits.items() if not stamps or now - stamps[-1] > 3600]
        for key in stale[:5000]:
            self._hits.pop(key, None)


limiter = RateLimiter()
