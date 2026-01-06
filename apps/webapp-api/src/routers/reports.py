"""
Reports Router - KPIs, statistics, charts, and exports
"""
import logging
from datetime import datetime, timezone, date
from typing import Optional, List, Dict, Any
from calendar import monthrange
import csv
import io

import psycopg2
import psycopg2.extras
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse

from src.dependencies import get_db, require_gestion_access

router = APIRouter()
logger = logging.getLogger(__name__)


# === KPIs ===

@router.get("/api/kpis")
async def api_kpis(_=Depends(require_gestion_access)):
    """Get main KPIs for dashboard"""
    from src.dependencies import get_db
    db = get_db()
    if db is None:
        return {
            "total_activos": 0,
            "total_inactivos": 0,
            "ingresos_mes": 0,
            "asistencias_hoy": 0,
            "nuevos_30_dias": 0
        }
    try:
        with db.get_connection_context() as conn:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            # Active users
            cur.execute("SELECT COUNT(*) as count FROM usuarios WHERE activo = TRUE")
            activos = cur.fetchone()["count"] or 0
            
            # Inactive users
            cur.execute("SELECT COUNT(*) as count FROM usuarios WHERE activo = FALSE")
            inactivos = cur.fetchone()["count"] or 0
            
            # Income this month
            cur.execute("""
                SELECT COALESCE(SUM(monto), 0) as total
                FROM pagos
                WHERE DATE_TRUNC('month', fecha) = DATE_TRUNC('month', CURRENT_DATE)
            """)
            ingresos = float(cur.fetchone()["total"] or 0)
            
            # Attendance today
            cur.execute("""
                SELECT COUNT(*) as count
                FROM asistencias
                WHERE DATE(created_at) = CURRENT_DATE
            """)
            asistencias = cur.fetchone()["count"] or 0
            
            # New users in last 30 days
            cur.execute("""
                SELECT COUNT(*) as count
                FROM usuarios
                WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
            """)
            nuevos = cur.fetchone()["count"] or 0
            
            return {
                "total_activos": activos,
                "total_inactivos": inactivos,
                "ingresos_mes": ingresos,
                "asistencias_hoy": asistencias,
                "nuevos_30_dias": nuevos
            }
    except Exception as e:
        logger.exception("Error getting KPIs")
        return {
            "total_activos": 0,
            "total_inactivos": 0,
            "ingresos_mes": 0,
            "asistencias_hoy": 0,
            "nuevos_30_dias": 0
        }


@router.get("/api/ingresos12m")
async def api_ingresos12m(_=Depends(require_gestion_access)):
    """Get income for the last 12 months"""
    from src.dependencies import get_db
    db = get_db()
    if db is None:
        return {"data": []}
    try:
        with db.get_connection_context() as conn:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute("""
                SELECT 
                    TO_CHAR(fecha, 'YYYY-MM') as mes,
                    SUM(monto) as total
                FROM pagos
                WHERE fecha >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '11 months')
                GROUP BY TO_CHAR(fecha, 'YYYY-MM')
                ORDER BY mes ASC
            """)
            rows = cur.fetchall() or []
            data = [{"mes": r["mes"], "total": float(r["total"] or 0)} for r in rows]
            return {"data": data}
    except Exception as e:
        logger.exception("Error getting ingresos12m")
        return {"data": []}


@router.get("/api/nuevos12m")
async def api_nuevos12m(_=Depends(require_gestion_access)):
    """Get new users for the last 12 months"""
    from src.dependencies import get_db
    db = get_db()
    if db is None:
        return {"data": []}
    try:
        with db.get_connection_context() as conn:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute("""
                SELECT 
                    TO_CHAR(created_at, 'YYYY-MM') as mes,
                    COUNT(*) as total
                FROM usuarios
                WHERE created_at >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '11 months')
                GROUP BY TO_CHAR(created_at, 'YYYY-MM')
                ORDER BY mes ASC
            """)
            rows = cur.fetchall() or []
            data = [{"mes": r["mes"], "total": int(r["total"] or 0)} for r in rows]
            return {"data": data}
    except Exception as e:
        logger.exception("Error getting nuevos12m")
        return {"data": []}


@router.get("/api/arpu12m")
async def api_arpu12m(_=Depends(require_gestion_access)):
    """Average revenue per user for last 12 months"""
    from src.dependencies import get_db
    db = get_db()
    if db is None:
        return {"data": []}
    try:
        with db.get_connection_context() as conn:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute("""
                SELECT 
                    TO_CHAR(p.fecha, 'YYYY-MM') as mes,
                    SUM(p.monto) / NULLIF(COUNT(DISTINCT p.usuario_id), 0) as arpu
                FROM pagos p
                WHERE p.fecha >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '11 months')
                GROUP BY TO_CHAR(p.fecha, 'YYYY-MM')
                ORDER BY mes ASC
            """)
            rows = cur.fetchall() or []
            data = [{"mes": r["mes"], "arpu": float(r["arpu"] or 0)} for r in rows]
            return {"data": data}
    except Exception as e:
        logger.exception("Error getting arpu12m")
        return {"data": []}


@router.get("/api/activos_inactivos")
async def api_activos_inactivos(_=Depends(require_gestion_access)):
    """Get active/inactive distribution"""
    from src.dependencies import get_db
    db = get_db()
    if db is None:
        return {"activos": 0, "inactivos": 0}
    try:
        with db.get_connection_context() as conn:
            cur = conn.cursor()
            cur.execute("SELECT activo, COUNT(*) FROM usuarios GROUP BY activo")
            rows = cur.fetchall()
            result = {"activos": 0, "inactivos": 0}
            for row in rows:
                if row[0]:
                    result["activos"] = row[1]
                else:
                    result["inactivos"] = row[1]
            return result
    except Exception as e:
        logger.exception("Error getting activos/inactivos")
        return {"activos": 0, "inactivos": 0}


@router.get("/api/kpis_avanzados")
async def api_kpis_avanzados(_=Depends(require_gestion_access)):
    """Advanced KPIs"""
    from src.dependencies import get_db
    db = get_db()
    if db is None:
        return {}
    try:
        with db.get_connection_context() as conn:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            # Churn rate (users who became inactive in last 30 days)
            cur.execute("""
                SELECT COUNT(*) as count FROM usuarios 
                WHERE activo = FALSE AND updated_at >= CURRENT_DATE - INTERVAL '30 days'
            """)
            churned = cur.fetchone()["count"] or 0
            
            # Total active at start of period
            cur.execute("""
                SELECT COUNT(*) as count FROM usuarios 
                WHERE activo = TRUE OR (activo = FALSE AND updated_at >= CURRENT_DATE - INTERVAL '30 days')
            """)
            total_start = cur.fetchone()["count"] or 1
            
            churn_rate = round(churned / total_start * 100, 1) if total_start > 0 else 0
            
            # Average payment amount
            cur.execute("""
                SELECT AVG(monto) as avg_monto FROM pagos 
                WHERE fecha >= CURRENT_DATE - INTERVAL '30 days'
            """)
            avg_pago = float(cur.fetchone()["avg_monto"] or 0)
            
            return {
                "churn_rate": churn_rate,
                "avg_pago": round(avg_pago, 2),
                "churned_30d": churned
            }
    except Exception as e:
        logger.exception("Error getting kpis_avanzados")
        return {}


# === Cohort and Retention ===

@router.get("/api/cohort_retencion_6m")
async def api_cohort_retencion_6m(_=Depends(require_gestion_access)):
    """Get 6-month cohort retention data"""
    from src.dependencies import get_db
    db = get_db()
    if db is None:
        return {"cohorts": []}
    try:
        with db.get_connection_context() as conn:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute("""
                WITH cohorts AS (
                    SELECT 
                        id,
                        DATE_TRUNC('month', created_at) as cohort_month,
                        activo
                    FROM usuarios
                    WHERE created_at >= CURRENT_DATE - INTERVAL '6 months'
                )
                SELECT 
                    TO_CHAR(cohort_month, 'YYYY-MM') as cohort,
                    COUNT(*) as total,
                    SUM(CASE WHEN activo THEN 1 ELSE 0 END) as retained
                FROM cohorts
                GROUP BY cohort_month
                ORDER BY cohort_month ASC
            """)
            rows = cur.fetchall() or []
            cohorts = []
            for r in rows:
                total = int(r["total"] or 0)
                retained = int(r["retained"] or 0)
                cohorts.append({
                    "cohort": r["cohort"],
                    "total": total,
                    "retained": retained,
                    "retention_rate": round(retained / total * 100, 1) if total > 0 else 0
                })
            return {"cohorts": cohorts}
    except Exception as e:
        logger.exception("Error getting cohort retention")
        return {"cohorts": []}


@router.get("/api/cohort_retencion_heatmap")
async def api_cohort_retencion_heatmap(_=Depends(require_gestion_access)):
    """Cohort retention heatmap data"""
    # Simplified version - same as 6m for now
    return await api_cohort_retencion_6m()


@router.get("/api/arpa_por_tipo_cuota")
async def api_arpa_por_tipo_cuota(_=Depends(require_gestion_access)):
    """ARPA by quota type"""
    from src.dependencies import get_db
    db = get_db()
    if db is None:
        return {"data": []}
    try:
        with db.get_connection_context() as conn:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute("""
                SELECT 
                    tc.nombre as tipo,
                    AVG(p.monto) as arpa
                FROM pagos p
                JOIN usuarios u ON p.usuario_id = u.id
                LEFT JOIN tipos_cuota tc ON u.tipo_cuota_id = tc.id
                WHERE p.fecha >= CURRENT_DATE - INTERVAL '3 months'
                GROUP BY tc.nombre
                ORDER BY arpa DESC
            """)
            rows = cur.fetchall() or []
            return {"data": [{"tipo": r["tipo"] or "Sin tipo", "arpa": float(r["arpa"] or 0)} for r in rows]}
    except Exception as e:
        return {"data": []}


@router.get("/api/payment_status_dist")
async def api_payment_status_dist(_=Depends(require_gestion_access)):
    """Payment status distribution"""
    from src.dependencies import get_db
    db = get_db()
    if db is None:
        return {"al_dia": 0, "vencido": 0, "sin_pagos": 0}
    try:
        with db.get_connection_context() as conn:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            # Users with payment in last 35 days
            cur.execute("""
                SELECT COUNT(DISTINCT u.id) as count
                FROM usuarios u
                JOIN pagos p ON u.id = p.usuario_id
                WHERE u.activo = TRUE AND p.fecha >= CURRENT_DATE - INTERVAL '35 days'
            """)
            al_dia = cur.fetchone()["count"] or 0
            
            # Users with old payments
            cur.execute("""
                SELECT COUNT(DISTINCT u.id) as count
                FROM usuarios u
                JOIN pagos p ON u.id = p.usuario_id
                WHERE u.activo = TRUE
                GROUP BY u.id
                HAVING MAX(p.fecha) < CURRENT_DATE - INTERVAL '35 days'
            """)
            vencido = cur.rowcount or 0
            
            # Users with no payments
            cur.execute("""
                SELECT COUNT(*) as count
                FROM usuarios u
                LEFT JOIN pagos p ON u.id = p.usuario_id
                WHERE u.activo = TRUE AND p.id IS NULL
            """)
            sin_pagos = cur.fetchone()["count"] or 0
            
            return {"al_dia": al_dia, "vencido": vencido, "sin_pagos": sin_pagos}
    except Exception as e:
        return {"al_dia": 0, "vencido": 0, "sin_pagos": 0}


@router.get("/api/waitlist_events")
async def api_waitlist_events(_=Depends(require_gestion_access)):
    """Get recent waitlist events"""
    from src.dependencies import get_db
    db = get_db()
    if db is None:
        return {"events": []}
    try:
        with db.get_connection_context() as conn:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute("""
                SELECT le.id, le.horario_id, le.usuario_id, le.posicion, le.fecha_registro,
                       u.nombre as usuario_nombre
                FROM lista_espera le
                JOIN usuarios u ON le.usuario_id = u.id
                ORDER BY le.fecha_registro DESC
                LIMIT 20
            """)
            rows = cur.fetchall() or []
            events = []
            for r in rows:
                events.append({
                    "id": r["id"],
                    "usuario_nombre": r["usuario_nombre"],
                    "posicion": r["posicion"],
                    "fecha": r["fecha_registro"].isoformat() if r["fecha_registro"] else None
                })
            return {"events": events}
    except Exception as e:
        return {"events": []}


# === Delinquency and Alerts ===

@router.get("/api/delinquency_alerts_recent")
async def api_delinquency_alerts_recent(_=Depends(require_gestion_access)):
    """Get recent delinquency alerts"""
    from src.dependencies import get_db
    db = get_db()
    if db is None:
        return {"alerts": []}
    try:
        with db.get_connection_context() as conn:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute("""
                SELECT 
                    u.id as usuario_id,
                    u.nombre as usuario_nombre,
                    u.activo,
                    MAX(p.fecha) as ultimo_pago
                FROM usuarios u
                LEFT JOIN pagos p ON u.id = p.usuario_id
                WHERE u.activo = FALSE 
                  AND (u.updated_at IS NULL OR u.updated_at >= CURRENT_DATE)
                GROUP BY u.id, u.nombre, u.activo
                ORDER BY u.nombre
                LIMIT 20
            """)
            rows = cur.fetchall() or []
            alerts = []
            for r in rows:
                alerts.append({
                    "usuario_id": r["usuario_id"],
                    "usuario_nombre": r["usuario_nombre"],
                    "ultimo_pago": r["ultimo_pago"].isoformat() if r["ultimo_pago"] else None
                })
            return {"alerts": alerts}
    except Exception as e:
        logger.exception("Error getting delinquency alerts")
        return {"alerts": []}


@router.get("/api/profesor_resumen")
async def api_profesor_resumen(request: Request, _=Depends(require_gestion_access)):
    """Get profesor summary (redirects to profesores router)"""
    profesor_id = request.query_params.get("profesor_id")
    if not profesor_id:
        return {}
    # This should use the profesores router's resumen endpoints
    return {}


# === Exports ===

@router.get("/api/export/usuarios/csv")
async def api_export_usuarios_csv(_=Depends(require_gestion_access)):
    """Export all users to CSV"""
    from src.dependencies import get_db
    db = get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="DB not available")
    try:
        with db.get_connection_context() as conn:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute("""
                SELECT 
                    id, nombre, dni, telefono, email, activo, rol,
                    tipo_cuota_id, notas, created_at
                FROM usuarios
                ORDER BY nombre ASC
            """)
            rows = cur.fetchall() or []
            
            output = io.StringIO()
            if rows:
                writer = csv.DictWriter(output, fieldnames=rows[0].keys())
                writer.writeheader()
                for row in rows:
                    row_dict = dict(row)
                    if row_dict.get("created_at"):
                        row_dict["created_at"] = row_dict["created_at"].isoformat()
                    writer.writerow(row_dict)
            
            output.seek(0)
            
            return StreamingResponse(
                iter([output.getvalue()]),
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename=usuarios_{date.today().isoformat()}.csv"
                }
            )
    except Exception as e:
        logger.exception("Error exporting usuarios CSV")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/export/pagos/csv")
async def api_export_pagos_csv(
    request: Request,
    _=Depends(require_gestion_access)
):
    """Export payments to CSV"""
    from src.dependencies import get_db
    db = get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="DB not available")
    try:
        desde = request.query_params.get("desde")
        hasta = request.query_params.get("hasta")
        
        with db.get_connection_context() as conn:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            query = """
                SELECT 
                    p.id, p.usuario_id, u.nombre as usuario_nombre,
                    p.monto, p.fecha, p.metodo_id, m.nombre as metodo_nombre,
                    p.notas, p.created_at
                FROM pagos p
                LEFT JOIN usuarios u ON p.usuario_id = u.id
                LEFT JOIN metodos_pago m ON p.metodo_id = m.id
                WHERE 1=1
            """
            params: List[Any] = []
            
            if desde:
                query += " AND p.fecha >= %s"
                params.append(desde)
            if hasta:
                query += " AND p.fecha <= %s"
                params.append(hasta)
            
            query += " ORDER BY p.fecha DESC"
            
            cur.execute(query, params)
            rows = cur.fetchall() or []
            
            output = io.StringIO()
            if rows:
                writer = csv.DictWriter(output, fieldnames=rows[0].keys())
                writer.writeheader()
                for row in rows:
                    row_dict = dict(row)
                    for key in ["fecha", "created_at"]:
                        if row_dict.get(key) and hasattr(row_dict[key], "isoformat"):
                            row_dict[key] = row_dict[key].isoformat()
                    writer.writerow(row_dict)
            
            output.seek(0)
            
            return StreamingResponse(
                iter([output.getvalue()]),
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename=pagos_{date.today().isoformat()}.csv"
                }
            )
    except Exception as e:
        logger.exception("Error exporting pagos CSV")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/export/asistencias/csv")
async def api_export_asistencias_csv(
    request: Request,
    _=Depends(require_gestion_access)
):
    """Export attendance to CSV"""
    from src.dependencies import get_db
    db = get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="DB not available")
    try:
        desde = request.query_params.get("desde")
        hasta = request.query_params.get("hasta")
        
        with db.get_connection_context() as conn:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            query = """
                SELECT 
                    a.id, a.usuario_id, u.nombre as usuario_nombre,
                    a.created_at
                FROM asistencias a
                LEFT JOIN usuarios u ON a.usuario_id = u.id
                WHERE 1=1
            """
            params: List[Any] = []
            
            if desde:
                query += " AND DATE(a.created_at) >= %s"
                params.append(desde)
            if hasta:
                query += " AND DATE(a.created_at) <= %s"
                params.append(hasta)
            
            query += " ORDER BY a.created_at DESC"
            
            cur.execute(query, params)
            rows = cur.fetchall() or []
            
            output = io.StringIO()
            if rows:
                writer = csv.DictWriter(output, fieldnames=rows[0].keys())
                writer.writeheader()
                for row in rows:
                    row_dict = dict(row)
                    if row_dict.get("created_at"):
                        row_dict["created_at"] = row_dict["created_at"].isoformat()
                    writer.writerow(row_dict)
            
            output.seek(0)
            
            return StreamingResponse(
                iter([output.getvalue()]),
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename=asistencias_{date.today().isoformat()}.csv"
                }
            )
    except Exception as e:
        logger.exception("Error exporting asistencias CSV")
        raise HTTPException(status_code=500, detail=str(e))


# Legacy endpoints - keep for backwards compatibility
@router.get("/api/export")
async def api_export(request: Request, _=Depends(require_gestion_access)):
    """Generic export endpoint"""
    return JSONResponse({"message": "Use /api/export/usuarios/csv, /api/export/pagos/csv, or /api/export/asistencias/csv"})


@router.get("/api/export_csv")
async def api_export_csv(request: Request, _=Depends(require_gestion_access)):
    """Legacy CSV export - redirects to usuarios"""
    return await api_export_usuarios_csv()


# === Gym Subscription (admin) ===

@router.get("/api/gym/subscription")
async def api_gym_subscription(_=Depends(require_gestion_access)):
    """Get gym subscription status"""
    return {
        "subscription": {"active": True, "next_due_date": None},
        "days_until_due": None
    }
