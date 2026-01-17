import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query
from sqlalchemy import text

from src.database.connection import AdminSessionLocal

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/api/public/gyms")
async def api_public_gyms(limit: int = Query(50, ge=1, le=200)):
    db = AdminSessionLocal()
    try:
        rows = db.execute(
            text(
                """
                SELECT id, nombre, subdominio, status
                FROM gyms
                WHERE status = 'active'
                ORDER BY nombre ASC
                LIMIT :limit
                """
            ),
            {"limit": int(limit)},
        ).fetchall()
        items: List[Dict[str, Any]] = []
        for r in rows:
            items.append(
                {
                    "id": int(r[0]),
                    "nombre": str(r[1] or ""),
                    "subdominio": str(r[2] or ""),
                    "status": str(r[3] or "active"),
                    "logo_url": None,
                }
            )
        return {"items": items, "total": len(items)}
    except Exception as e:
        logger.error(f"Error fetching public gyms: {e}")
        return {"items": [], "total": 0}
    finally:
        try:
            db.close()
        except Exception:
            pass


@router.get("/api/public/metrics")
async def api_public_metrics(ttl_seconds: int = Query(600, ge=60, le=3600)):
    db = AdminSessionLocal()
    try:
        active_gyms = 0
        paying_gyms = 0
        try:
            active_gyms = int(
                (db.execute(text("SELECT COUNT(*) FROM gyms WHERE status = 'active'")).fetchone() or [0])[0] or 0
            )
        except Exception:
            active_gyms = 0

        try:
            paying_gyms = int(
                (
                    db.execute(
                        text(
                            "SELECT COUNT(DISTINCT gym_id) FROM gym_subscriptions WHERE status = 'active' AND next_due_date >= CURRENT_DATE"
                        )
                    ).fetchone()
                    or [0]
                )[0]
                or 0
            )
        except Exception:
            paying_gyms = 0

        return {
            "ok": True,
            "generated_at": None,
            "totals": {
                "active_gyms": active_gyms,
                "paying_gyms": paying_gyms,
                "total_users": None,
                "total_active_users": None,
            },
            "gyms": [],
        }
    except Exception as e:
        logger.error(f"Error fetching public metrics: {e}")
        return {"ok": False, "error": "error_fetching_public_metrics"}
    finally:
        try:
            db.close()
        except Exception:
            pass

