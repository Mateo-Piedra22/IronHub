"""
Rate limiting module for authentication endpoints.

Provides thread-safe rate limiting by IP and DNI to prevent brute-force attacks.
"""

import os
import time
import threading
from typing import Dict
from fastapi import Request
from src.rate_limit_store import incr_and_check, get_rate_limit_store, InMemoryRateLimitStore


# --- Thread-safe storage and lock ---
_login_attempts_lock = threading.Lock()
_login_attempts_by_ip: Dict[str, list] = {}
_login_attempts_by_dni: Dict[str, list] = {}


def _get_client_ip(request: Request) -> str:
    """
    Extract client IP address from request, respecting proxy headers when enabled.

    Checks X-Forwarded-For and X-Real-IP headers if PROXY_HEADERS_ENABLED is set.
    Falls back to request.client.host otherwise.
    """
    try:
        trust_proxy = str(os.getenv("PROXY_HEADERS_ENABLED", "0")).strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
        if trust_proxy:
            xff = request.headers.get("x-forwarded-for")
            if xff:
                try:
                    return xff.split(",")[0].strip()
                except Exception:
                    return xff.strip()
            xri = request.headers.get("x-real-ip")
            if xri:
                return xri.strip()
        c = getattr(request, "client", None)
        if c and getattr(c, "host", None):
            return c.host
        return "0.0.0.0"
    except Exception:
        return "0.0.0.0"


def _prune_attempts(store: Dict[str, list], window_s: int) -> None:
    """
    Remove expired attempts from the store (those older than window_s seconds).
    Called internally while holding the lock.
    """
    try:
        now = time.time()
        for k, lst in list(store.items()):
            try:
                store[k] = [t for t in lst if (now - float(t)) <= window_s]
                if not store[k]:
                    store.pop(k, None)
            except Exception:
                store.pop(k, None)
    except Exception:
        pass


def _is_rate_limited(
    key: str, store: Dict[str, list], max_attempts: int, window_s: int
) -> bool:
    """
    Check if the key (IP or DNI) has exceeded max_attempts within window_s seconds.

    Args:
        key: Identifier string (e.g., "ip:192.168.1.1" or "dni:12345678")
        store: The attempts dictionary to check
        max_attempts: Maximum allowed attempts
        window_s: Time window in seconds

    Returns:
        True if rate limited, False otherwise
    """
    with _login_attempts_lock:
        _prune_attempts(store, window_s)
        lst = store.get(key, [])
        try:
            return len(lst) >= int(max_attempts)
        except Exception:
            return len(lst) >= max_attempts


def _register_attempt(key: str, store: Dict[str, list]) -> None:
    """
    Register a login attempt for the given key.
    Limits memory usage by keeping only the last 50 attempts per key.
    """
    try:
        now = time.time()
        with _login_attempts_lock:
            lst = store.get(key)
            if lst is None:
                store[key] = [now]
            else:
                lst.append(now)
                # Limit memory: keep last 50 attempts
                if len(lst) > 50:
                    store[key] = lst[-50:]
    except Exception:
        pass


def _clear_attempts(key: str, store: Dict[str, list]) -> None:
    """
    Clear all attempts for a key (called on successful login).
    """
    try:
        with _login_attempts_lock:
            store.pop(key, None)
    except Exception:
        pass


# --- Convenience functions with default limits ---


def is_ip_rate_limited(
    request: Request, max_attempts: int = 10, window_s: int = 300
) -> bool:
    """Check if the request IP is rate limited (default: 10 attempts per 5 minutes)."""
    ip = _get_client_ip(request)
    key = f"login:ip:{ip}"
    limited, count = incr_and_check(key, window_s, max_attempts)
    try:
        store = get_rate_limit_store()
        if isinstance(store, InMemoryRateLimitStore) and (count % 50 == 0):
            store.cleanup(window_s)
    except Exception:
        pass
    return bool(limited)


def is_dni_rate_limited(dni: str, max_attempts: int = 5, window_s: int = 300) -> bool:
    """Check if the DNI is rate limited (default: 5 attempts per 5 minutes)."""
    key = f"login:dni:{str(dni or '').strip()}"
    limited, count = incr_and_check(key, window_s, max_attempts)
    try:
        store = get_rate_limit_store()
        if isinstance(store, InMemoryRateLimitStore) and (count % 50 == 0):
            store.cleanup(window_s)
    except Exception:
        pass
    return bool(limited)


def register_ip_attempt(request: Request) -> None:
    """Register a login attempt for the request IP."""
    return


def register_dni_attempt(dni: str) -> None:
    """Register a login attempt for the DNI."""
    return


def clear_ip_attempts(request: Request) -> None:
    """Clear all attempts for the request IP (on successful login)."""
    return


def clear_dni_attempts(dni: str) -> None:
    """Clear all attempts for the DNI (on successful login)."""
    return


def is_rate_limited_login(request: Request, dni: str) -> bool:
    """
    Combined rate limit check for login attempts.
    Returns True if EITHER IP or DNI is rate limited.
    """
    ip_limited = is_ip_rate_limited(request)
    dni_limited = is_dni_rate_limited(dni)
    return bool(ip_limited or dni_limited)


def register_login_attempt(request: Request, dni: str) -> None:
    """Register a login attempt for both IP and DNI."""
    return


def clear_login_attempts(request: Request, dni: str) -> None:
    """Clear attempts for both IP and DNI (on successful login)."""
    return


# --- Global API Rate Limiting ---
# These functions provide rate limiting for all API requests, not just login

_api_requests_by_ip: Dict[str, list] = {}

# Configuration via environment variables
try:
    _GLOBAL_RATE_LIMIT_MAX = int(os.getenv("GLOBAL_RATE_LIMIT_MAX", "100"))
except Exception:
    _GLOBAL_RATE_LIMIT_MAX = 100  # Default: 100 requests per window

try:
    _GLOBAL_RATE_LIMIT_WINDOW = int(os.getenv("GLOBAL_RATE_LIMIT_WINDOW", "60"))
except Exception:
    _GLOBAL_RATE_LIMIT_WINDOW = 60  # Default: 60 seconds window

# Stricter limits for write operations
try:
    _WRITE_RATE_LIMIT_MAX = int(os.getenv("WRITE_RATE_LIMIT_MAX", "30"))
except Exception:
    _WRITE_RATE_LIMIT_MAX = 30  # Default: 30 writes per window

try:
    _WRITE_RATE_LIMIT_WINDOW = int(os.getenv("WRITE_RATE_LIMIT_WINDOW", "60"))
except Exception:
    _WRITE_RATE_LIMIT_WINDOW = 60  # Default: 60 seconds window


_write_requests_by_ip: Dict[str, list] = {}


def is_global_rate_limited(request: Request) -> bool:
    """
    Check if the request IP has exceeded the global rate limit for API requests.

    Returns:
        True if rate limited, False otherwise
    """
    ip = _get_client_ip(request)
    tenant = str(request.headers.get("x-tenant") or "").strip().lower()
    key = f"api:{tenant}:{ip}"
    limited, count = incr_and_check(key, _GLOBAL_RATE_LIMIT_WINDOW, _GLOBAL_RATE_LIMIT_MAX)
    try:
        store = get_rate_limit_store()
        if isinstance(store, InMemoryRateLimitStore) and (count % 200 == 0):
            store.cleanup(_GLOBAL_RATE_LIMIT_WINDOW)
    except Exception:
        pass
    return bool(limited)


def is_write_rate_limited(request: Request) -> bool:
    """
    Check if the request IP has exceeded the rate limit for write operations (POST/PUT/DELETE).

    Returns:
        True if rate limited, False otherwise
    """
    ip = _get_client_ip(request)
    tenant = str(request.headers.get("x-tenant") or "").strip().lower()
    key = f"write:{tenant}:{ip}"
    limited, count = incr_and_check(key, _WRITE_RATE_LIMIT_WINDOW, _WRITE_RATE_LIMIT_MAX)
    try:
        store = get_rate_limit_store()
        if isinstance(store, InMemoryRateLimitStore) and (count % 50 == 0):
            store.cleanup(_WRITE_RATE_LIMIT_WINDOW)
    except Exception:
        pass
    return bool(limited)


def register_api_request(request: Request) -> None:
    """Register an API request for the given IP."""
    return


def register_write_request(request: Request) -> None:
    """Register a write operation (POST/PUT/DELETE) for the given IP."""
    return


def get_rate_limit_status(request: Request) -> dict:
    """
    Get the current rate limit status for a request.
    Useful for including in response headers.

    Returns:
        Dict with rate limit information
    """
    ip = _get_client_ip(request)
    tenant = str(request.headers.get("x-tenant") or "").strip().lower()
    return {
        "api_limit": _GLOBAL_RATE_LIMIT_MAX,
        "api_window": _GLOBAL_RATE_LIMIT_WINDOW,
        "write_limit": _WRITE_RATE_LIMIT_MAX,
        "write_window": _WRITE_RATE_LIMIT_WINDOW,
        "ip": ip,
        "tenant": tenant,
    }
