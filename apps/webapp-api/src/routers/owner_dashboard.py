from __future__ import annotations

import csv
import io
import logging
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from src.database.clase_profesor_schema import ensure_clase_profesor_schema
from src.dependencies import (
    get_db_session,
    get_staff_service,
    get_reports_service,
    get_whatsapp_service,
    get_whatsapp_settings_service,
    require_owner,
)
from src.models.orm_models import (
    Asistencia,
    Clase,
    ClaseHorario,
    Pago,
    Profesor,
    ProfesorClaseAsignacion,
    Sucursal,
    Usuario,
)
from src.services.reports_service import ReportsService
from src.services.staff_service import StaffService
from src.services.whatsapp_service import WhatsAppService
from src.services.whatsapp_settings_service import WhatsAppSettingsService

logger = logging.getLogger(__name__)

router = APIRouter(
    dependencies=[
        Depends(require_owner),
    ]
)


def _to_csv_response(data: list, filename: str):
    if not data:
        output = io.StringIO()
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(data[0].keys()))
    writer.writeheader()
    writer.writerows(data)
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


def _get_optional_sucursal_id(request: Request, db: Session) -> Optional[int]:
    try:
        sid_raw = request.session.get("sucursal_id")
    except Exception:
        sid_raw = None
    try:
        sid = int(sid_raw) if sid_raw is not None else None
    except Exception:
        sid = None
    if sid is None or sid <= 0:
        return None
    try:
        ok = (
            db.execute(
                text("SELECT 1 FROM sucursales WHERE id = :id AND activa = TRUE LIMIT 1"),
                {"id": int(sid)},
            ).fetchone()
            is not None
        )
        if ok:
            return int(sid)
    except Exception:
        pass
    try:
        request.session.pop("sucursal_id", None)
    except Exception:
        pass
    return None


def _get_sucursal_nombre(db: Session, sucursal_id: Optional[int]) -> Optional[str]:
    if sucursal_id is None:
        return None
    try:
        row = (
            db.execute(
                text("SELECT nombre FROM sucursales WHERE id = :id LIMIT 1"),
                {"id": int(sucursal_id)},
            )
            .mappings()
            .first()
        )
        if row and row.get("nombre") is not None:
            return str(row.get("nombre") or "")
    except Exception:
        return None
    return None


def _safe(fn, default):
    try:
        return fn()
    except Exception as e:
        try:
            logger.error(f"Owner dashboard section failed: {e}")
        except Exception:
            pass
        return default


@router.get("/api/owner_dashboard/overview")
async def api_owner_dashboard_overview(
    request: Request,
    db: Session = Depends(get_db_session),
    reports: ReportsService = Depends(get_reports_service),
    wa_settings: WhatsAppSettingsService = Depends(get_whatsapp_settings_service),
    wa_svc: WhatsAppService = Depends(get_whatsapp_service),
):
    sid = _get_optional_sucursal_id(request, db)
    scope = {
        "mode": "sucursal" if sid is not None else "general",
        "sucursal_id": sid,
        "sucursal_nombre": _get_sucursal_nombre(db, sid),
    }

    kpis = _safe(lambda: reports.obtener_kpis(sucursal_id=sid), {})
    kpis_adv = _safe(lambda: reports.obtener_kpis_avanzados(sucursal_id=sid), {})
    activos_inactivos = _safe(lambda: reports.obtener_activos_inactivos(sucursal_id=sid), {})
    ingresos12m = _safe(lambda: reports.obtener_ingresos_12m(sucursal_id=sid), [])
    nuevos12m = _safe(lambda: reports.obtener_nuevos_12m(sucursal_id=sid), [])
    arpu12m = _safe(lambda: reports.obtener_arpu_12m(sucursal_id=sid), [])
    arpa_por_tipo = _safe(lambda: reports.obtener_arpa_por_tipo(sucursal_id=sid), [])
    payment_status = _safe(lambda: reports.obtener_estado_pagos(sucursal_id=sid), {})
    cohorts_6m = _safe(lambda: reports.obtener_cohort_6m(sucursal_id=sid), [])
    waitlist_events = _safe(lambda: reports.obtener_eventos_espera(sucursal_id=sid), [])
    delinquency_alerts = _safe(lambda: reports.obtener_alertas_morosidad(sucursal_id=sid), [])
    wa_stats = _safe(lambda: wa_settings.get_stats(sucursal_id=sid), {})
    wa_pendientes = _safe(lambda: wa_svc.obtener_resumen_mensajes(30, 200, sucursal_id=sid), [])
    attendance_audit_7d = _safe(
        lambda: reports.obtener_auditoria_asistencias(dias=7, sucursal_id=sid),
        {"ok": False},
    )

    return {
        "ok": True,
        "scope": scope,
        "kpis": kpis,
        "kpis_avanzados": kpis_adv,
        "activos_inactivos": activos_inactivos,
        "ingresos12m": {"data": ingresos12m},
        "nuevos12m": {"data": nuevos12m},
        "arpu12m": {"data": arpu12m},
        "arpa_por_tipo_cuota": {"data": arpa_por_tipo},
        "payment_status_dist": payment_status,
        "cohort_retencion_6m": {"cohorts": cohorts_6m},
        "waitlist_events": {"events": waitlist_events},
        "delinquency_alerts_recent": {"alerts": delinquency_alerts},
        "whatsapp_stats": wa_stats,
        "whatsapp_pendientes": {"mensajes": wa_pendientes},
        "attendance_audit_7d": attendance_audit_7d if attendance_audit_7d.get("ok") else None,
    }


@router.get("/api/owner_dashboard/attendance_audit")
async def api_owner_dashboard_attendance_audit(
    request: Request,
    db: Session = Depends(get_db_session),
    svc: ReportsService = Depends(get_reports_service),
    dias: int = Query(35, ge=1, le=366),
    desde: Optional[str] = Query(None),
    hasta: Optional[str] = Query(None),
    umbral_multiples: int = Query(3, ge=2, le=50),
    umbral_repeticion_minutos: int = Query(5, ge=1, le=60),
):
    sid = _get_optional_sucursal_id(request, db)
    d = None
    h = None
    try:
        d = date.fromisoformat(desde) if desde else None
    except Exception:
        d = None
    try:
        h = date.fromisoformat(hasta) if hasta else None
    except Exception:
        h = None
    return svc.obtener_auditoria_asistencias(
        desde=d,
        hasta=h,
        dias=int(dias),
        umbral_multiples=int(umbral_multiples),
        umbral_repeticion_minutos=int(umbral_repeticion_minutos),
        sucursal_id=sid,
    )


@router.get("/api/owner_dashboard/usuarios")
async def api_owner_dashboard_usuarios(
    request: Request,
    db: Session = Depends(get_db_session),
    search: str = "",
    activo: Optional[bool] = None,
    page: int = 1,
    limit: int = 20,
):
    sid = _get_optional_sucursal_id(request, db)
    page_i = max(1, int(page or 1))
    limit_i = max(1, min(int(limit or 20), 200))
    offset_i = (page_i - 1) * limit_i

    term = str(search or "").strip()
    where_parts: List[str] = []
    params: Dict[str, Any] = {"limit": int(limit_i), "offset": int(offset_i)}

    if term:
        where_parts.append("(u.nombre ILIKE :q OR u.dni ILIKE :q OR u.telefono ILIKE :q)")
        params["q"] = f"%{term}%"
    if activo is not None:
        where_parts.append("u.activo = :activo")
        params["activo"] = bool(activo)
    if sid is not None:
        params["sid"] = int(sid)
        where_parts.append(
            """
            COALESCE((
                SELECT uas.allow
                FROM usuario_accesos_sucursales uas
                WHERE uas.usuario_id = u.id
                  AND uas.sucursal_id = :sid
                  AND (uas.starts_at IS NULL OR uas.starts_at <= NOW())
                  AND (uas.ends_at IS NULL OR uas.ends_at >= NOW())
                ORDER BY uas.id DESC
                LIMIT 1
            ), (
                COALESCE(tc.all_sucursales, FALSE)
                OR EXISTS (
                    SELECT 1
                    FROM tipo_cuota_sucursales tcs
                    WHERE tcs.tipo_cuota_id = tc.id
                      AND tcs.sucursal_id = :sid
                )
            )) = TRUE
            """
        )

    where_sql = " AND ".join([p.strip() for p in where_parts if p and p.strip()])
    where_sql = where_sql.strip()
    if where_sql:
        where_sql = "WHERE " + where_sql

    total = (
        db.execute(
            text(
                f"""
                SELECT COUNT(*) AS total
                FROM usuarios u
                LEFT JOIN tipos_cuota tc ON LOWER(tc.nombre) = LOWER(u.tipo_cuota)
                {where_sql}
                """
            ),
            params,
        )
        .scalar()
        or 0
    )

    rows = (
        db.execute(
            text(
                f"""
                SELECT
                  u.id,
                  u.nombre,
                  u.dni,
                  u.telefono,
                  u.activo,
                  u.rol,
                  u.tipo_cuota,
                  u.fecha_registro,
                  u.fecha_proximo_vencimiento,
                  u.cuotas_vencidas,
                  u.ultimo_pago,
                  u.notas,
                  u.sucursal_registro_id,
                  s.nombre AS sucursal_registro_nombre
                FROM usuarios u
                LEFT JOIN tipos_cuota tc ON LOWER(tc.nombre) = LOWER(u.tipo_cuota)
                LEFT JOIN sucursales s ON s.id = u.sucursal_registro_id
                {where_sql}
                ORDER BY u.nombre ASC
                LIMIT :limit OFFSET :offset
                """
            ),
            params,
        )
        .mappings()
        .all()
    )

    usuarios = [
        {
            "id": int(r.get("id") or 0),
            "nombre": str(r.get("nombre") or ""),
            "dni": r.get("dni"),
            "telefono": r.get("telefono"),
            "email": "",
            "activo": bool(r.get("activo")) if r.get("activo") is not None else False,
            "rol": str(r.get("rol") or "").strip().lower(),
            "tipo_cuota_id": None,
            "tipo_cuota_nombre": r.get("tipo_cuota"),
            "fecha_registro": r.get("fecha_registro"),
            "fecha_proximo_vencimiento": r.get("fecha_proximo_vencimiento"),
            "cuotas_vencidas": r.get("cuotas_vencidas"),
            "ultimo_pago": r.get("ultimo_pago"),
            "notas": r.get("notas"),
            "sucursal_registro_id": r.get("sucursal_registro_id"),
            "sucursal_registro_nombre": r.get("sucursal_registro_nombre"),
        }
        for r in (rows or [])
        if r and r.get("id") is not None
    ]

    return {
        "ok": True,
        "usuarios": usuarios,
        "total": int(total or 0),
        "limit": int(limit_i),
        "offset": int(offset_i),
    }


@router.get("/api/owner_dashboard/staff")
async def api_owner_dashboard_staff(
    request: Request,
    db: Session = Depends(get_db_session),
    svc: StaffService = Depends(get_staff_service),
    search: str = "",
):
    sid = _get_optional_sucursal_id(request, db)
    items = svc.list_staff(search=search, sucursal_id=sid, show_all=(sid is None))
    sucursal_ids: List[int] = []
    for it in items or []:
        for x in (it or {}).get("sucursales") or []:
            try:
                sucursal_ids.append(int(x))
            except Exception:
                pass
    uniq = sorted({i for i in sucursal_ids if i > 0})
    names: Dict[int, str] = {}
    if uniq:
        rows = (
            db.execute(
                text(
                    "SELECT id, nombre FROM sucursales WHERE id = ANY(:ids) ORDER BY id ASC"
                ),
                {"ids": uniq},
            )
            .mappings()
            .all()
        )
        for r in rows or []:
            try:
                names[int(r.get("id"))] = str(r.get("nombre") or "")
            except Exception:
                pass
    for it in items or []:
        ids = []
        for x in (it or {}).get("sucursales") or []:
            try:
                ids.append(int(x))
            except Exception:
                pass
        (it or {})["sucursales_info"] = [
            {"id": i, "nombre": names.get(i) or ""}
            for i in sorted({i for i in ids if i > 0})
        ]
    return {"ok": True, "items": items}


@router.get("/api/owner_dashboard/profesores")
async def api_owner_dashboard_profesores(
    request: Request,
    db: Session = Depends(get_db_session),
    search: str = "",
):
    ensure_clase_profesor_schema(db)
    sid = _get_optional_sucursal_id(request, db)
    term = str(search or "").strip()
    q = f"%{term}%" if term else None
    rows = (
        db.execute(
            text(
                """
                SELECT
                  p.id AS profesor_id,
                  p.usuario_id,
                  u.nombre,
                  u.dni,
                  u.telefono,
                  p.tipo,
                  p.estado,
                  ARRAY_REMOVE(ARRAY_AGG(DISTINCT suc.sid), NULL) AS sucursal_ids
                FROM profesores p
                JOIN usuarios u ON u.id = p.usuario_id
                LEFT JOIN (
                    SELECT p.id AS profesor_id, us.sucursal_id AS sid
                    FROM profesores p
                    LEFT JOIN usuario_sucursales us ON us.usuario_id = p.usuario_id
                    UNION
                    SELECT a.profesor_id AS profesor_id, c.sucursal_id AS sid
                    FROM profesor_clase_asignaciones a
                    JOIN clases_horarios ch ON ch.id = a.clase_horario_id
                    JOIN clases c ON c.id = ch.clase_id
                    WHERE a.activa = TRUE
                    UNION
                    SELECT a.profesor_id AS profesor_id, c.sucursal_id AS sid
                    FROM clase_profesor_asignaciones a
                    JOIN clases c ON c.id = a.clase_id
                    WHERE a.activa = TRUE
                ) suc ON suc.profesor_id = p.id
                WHERE (:sid IS NULL OR suc.sid = :sid)
                  AND (
                    :q IS NULL OR u.nombre ILIKE :q OR u.dni ILIKE :q OR u.telefono ILIKE :q
                  )
                GROUP BY p.id, p.usuario_id, u.nombre, u.dni, u.telefono, p.tipo, p.estado
                ORDER BY u.nombre ASC
                """
            ),
            {"sid": int(sid) if sid is not None else None, "q": q},
        )
        .mappings()
        .all()
    )
    items: List[Dict[str, Any]] = []
    sucursal_ids: List[int] = []
    for r in rows or []:
        for x in r.get("sucursal_ids") or []:
            try:
                sucursal_ids.append(int(x))
            except Exception:
                pass
    uniq = sorted({i for i in sucursal_ids if i > 0})
    names: Dict[int, str] = {}
    if uniq:
        ns = (
            db.execute(
                text(
                    "SELECT id, nombre FROM sucursales WHERE id = ANY(:ids) ORDER BY id ASC"
                ),
                {"ids": uniq},
            )
            .mappings()
            .all()
        )
        for r in ns or []:
            try:
                names[int(r.get("id"))] = str(r.get("nombre") or "")
            except Exception:
                pass
    for r in rows or []:
        ids = r.get("sucursal_ids") or []
        pairs = []
        for i in ids or []:
            try:
                iid = int(i)
                if iid > 0:
                    pairs.append({"id": iid, "nombre": names.get(iid) or ""})
            except Exception:
                pass
        items.append(
            {
                "id": r.get("profesor_id"),
                "usuario_id": r.get("usuario_id"),
                "nombre": r.get("nombre"),
                "dni": r.get("dni"),
                "telefono": r.get("telefono"),
                "tipo": r.get("tipo"),
                "estado": r.get("estado"),
                "sucursales": sorted(pairs, key=lambda x: int(x.get("id") or 0)),
            }
        )
    return {"ok": True, "items": items}


@router.get("/api/owner_dashboard/pagos")
async def api_owner_dashboard_pagos(
    request: Request,
    db: Session = Depends(get_db_session),
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    metodo_id: Optional[int] = None,
    page: int = 1,
    limit: int = 20,
):
    sid = _get_optional_sucursal_id(request, db)
    page_i = max(1, int(page or 1))
    limit_i = max(1, min(int(limit or 20), 200))
    offset_i = (page_i - 1) * limit_i

    d = None
    h = None
    try:
        d = date.fromisoformat(str(desde)) if desde else None
    except Exception:
        d = None
    try:
        h = date.fromisoformat(str(hasta)) if hasta else None
    except Exception:
        h = None

    stmt = (
        select(
            Pago,
            Usuario.nombre.label("usuario_nombre"),
            Sucursal.nombre.label("sucursal_nombre"),
        )
        .join(Usuario, Pago.usuario_id == Usuario.id)
        .outerjoin(Sucursal, Pago.sucursal_id == Sucursal.id)
    )

    if d is not None:
        stmt = stmt.where(func.date(Pago.fecha_pago) >= d)
    if h is not None:
        stmt = stmt.where(func.date(Pago.fecha_pago) <= h)
    if metodo_id is not None:
        try:
            mid = int(metodo_id)
        except Exception:
            mid = None
        if mid is not None:
            stmt = stmt.where(Pago.metodo_pago_id == mid)
    if sid is not None:
        stmt = stmt.where(Pago.sucursal_id == int(sid))

    rows = (
        db.execute(stmt.order_by(Pago.fecha_pago.desc()).limit(limit_i).offset(offset_i))
        .mappings()
        .all()
    )

    pagos: List[Dict[str, Any]] = []
    for r in rows or []:
        p = r.get("Pago")
        if not p:
            continue
        pagos.append(
            {
                "id": int(getattr(p, "id", 0) or 0),
                "usuario_id": int(getattr(p, "usuario_id", 0) or 0),
                "usuario_nombre": r.get("usuario_nombre"),
                "monto": float(getattr(p, "monto", 0) or 0),
                "fecha_pago": getattr(p, "fecha_pago", None),
                "mes": getattr(p, "mes", None),
                "anio": getattr(p, "año", None),
                "metodo_pago_id": getattr(p, "metodo_pago_id", None),
                "metodo_pago": getattr(p, "metodo_pago", None),
                "estado": getattr(p, "estado", None),
                "sucursal_id": getattr(p, "sucursal_id", None),
                "sucursal_nombre": r.get("sucursal_nombre"),
            }
        )

    return {"ok": True, "pagos": pagos, "limit": limit_i, "offset": offset_i}


@router.get("/api/owner_dashboard/asistencias")
async def api_owner_dashboard_asistencias(
    request: Request,
    db: Session = Depends(get_db_session),
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
):
    sid = _get_optional_sucursal_id(request, db)
    page_i = max(1, int(page or 1))
    limit_i = max(1, min(int(limit or 20), 200))
    offset_i = (page_i - 1) * limit_i

    d = None
    h = None
    try:
        d = date.fromisoformat(str(desde)) if desde else None
    except Exception:
        d = None
    try:
        h = date.fromisoformat(str(hasta)) if hasta else None
    except Exception:
        h = None

    if d is None and h is None:
        h = date.today()
        d = h - timedelta(days=7)

    stmt = (
        select(
            Asistencia,
            Usuario.nombre.label("usuario_nombre"),
            Sucursal.nombre.label("sucursal_nombre"),
        )
        .join(Usuario, Asistencia.usuario_id == Usuario.id)
        .outerjoin(Sucursal, Asistencia.sucursal_id == Sucursal.id)
    )
    if d is not None:
        stmt = stmt.where(Asistencia.fecha >= d)
    if h is not None:
        stmt = stmt.where(Asistencia.fecha <= h)
    if sid is not None:
        stmt = stmt.where(Asistencia.sucursal_id == int(sid))

    rows = (
        db.execute(stmt.order_by(Asistencia.fecha.desc()).limit(limit_i).offset(offset_i))
        .mappings()
        .all()
    )

    items: List[Dict[str, Any]] = []
    for r in rows or []:
        a = r.get("Asistencia")
        if not a:
            continue
        items.append(
            {
                "id": int(getattr(a, "id", 0) or 0),
                "usuario_id": int(getattr(a, "usuario_id", 0) or 0),
                "usuario_nombre": r.get("usuario_nombre"),
                "fecha": getattr(a, "fecha", None),
                "hora": getattr(a, "hora", None),
                "tipo": getattr(a, "tipo", None),
                "sucursal_id": getattr(a, "sucursal_id", None),
                "sucursal_nombre": r.get("sucursal_nombre"),
            }
        )

    return {"ok": True, "asistencias": items, "limit": limit_i, "offset": offset_i}


@router.get("/api/owner_dashboard/export/{type}/csv")
async def api_owner_dashboard_export_csv(
    request: Request,
    type: str,
    db: Session = Depends(get_db_session),
    reports: ReportsService = Depends(get_reports_service),
    desde: Optional[str] = Query(None),
    hasta: Optional[str] = Query(None),
):
    sid = _get_optional_sucursal_id(request, db)
    t = str(type or "").strip().lower()
    if t == "usuarios":
        def _load():
            rows = db.execute(
                text(
                    """
                    SELECT
                      u.id,
                      u.nombre,
                      u.dni,
                      u.telefono,
                      u.activo,
                      u.rol,
                      u.tipo_cuota,
                      u.fecha_registro AS created_at,
                      u.sucursal_registro_id,
                      s.nombre AS sucursal_registro_nombre
                    FROM usuarios u
                    LEFT JOIN tipos_cuota tc ON LOWER(tc.nombre) = LOWER(u.tipo_cuota)
                    LEFT JOIN sucursales s ON s.id = u.sucursal_registro_id
                    WHERE (
                      :sid IS NULL OR
                      COALESCE((
                          SELECT uas.allow
                          FROM usuario_accesos_sucursales uas
                          WHERE uas.usuario_id = u.id
                            AND uas.sucursal_id = :sid
                            AND (uas.starts_at IS NULL OR uas.starts_at <= NOW())
                            AND (uas.ends_at IS NULL OR uas.ends_at >= NOW())
                          ORDER BY uas.id DESC
                          LIMIT 1
                      ), (
                          COALESCE(tc.all_sucursales, FALSE)
                          OR EXISTS (
                              SELECT 1
                              FROM tipo_cuota_sucursales tcs
                              WHERE tcs.tipo_cuota_id = tc.id
                                AND tcs.sucursal_id = :sid
                          )
                      )) = TRUE
                    )
                    ORDER BY u.nombre ASC
                    """
                ),
                {"sid": int(sid) if sid is not None else None},
            ).mappings().all()
            return [
                {
                    "id": r.get("id"),
                    "nombre": r.get("nombre"),
                    "dni": r.get("dni"),
                    "telefono": r.get("telefono"),
                    "activo": r.get("activo"),
                    "rol": r.get("rol"),
                    "tipo_cuota": r.get("tipo_cuota"),
                    "created_at": r.get("created_at"),
                    "sucursal_registro_id": r.get("sucursal_registro_id"),
                    "sucursal_registro_nombre": r.get("sucursal_registro_nombre"),
                }
                for r in (rows or [])
            ]

        data = _safe(_load, [])
        return _to_csv_response(data, f"usuarios_{date.today().isoformat()}.csv")
    if t == "pagos":
        def _load():
            d = None
            h = None
            try:
                d = date.fromisoformat(desde) if desde else None
            except Exception:
                d = None
            try:
                h = date.fromisoformat(hasta) if hasta else None
            except Exception:
                h = None
            rows = db.execute(
                text(
                    """
                    SELECT
                      p.id,
                      p.usuario_id,
                      u.nombre AS usuario_nombre,
                      p.monto,
                      p.fecha_pago,
                      p.metodo_pago,
                      p.metodo_pago_id,
                      p.estado,
                      p.sucursal_id,
                      s.nombre AS sucursal_nombre
                    FROM pagos p
                    JOIN usuarios u ON u.id = p.usuario_id
                    LEFT JOIN sucursales s ON s.id = p.sucursal_id
                    WHERE (:sid IS NULL OR p.sucursal_id = :sid)
                      AND (:desde IS NULL OR DATE(p.fecha_pago) >= :desde)
                      AND (:hasta IS NULL OR DATE(p.fecha_pago) <= :hasta)
                    ORDER BY p.fecha_pago DESC
                    """
                ),
                {
                    "sid": int(sid) if sid is not None else None,
                    "desde": d,
                    "hasta": h,
                },
            ).mappings().all()
            return [
                {
                    "id": r.get("id"),
                    "usuario_id": r.get("usuario_id"),
                    "usuario_nombre": r.get("usuario_nombre"),
                    "monto": r.get("monto"),
                    "fecha_pago": r.get("fecha_pago"),
                    "metodo_pago": r.get("metodo_pago"),
                    "metodo_pago_id": r.get("metodo_pago_id"),
                    "estado": r.get("estado"),
                    "sucursal_id": r.get("sucursal_id"),
                    "sucursal_nombre": r.get("sucursal_nombre"),
                }
                for r in (rows or [])
            ]

        data = _safe(_load, [])
        return _to_csv_response(data, f"pagos_{date.today().isoformat()}.csv")
    if t == "asistencias":
        def _load():
            d = None
            h = None
            try:
                d = date.fromisoformat(desde) if desde else None
            except Exception:
                d = None
            try:
                h = date.fromisoformat(hasta) if hasta else None
            except Exception:
                h = None
            rows = db.execute(
                text(
                    """
                    SELECT
                      a.id,
                      a.usuario_id,
                      u.nombre AS usuario_nombre,
                      a.fecha,
                      a.hora,
                      a.tipo,
                      a.sucursal_id,
                      s.nombre AS sucursal_nombre
                    FROM asistencias a
                    JOIN usuarios u ON u.id = a.usuario_id
                    LEFT JOIN sucursales s ON s.id = a.sucursal_id
                    WHERE (:sid IS NULL OR a.sucursal_id = :sid)
                      AND (:desde IS NULL OR a.fecha >= :desde)
                      AND (:hasta IS NULL OR a.fecha <= :hasta)
                    ORDER BY a.fecha DESC
                    """
                ),
                {
                    "sid": int(sid) if sid is not None else None,
                    "desde": d,
                    "hasta": h,
                },
            ).mappings().all()
            return [
                {
                    "id": r.get("id"),
                    "usuario_id": r.get("usuario_id"),
                    "usuario_nombre": r.get("usuario_nombre"),
                    "fecha": r.get("fecha"),
                    "hora": r.get("hora"),
                    "tipo": r.get("tipo"),
                    "sucursal_id": r.get("sucursal_id"),
                    "sucursal_nombre": r.get("sucursal_nombre"),
                }
                for r in (rows or [])
            ]

        data = _safe(_load, [])
        return _to_csv_response(data, f"asistencias_{date.today().isoformat()}.csv")
    if t == "asistencias_audit":
        try:
            d = date.fromisoformat(desde) if desde else None
        except Exception:
            d = None
        try:
            h = date.fromisoformat(hasta) if hasta else None
        except Exception:
            h = None
        data = _safe(
            lambda: reports.obtener_auditoria_asistencias(
                desde=d, hasta=h, dias=35, sucursal_id=sid
            ),
            {"ok": False},
        )
        rows = []
        if isinstance(data, dict) and data.get("ok"):
            rows = list(data.get("daily") or [])
        return _to_csv_response(rows, f"asistencias_audit_{date.today().isoformat()}.csv")
    return JSONResponse({"ok": False, "error": "type_invalid"}, status_code=400)
