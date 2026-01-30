import os
import time
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple

from sqlalchemy import text


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class RateLimitStore:
    def incr(self, key: str, window_seconds: int) -> int:
        raise NotImplementedError()


class InMemoryRateLimitStore(RateLimitStore):
    def __init__(self) -> None:
        self._counts: dict[str, tuple[int, float]] = {}

    def incr(self, key: str, window_seconds: int) -> int:
        now = time.time()
        bucket = int(now // max(1, int(window_seconds)))
        k = f"{key}:{bucket}"
        cur = self._counts.get(k)
        if not cur:
            self._counts[k] = (1, now)
            return 1
        c, _ts = cur
        c += 1
        self._counts[k] = (c, now)
        return c

    def cleanup(self, window_seconds: int, keep_windows: int = 3) -> None:
        try:
            now = time.time()
            ws = max(1, int(window_seconds))
            min_bucket = int(now // ws) - int(keep_windows)
            drop = []
            for k in self._counts.keys():
                try:
                    bucket = int(k.rsplit(":", 1)[1])
                    if bucket <= min_bucket:
                        drop.append(k)
                except Exception:
                    continue
            for k in drop:
                self._counts.pop(k, None)
        except Exception:
            return


class PostgresRateLimitStore(RateLimitStore):
    def __init__(self) -> None:
        from src.database.tenant_connection import admin_engine

        self._engine = admin_engine
        self._cleanup_every = 250
        self._op_count = 0

    def _maybe_cleanup(self) -> None:
        self._op_count += 1
        if self._op_count % self._cleanup_every != 0:
            return
        now = _utcnow()
        with self._engine.begin() as conn:
            conn.execute(
                text("DELETE FROM rate_limit_buckets WHERE expires_at < :now"),
                {"now": now},
            )

    def incr(self, key: str, window_seconds: int) -> int:
        now = _utcnow()
        ws = max(1, int(window_seconds))
        bucket = int(now.timestamp() // ws)
        k = f"{key}:{bucket}"
        expires_at = now + timedelta(seconds=ws * 3)
        with self._engine.begin() as conn:
            row = conn.execute(
                text(
                    """
                    INSERT INTO rate_limit_buckets(key, count, expires_at)
                    VALUES (:key, 1, :expires_at)
                    ON CONFLICT (key) DO UPDATE
                      SET count = rate_limit_buckets.count + 1,
                          expires_at = GREATEST(rate_limit_buckets.expires_at, EXCLUDED.expires_at)
                    RETURNING count
                    """
                ),
                {"key": k, "expires_at": expires_at},
            ).fetchone()
        self._maybe_cleanup()
        try:
            return int(row[0] if row else 1)
        except Exception:
            return 1


_store: Optional[RateLimitStore] = None


def get_rate_limit_store() -> RateLimitStore:
    global _store
    if _store is not None:
        return _store
    backend = str(os.getenv("RATE_LIMIT_BACKEND") or "").strip().lower() or "memory"
    if backend in ("pg", "postgres", "postgresql", "db"):
        try:
            _store = PostgresRateLimitStore()
            return _store
        except Exception:
            _store = InMemoryRateLimitStore()
            return _store
    _store = InMemoryRateLimitStore()
    return _store


def incr_and_check(key: str, window_seconds: int, limit: int) -> Tuple[bool, int]:
    ws = max(1, int(window_seconds))
    lim = max(1, int(limit))
    store = get_rate_limit_store()
    count = store.incr(key, ws)
    return (count > lim), count
