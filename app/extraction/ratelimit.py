import threading
import time

import redis

from app.config import get_settings

_KEY = "switchboard:gemini:slot"
_lock = threading.Lock()
_last_call = 0.0


def _local_wait(interval: float) -> None:
    """Per-process fallback when Redis is unreachable (e.g. local runs and tests)."""
    global _last_call
    with _lock:
        delay = _last_call + interval - time.monotonic()
        if delay > 0:
            time.sleep(delay)
        _last_call = time.monotonic()


def wait_for_slot() -> None:
    """Block until the next Gemini call is allowed.

    Calls are spaced evenly (60 / GEMINI_RPM seconds apart) using a Redis key with a TTL,
    so the limit is shared by every worker process and never bursts at minute boundaries.
    """
    rpm = get_settings().gemini_rpm
    if rpm <= 0:
        return
    interval = 60.0 / rpm
    try:
        r = redis.Redis.from_url(get_settings().redis_url, socket_connect_timeout=1)
        while not r.set(_KEY, "1", nx=True, px=int(interval * 1000)):
            time.sleep(max(r.pttl(_KEY), 50) / 1000)
    except redis.RedisError:
        _local_wait(interval)
