import threading
import time

import redis

from app.config import get_settings

_lock = threading.Lock()
_last_call: dict[str, float] = {}
_local_exhausted: dict[str, float] = {}  # model -> unix time it resets (Redis-down fallback)


def _redis() -> redis.Redis:
    return redis.Redis.from_url(get_settings().redis_url, socket_connect_timeout=1)


def _local_wait(model: str, interval: float) -> None:
    """Per-process fallback when Redis is unreachable (e.g. local runs and tests)."""
    with _lock:
        delay = _last_call.get(model, 0.0) + interval - time.monotonic()
        if delay > 0:
            time.sleep(delay)
        _last_call[model] = time.monotonic()


def wait_for_slot(model: str) -> None:
    """Block until the next call to `model` is allowed.

    Each model has its own limiter: calls are spaced 60 / GEMINI_RPM seconds apart using a
    Redis key with a TTL, so the limit is shared by every worker and never bursts.
    """
    settings = get_settings()
    rpm = settings.azure_rpm if model.startswith("azure:") else settings.gemini_rpm
    if rpm <= 0:
        return
    interval = 60.0 / rpm
    key = f"switchboard:gemini:slot:{model}"
    try:
        r = _redis()
        while not r.set(key, "1", nx=True, px=int(interval * 1000)):
            time.sleep(max(r.pttl(key), 50) / 1000)
    except redis.RedisError:
        _local_wait(model, interval)


def mark_exhausted(model: str, seconds: float) -> None:
    """Record that `model` has no daily quota left for `seconds`; every worker then skips it."""
    seconds = max(int(seconds), 60)
    _local_exhausted[model] = time.time() + seconds
    try:
        _redis().set(f"switchboard:gemini:exhausted:{model}", "1", ex=seconds)
    except redis.RedisError:
        pass


def exhausted_for(model: str) -> float:
    """Seconds until `model` is usable again (0 if it is available now)."""
    try:
        ttl = _redis().ttl(f"switchboard:gemini:exhausted:{model}")
        if ttl and ttl > 0:
            return float(ttl)
        if ttl == -2:  # key absent in Redis: trust Redis over the local copy
            _local_exhausted.pop(model, None)
            return 0.0
    except redis.RedisError:
        pass
    return max(_local_exhausted.get(model, 0.0) - time.time(), 0.0)
