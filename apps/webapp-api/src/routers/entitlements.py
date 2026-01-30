import logging
from datetime import datetime
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.database.entitlements_schema import ensure_entitlements_schema
from src.dependencies import get_db_session, require_owner

logger = logging.getLogger(__name__)
router = APIRouter()


def _parse_dt(v: Any) -> Optional[datetime]:
    if v is None:
        return None
    try:
        return datetime.fromisoformat(str(v))
    except Exception:
        return None


@router.get("/api/gestion/tipos-cuota/{tipo_cuota_id}/entitlements")
async def api_tipo_cuota_entitlements_get(
    tipo_cuota_id: int,
    _=Depends(require_owner),
    db: Session = Depends(get_db_session),
):
    try:
        ensure_entitlements_schema(db)
        tc = (
            db.execute(
                text(
                    "SELECT id, nombre, all_sucursales FROM tipos_cuota WHERE id = :id LIMIT 1"
                ),
                {"id": int(tipo_cuota_id)},
            )
            .mappings()
            .first()
        )
        if not tc:
            raise HTTPException(status_code=404, detail="Tipo de cuota no encontrado")
        rows = (
            db.execute(
                text(
                    "SELECT sucursal_id FROM tipo_cuota_sucursales WHERE tipo_cuota_id = :id ORDER BY sucursal_id ASC"
                ),
                {"id": int(tipo_cuota_id)},
            )
            .fetchall()
        )
        sucursal_ids: List[int] = []
        for r in rows or []:
            try:
                sucursal_ids.append(int(r[0]))
            except Exception:
                pass
        rules = (
            db.execute(
                text(
                    """
                    SELECT id, sucursal_id, target_type, target_id, allow
                    FROM tipo_cuota_clases_permisos
                    WHERE tipo_cuota_id = :id
                    ORDER BY id ASC
                    """
                ),
                {"id": int(tipo_cuota_id)},
            )
            .mappings()
            .all()
        )
        return {
            "ok": True,
            "tipo_cuota": {
                "id": int(tc.get("id")),
                "nombre": str(tc.get("nombre") or ""),
                "all_sucursales": bool(tc.get("all_sucursales")),
            },
            "sucursal_ids": sucursal_ids,
            "class_rules": [
                {
                    "id": int(r.get("id")),
                    "sucursal_id": int(r.get("sucursal_id"))
                    if r.get("sucursal_id") is not None
                    else None,
                    "target_type": str(r.get("target_type") or ""),
                    "target_id": int(r.get("target_id")),
                    "allow": bool(r.get("allow")),
                }
                for r in (rules or [])
                if r and r.get("id") is not None and r.get("target_id") is not None
            ],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error get tipo_cuota entitlements: {e}")
        return JSONResponse({"ok": False, "error": "server_error"}, status_code=500)


@router.put("/api/gestion/tipos-cuota/{tipo_cuota_id}/entitlements")
async def api_tipo_cuota_entitlements_put(
    tipo_cuota_id: int,
    request: Request,
    _=Depends(require_owner),
    db: Session = Depends(get_db_session),
):
    try:
        ensure_entitlements_schema(db)
        try:
            payload = await request.json()
        except Exception:
            payload = {}
        all_sucursales = bool(payload.get("all_sucursales"))
        sucursal_ids = payload.get("sucursal_ids") or []
        class_rules = payload.get("class_rules") or []
        if not isinstance(sucursal_ids, list):
            sucursal_ids = []
        if not isinstance(class_rules, list):
            class_rules = []

        tc = (
            db.execute(
                text("SELECT id FROM tipos_cuota WHERE id = :id LIMIT 1"),
                {"id": int(tipo_cuota_id)},
            )
            .mappings()
            .first()
        )
        if not tc:
            raise HTTPException(status_code=404, detail="Tipo de cuota no encontrado")

        db.execute(
            text("UPDATE tipos_cuota SET all_sucursales = :v WHERE id = :id"),
            {"id": int(tipo_cuota_id), "v": bool(all_sucursales)},
        )

        db.execute(
            text("DELETE FROM tipo_cuota_sucursales WHERE tipo_cuota_id = :id"),
            {"id": int(tipo_cuota_id)},
        )
        if not all_sucursales:
            for sid in sucursal_ids:
                try:
                    sid_i = int(sid)
                except Exception:
                    continue
                db.execute(
                    text(
                        "INSERT INTO tipo_cuota_sucursales(tipo_cuota_id, sucursal_id) VALUES (:tc, :sid) ON CONFLICT DO NOTHING"
                    ),
                    {"tc": int(tipo_cuota_id), "sid": int(sid_i)},
                )

        db.execute(
            text("DELETE FROM tipo_cuota_clases_permisos WHERE tipo_cuota_id = :id"),
            {"id": int(tipo_cuota_id)},
        )
        for r in class_rules:
            if not isinstance(r, dict):
                continue
            target_type = str(r.get("target_type") or "").strip().lower()
            if target_type not in ("tipo_clase", "clase"):
                continue
            target_id = r.get("target_id")
            try:
                target_id_i = int(target_id)
            except Exception:
                continue
            sucursal_id = r.get("sucursal_id")
            sucursal_id_i = None
            try:
                sucursal_id_i = int(sucursal_id) if sucursal_id is not None else None
            except Exception:
                sucursal_id_i = None
            allow = bool(r.get("allow", True))
            db.execute(
                text(
                    """
                    INSERT INTO tipo_cuota_clases_permisos(tipo_cuota_id, sucursal_id, target_type, target_id, allow)
                    VALUES (:tc, :sid, :tt, :tid, :allow)
                    """
                ),
                {
                    "tc": int(tipo_cuota_id),
                    "sid": sucursal_id_i,
                    "tt": target_type,
                    "tid": int(target_id_i),
                    "allow": bool(allow),
                },
            )

        db.commit()
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        logger.error(f"Error put tipo_cuota entitlements: {e}")
        return JSONResponse({"ok": False, "error": "server_error"}, status_code=500)


@router.get("/api/gestion/usuarios/{usuario_id}/entitlements")
async def api_usuario_entitlements_get(
    usuario_id: int,
    _=Depends(require_owner),
    db: Session = Depends(get_db_session),
):
    try:
        ensure_entitlements_schema(db)
        rows = (
            db.execute(
                text(
                    """
                    SELECT id, sucursal_id, allow, motivo, starts_at, ends_at
                    FROM usuario_accesos_sucursales
                    WHERE usuario_id = :uid
                    ORDER BY id DESC
                    """
                ),
                {"uid": int(usuario_id)},
            )
            .mappings()
            .all()
        )
        branch_overrides = []
        for r in rows or []:
            if not r or r.get("id") is None:
                continue
            branch_overrides.append(
                {
                    "id": int(r.get("id")),
                    "sucursal_id": int(r.get("sucursal_id")),
                    "allow": bool(r.get("allow")),
                    "motivo": str(r.get("motivo") or ""),
                    "starts_at": r.get("starts_at").isoformat()
                    if r.get("starts_at")
                    else None,
                    "ends_at": r.get("ends_at").isoformat() if r.get("ends_at") else None,
                }
            )
        rows = (
            db.execute(
                text(
                    """
                    SELECT id, sucursal_id, target_type, target_id, allow, motivo, starts_at, ends_at
                    FROM usuario_permisos_clases
                    WHERE usuario_id = :uid
                    ORDER BY id DESC
                    """
                ),
                {"uid": int(usuario_id)},
            )
            .mappings()
            .all()
        )
        class_overrides = []
        for r in rows or []:
            if not r or r.get("id") is None:
                continue
            class_overrides.append(
                {
                    "id": int(r.get("id")),
                    "sucursal_id": int(r.get("sucursal_id"))
                    if r.get("sucursal_id") is not None
                    else None,
                    "target_type": str(r.get("target_type") or ""),
                    "target_id": int(r.get("target_id")),
                    "allow": bool(r.get("allow")),
                    "motivo": str(r.get("motivo") or ""),
                    "starts_at": r.get("starts_at").isoformat()
                    if r.get("starts_at")
                    else None,
                    "ends_at": r.get("ends_at").isoformat() if r.get("ends_at") else None,
                }
            )
        return {"ok": True, "branch_overrides": branch_overrides, "class_overrides": class_overrides}
    except Exception as e:
        logger.error(f"Error get usuario entitlements: {e}")
        return JSONResponse({"ok": False, "error": "server_error"}, status_code=500)


@router.put("/api/gestion/usuarios/{usuario_id}/entitlements")
async def api_usuario_entitlements_put(
    usuario_id: int,
    request: Request,
    _=Depends(require_owner),
    db: Session = Depends(get_db_session),
):
    try:
        ensure_entitlements_schema(db)
        try:
            payload = await request.json()
        except Exception:
            payload = {}
        branch_overrides = payload.get("branch_overrides") or []
        class_overrides = payload.get("class_overrides") or []
        if not isinstance(branch_overrides, list):
            branch_overrides = []
        if not isinstance(class_overrides, list):
            class_overrides = []

        db.execute(
            text("DELETE FROM usuario_accesos_sucursales WHERE usuario_id = :uid"),
            {"uid": int(usuario_id)},
        )
        for r in branch_overrides:
            if not isinstance(r, dict):
                continue
            sid = r.get("sucursal_id")
            try:
                sid_i = int(sid)
            except Exception:
                continue
            allow = bool(r.get("allow"))
            motivo = str(r.get("motivo") or "").strip() or None
            starts_at = _parse_dt(r.get("starts_at"))
            ends_at = _parse_dt(r.get("ends_at"))
            db.execute(
                text(
                    """
                    INSERT INTO usuario_accesos_sucursales(usuario_id, sucursal_id, allow, motivo, starts_at, ends_at)
                    VALUES (:uid, :sid, :allow, :motivo, :st, :en)
                    """
                ),
                {
                    "uid": int(usuario_id),
                    "sid": int(sid_i),
                    "allow": bool(allow),
                    "motivo": motivo,
                    "st": starts_at,
                    "en": ends_at,
                },
            )

        db.execute(
            text("DELETE FROM usuario_permisos_clases WHERE usuario_id = :uid"),
            {"uid": int(usuario_id)},
        )
        for r in class_overrides:
            if not isinstance(r, dict):
                continue
            target_type = str(r.get("target_type") or "").strip().lower()
            if target_type not in ("tipo_clase", "clase"):
                continue
            tid = r.get("target_id")
            try:
                tid_i = int(tid)
            except Exception:
                continue
            sucursal_id = r.get("sucursal_id")
            sucursal_id_i = None
            try:
                sucursal_id_i = int(sucursal_id) if sucursal_id is not None else None
            except Exception:
                sucursal_id_i = None
            allow = bool(r.get("allow"))
            motivo = str(r.get("motivo") or "").strip() or None
            starts_at = _parse_dt(r.get("starts_at"))
            ends_at = _parse_dt(r.get("ends_at"))
            db.execute(
                text(
                    """
                    INSERT INTO usuario_permisos_clases(usuario_id, sucursal_id, target_type, target_id, allow, motivo, starts_at, ends_at)
                    VALUES (:uid, :sid, :tt, :tid, :allow, :motivo, :st, :en)
                    """
                ),
                {
                    "uid": int(usuario_id),
                    "sid": sucursal_id_i,
                    "tt": target_type,
                    "tid": int(tid_i),
                    "allow": bool(allow),
                    "motivo": motivo,
                    "st": starts_at,
                    "en": ends_at,
                },
            )

        db.commit()
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        logger.error(f"Error put usuario entitlements: {e}")
        return JSONResponse({"ok": False, "error": "server_error"}, status_code=500)


@router.post("/api/gestion/entitlements/backfill")
async def api_entitlements_backfill(
    request: Request,
    _=Depends(require_owner),
    db: Session = Depends(get_db_session),
):
    try:
        ensure_entitlements_schema(db)
        try:
            payload = await request.json()
        except Exception:
            payload = {}
        create_memberships = bool(payload.get("create_memberships", False))
        db.execute(
            text("UPDATE tipos_cuota SET all_sucursales = TRUE WHERE all_sucursales IS NULL")
        )
        created = 0
        if create_memberships:
            try:
                res = db.execute(
                    text(
                        """
                        INSERT INTO memberships(usuario_id, plan_name, status, start_date, end_date, all_sucursales, created_at, updated_at)
                        SELECT u.id, NULLIF(TRIM(COALESCE(u.tipo_cuota,'')),''), 'active', CURRENT_DATE, u.fecha_proximo_vencimiento::date, TRUE, NOW(), NOW()
                        FROM usuarios u
                        WHERE u.fecha_proximo_vencimiento IS NOT NULL
                          AND LOWER(COALESCE(u.rol,'socio')) NOT IN ('owner','dueño','dueno','admin','administrador','profesor')
                          AND NOT EXISTS (
                              SELECT 1 FROM memberships m WHERE m.usuario_id = u.id AND m.status = 'active'
                          )
                        """
                    )
                )
                try:
                    created = int(getattr(res, "rowcount", 0) or 0)
                except Exception:
                    created = 0
            except Exception:
                created = 0
        db.commit()
        return {"ok": True, "created_memberships": created}
    except HTTPException:
        raise
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        logger.error(f"Error backfill entitlements: {e}")
        return JSONResponse({"ok": False, "error": "server_error"}, status_code=500)
