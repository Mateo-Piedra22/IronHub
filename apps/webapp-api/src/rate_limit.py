"""
Rate limiting module for authentication endpoints.
Ported from legacy Gym Management System server.py (lines 270-337).

Provides thread-safe rate limiting by IP and DNI to prevent brute-force attacks.
"""

import os
import time
import threading
from typing import Dict
from fastapi import Request


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
        trust_proxy = str(os.getenv("PROXY_HEADERS_ENABLED", "0")).strip().lower() in ("1", "true", "yes", "on")
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


def _is_rate_limited(key: str, store: Dict[str, list], max_attempts: int, window_s: int) -> bool:
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

def is_ip_rate_limited(request: Request, max_attempts: int = 10, window_s: int = 300) -> bool:
    """Check if the request IP is rate limited (default: 10 attempts per 5 minutes)."""
    ip = _get_client_ip(request)
    key = f"ip:{ip}"
    return _is_rate_limited(key, _login_attempts_by_ip, max_attempts, window_s)


def is_dni_rate_limited(dni: str, max_attempts: int = 5, window_s: int = 300) -> bool:
    """Check if the DNI is rate limited (default: 5 attempts per 5 minutes)."""
    key = f"dni:{dni}"
    return _is_rate_limited(key, _login_attempts_by_dni, max_attempts, window_s)


def register_ip_attempt(request: Request) -> None:
    """Register a login attempt for the request IP."""
    ip = _get_client_ip(request)
    key = f"ip:{ip}"
    _register_attempt(key, _login_attempts_by_ip)


def register_dni_attempt(dni: str) -> None:
    """Register a login attempt for the DNI."""
    key = f"dni:{dni}"
    _register_attempt(key, _login_attempts_by_dni)


def clear_ip_attempts(request: Request) -> None:
    """Clear all attempts for the request IP (on successful login)."""
    ip = _get_client_ip(request)
    key = f"ip:{ip}"
    _clear_attempts(key, _login_attempts_by_ip)


def clear_dni_attempts(dni: str) -> None:
    """Clear all attempts for the DNI (on successful login)."""
    key = f"dni:{dni}"
    _clear_attempts(key, _login_attempts_by_dni)


def is_rate_limited_login(request: Request, dni: str) -> bool:
    """
    Combined rate limit check for login attempts.
    Returns True if EITHER IP or DNI is rate limited.
    """
    return is_ip_rate_limited(request) or is_dni_rate_limited(dni)


def register_login_attempt(request: Request, dni: str) -> None:
    """Register a login attempt for both IP and DNI."""
    register_ip_attempt(request)
    register_dni_attempt(dni)


def clear_login_attempts(request: Request, dni: str) -> None:
    """Clear attempts for both IP and DNI (on successful login)."""
    clear_ip_attempts(request)
    clear_dni_attempts(dni)
