"""Reports Router - KPIs, statistics, charts, and exports using ReportsService."""
import logging
import csv
import io
from datetime import date

from fastapi import APIRouter, Request, Depends, HTTPException, Query
from typing import Optional
from fastapi.responses import JSONResponse, StreamingResponse

from src.dependencies import require_gestion_access, require_owner, get_reports_service, get_whatsapp_settings_service, get_whatsapp_service
from src.services.reports_service import ReportsService
from src.services.whatsapp_settings_service import WhatsAppSettingsService
from src.services.whatsapp_service import WhatsAppService

router = APIRouter()
logger = logging.getLogger(__name__)


# === KPIs ===

@router.get("/api/kpis")
async def api_kpis(_=Depends(require_gestion_access), svc: ReportsService = Depends(get_reports_service)):
    """Get main KPIs for dashboard."""
    return svc.obtener_kpis()


@router.get("/api/kpis_avanzados")
async def api_kpis_avanzados(_=Depends(require_gestion_access), svc: ReportsService = Depends(get_reports_service)):
    """Get advanced KPIs."""
    return svc.obtener_kpis_avanzados()


@router.get("/api/activos_inactivos")
async def api_activos_inactivos(_=Depends(require_gestion_access), svc: ReportsService = Depends(get_reports_service)):
    """Get active/inactive distribution."""
    return svc.obtener_activos_inactivos()


# === 12-Month Trends ===

@router.get("/api/ingresos12m")
async def api_ingresos12m(_=Depends(require_gestion_access), svc: ReportsService = Depends(get_reports_service)):
    """Get income for the last 12 months."""
    return {"data": svc.obtener_ingresos_12m()}


@router.get("/api/nuevos12m")
async def api_nuevos12m(_=Depends(require_gestion_access), svc: ReportsService = Depends(get_reports_service)):
    """Get new users for the last 12 months."""
    return {"data": svc.obtener_nuevos_12m()}


@router.get("/api/arpu12m")
async def api_arpu12m(_=Depends(require_gestion_access), svc: ReportsService = Depends(get_reports_service)):
    """Average revenue per user for last 12 months."""
    return {"data": svc.obtener_arpu_12m()}


# === Cohort and Retention ===

@router.get("/api/cohort_retencion_6m")
async def api_cohort_retencion_6m(_=Depends(require_gestion_access), svc: ReportsService = Depends(get_reports_service)):
    """Get 6-month cohort retention data."""
    return {"cohorts": svc.obtener_cohort_6m()}


@router.get("/api/cohort_retencion_heatmap")
async def api_cohort_retencion_heatmap(_=Depends(require_gestion_access), svc: ReportsService = Depends(get_reports_service)):
    """Cohort retention heatmap data."""
    return {"cohorts": svc.obtener_cohort_6m()}


@router.get("/api/arpa_por_tipo_cuota")
async def api_arpa_por_tipo_cuota(_=Depends(require_gestion_access), svc: ReportsService = Depends(get_reports_service)):
    """ARPA by quota type."""
    return {"data": svc.obtener_arpa_por_tipo()}


@router.get("/api/payment_status_dist")
async def api_payment_status_dist(_=Depends(require_gestion_access), svc: ReportsService = Depends(get_reports_service)):
    """Payment status distribution."""
    return svc.obtener_estado_pagos()


@router.get("/api/waitlist_events")
async def api_waitlist_events(_=Depends(require_gestion_access), svc: ReportsService = Depends(get_reports_service)):
    """Get recent waitlist events."""
    return {"events": svc.obtener_eventos_espera()}


# === Delinquency and Alerts ===

@router.get("/api/delinquency_alerts_recent")
async def api_delinquency_alerts_recent(_=Depends(require_gestion_access), svc: ReportsService = Depends(get_reports_service)):
    """Get recent delinquency alerts."""
    return {"alerts": svc.obtener_alertas_morosidad()}


@router.get("/api/owner_dashboard/overview")
async def api_owner_dashboard_overview(
    _=Depends(require_owner),
    reports: ReportsService = Depends(get_reports_service),
    wa_settings: WhatsAppSettingsService = Depends(get_whatsapp_settings_service),
    wa_svc: WhatsAppService = Depends(get_whatsapp_service),
):
    kpis = reports.obtener_kpis()
    kpis_adv = reports.obtener_kpis_avanzados()
    activos_inactivos = reports.obtener_activos_inactivos()
    ingresos12m = reports.obtener_ingresos_12m()
    nuevos12m = reports.obtener_nuevos_12m()
    arpu12m = reports.obtener_arpu_12m()
    arpa_por_tipo = reports.obtener_arpa_por_tipo()
    payment_status = reports.obtener_estado_pagos()
    cohorts_6m = reports.obtener_cohort_6m()
    waitlist_events = reports.obtener_eventos_espera()
    delinquency_alerts = reports.obtener_alertas_morosidad()
    wa_stats = wa_settings.get_stats()
    wa_pendientes = wa_svc.obtener_resumen_mensajes(30, 200)
    attendance_audit_7d = reports.obtener_auditoria_asistencias(dias=7)

    return {
        "ok": True,
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
async def api_owner_attendance_audit(
    _=Depends(require_owner),
    svc: ReportsService = Depends(get_reports_service),
    dias: int = Query(35, ge=1, le=366),
    desde: Optional[str] = Query(None),
    hasta: Optional[str] = Query(None),
    umbral_multiples: int = Query(3, ge=2, le=50),
    umbral_repeticion_minutos: int = Query(5, ge=1, le=60),
):
    d = date.fromisoformat(desde) if desde else None
    h = date.fromisoformat(hasta) if hasta else None
    return svc.obtener_auditoria_asistencias(
        desde=d,
        hasta=h,
        dias=dias,
        umbral_multiples=umbral_multiples,
        umbral_repeticion_minutos=umbral_repeticion_minutos,
    )





# === Exports ===

def _to_csv_response(data: list, filename: str):
    """Helper to convert list of dicts to CSV response."""
    if not data:
        output = io.StringIO()
        return StreamingResponse(iter([output.getvalue()]), media_type="text/csv",
                                headers={"Content-Disposition": f"attachment; filename={filename}"})
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=data[0].keys())
    writer.writeheader()
    writer.writerows(data)
    output.seek(0)
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv",
                            headers={"Content-Disposition": f"attachment; filename={filename}"})


@router.get("/api/export/usuarios/csv")
async def api_export_usuarios_csv(_=Depends(require_gestion_access), svc: ReportsService = Depends(get_reports_service)):
    """Export all users to CSV."""
    return _to_csv_response(svc.exportar_usuarios(), f"usuarios_{date.today().isoformat()}.csv")


@router.get("/api/export/pagos/csv")
async def api_export_pagos_csv(request: Request, _=Depends(require_gestion_access), svc: ReportsService = Depends(get_reports_service)):
    """Export payments to CSV."""
    return _to_csv_response(svc.exportar_pagos(request.query_params.get("desde"), request.query_params.get("hasta")), f"pagos_{date.today().isoformat()}.csv")


@router.get("/api/export/asistencias/csv")
async def api_export_asistencias_csv(request: Request, _=Depends(require_gestion_access), svc: ReportsService = Depends(get_reports_service)):
    """Export attendance to CSV."""
    return _to_csv_response(svc.exportar_asistencias(request.query_params.get("desde"), request.query_params.get("hasta")), f"asistencias_{date.today().isoformat()}.csv")


@router.get("/api/export/asistencias_audit/csv")
async def api_export_asistencias_audit_csv(request: Request, _=Depends(require_owner), svc: ReportsService = Depends(get_reports_service)):
    return _to_csv_response(
        svc.exportar_asistencias_audit(request.query_params.get("desde"), request.query_params.get("hasta")),
        f"asistencias_audit_{date.today().isoformat()}.csv",
    )


# Legacy endpoints
@router.get("/api/export")
async def api_export(request: Request, _=Depends(require_gestion_access)):
    return JSONResponse({"message": "Use /api/export/usuarios/csv, /api/export/pagos/csv, or /api/export/asistencias/csv"})


@router.get("/api/export_csv")
async def api_export_csv(_=Depends(require_gestion_access), svc: ReportsService = Depends(get_reports_service)):
    return _to_csv_response(svc.exportar_usuarios(), f"usuarios_{date.today().isoformat()}.csv")


# === Gym Subscription ===

@router.get("/api/gym/subscription")
async def api_gym_subscription(_=Depends(require_gestion_access)):
    """Get gym subscription status."""
    return {"subscription": {"active": True, "next_due_date": None}, "days_until_due": None}
