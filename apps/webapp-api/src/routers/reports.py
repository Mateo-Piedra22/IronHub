"""Reports Router - KPIs, statistics, charts, and exports using ReportsService."""

import logging
import csv
import io
from datetime import date

from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse, StreamingResponse

from src.dependencies import (
    require_gestion_access,
    require_owner,
    get_reports_service,
    require_feature,
    require_sucursal_selected,
    require_scope_gestion,
)
from src.services.reports_service import ReportsService

router = APIRouter(
    dependencies=[
        Depends(require_feature("reportes")),
        Depends(require_sucursal_selected),
        Depends(require_scope_gestion("reportes:read")),
    ]
)
logger = logging.getLogger(__name__)


# === KPIs ===


@router.get("/api/kpis")
async def api_kpis(
    _=Depends(require_gestion_access),
    svc: ReportsService = Depends(get_reports_service),
):
    """Get main KPIs for dashboard."""
    return svc.obtener_kpis()


@router.get("/api/kpis_avanzados")
async def api_kpis_avanzados(
    _=Depends(require_gestion_access),
    svc: ReportsService = Depends(get_reports_service),
):
    """Get advanced KPIs."""
    return svc.obtener_kpis_avanzados()


@router.get("/api/activos_inactivos")
async def api_activos_inactivos(
    _=Depends(require_gestion_access),
    svc: ReportsService = Depends(get_reports_service),
):
    """Get active/inactive distribution."""
    return svc.obtener_activos_inactivos()


# === 12-Month Trends ===


@router.get("/api/ingresos12m")
async def api_ingresos12m(
    _=Depends(require_gestion_access),
    svc: ReportsService = Depends(get_reports_service),
):
    """Get income for the last 12 months."""
    return {"data": svc.obtener_ingresos_12m()}


@router.get("/api/nuevos12m")
async def api_nuevos12m(
    _=Depends(require_gestion_access),
    svc: ReportsService = Depends(get_reports_service),
):
    """Get new users for the last 12 months."""
    return {"data": svc.obtener_nuevos_12m()}


@router.get("/api/arpu12m")
async def api_arpu12m(
    _=Depends(require_gestion_access),
    svc: ReportsService = Depends(get_reports_service),
):
    """Average revenue per user for last 12 months."""
    return {"data": svc.obtener_arpu_12m()}


# === Cohort and Retention ===


@router.get("/api/cohort_retencion_6m")
async def api_cohort_retencion_6m(
    _=Depends(require_gestion_access),
    svc: ReportsService = Depends(get_reports_service),
):
    """Get 6-month cohort retention data."""
    return {"cohorts": svc.obtener_cohort_6m()}


@router.get("/api/cohort_retencion_heatmap")
async def api_cohort_retencion_heatmap(
    _=Depends(require_gestion_access),
    svc: ReportsService = Depends(get_reports_service),
):
    """Cohort retention heatmap data."""
    return {"cohorts": svc.obtener_cohort_6m()}


@router.get("/api/arpa_por_tipo_cuota")
async def api_arpa_por_tipo_cuota(
    _=Depends(require_gestion_access),
    svc: ReportsService = Depends(get_reports_service),
):
    """ARPA by quota type."""
    return {"data": svc.obtener_arpa_por_tipo()}


@router.get("/api/payment_status_dist")
async def api_payment_status_dist(
    _=Depends(require_gestion_access),
    svc: ReportsService = Depends(get_reports_service),
):
    """Payment status distribution."""
    return svc.obtener_estado_pagos()


@router.get("/api/waitlist_events")
async def api_waitlist_events(
    _=Depends(require_gestion_access),
    svc: ReportsService = Depends(get_reports_service),
):
    """Get recent waitlist events."""
    return {"events": svc.obtener_eventos_espera()}


# === Delinquency and Alerts ===


@router.get("/api/delinquency_alerts_recent")
async def api_delinquency_alerts_recent(
    _=Depends(require_gestion_access),
    svc: ReportsService = Depends(get_reports_service),
):
    """Get recent delinquency alerts."""
    return {"alerts": svc.obtener_alertas_morosidad()}


# === Exports ===


def _to_csv_response(data: list, filename: str):
    """Helper to convert list of dicts to CSV response."""
    if not data:
        output = io.StringIO()
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=data[0].keys())
    writer.writeheader()
    writer.writerows(data)
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/api/export/usuarios/csv")
async def api_export_usuarios_csv(
    _=Depends(require_gestion_access),
    svc: ReportsService = Depends(get_reports_service),
):
    """Export all users to CSV."""
    return _to_csv_response(
        svc.exportar_usuarios(), f"usuarios_{date.today().isoformat()}.csv"
    )


@router.get("/api/export/pagos/csv")
async def api_export_pagos_csv(
    request: Request,
    _=Depends(require_gestion_access),
    svc: ReportsService = Depends(get_reports_service),
):
    """Export payments to CSV."""
    return _to_csv_response(
        svc.exportar_pagos(
            request.query_params.get("desde"), request.query_params.get("hasta")
        ),
        f"pagos_{date.today().isoformat()}.csv",
    )


@router.get("/api/export/asistencias/csv")
async def api_export_asistencias_csv(
    request: Request,
    _=Depends(require_gestion_access),
    svc: ReportsService = Depends(get_reports_service),
):
    """Export attendance to CSV."""
    return _to_csv_response(
        svc.exportar_asistencias(
            request.query_params.get("desde"), request.query_params.get("hasta")
        ),
        f"asistencias_{date.today().isoformat()}.csv",
    )


@router.get("/api/export/asistencias_audit/csv")
async def api_export_asistencias_audit_csv(
    request: Request,
    _=Depends(require_owner),
    svc: ReportsService = Depends(get_reports_service),
):
    return _to_csv_response(
        svc.exportar_asistencias_audit(
            request.query_params.get("desde"), request.query_params.get("hasta")
        ),
        f"asistencias_audit_{date.today().isoformat()}.csv",
    )


# Legacy endpoints
@router.get("/api/export")
async def api_export(request: Request, _=Depends(require_gestion_access)):
    return JSONResponse(
        {
            "message": "Use /api/export/usuarios/csv, /api/export/pagos/csv, or /api/export/asistencias/csv"
        }
    )


@router.get("/api/export_csv")
async def api_export_csv(
    _=Depends(require_gestion_access),
    svc: ReportsService = Depends(get_reports_service),
):
    return _to_csv_response(
        svc.exportar_usuarios(), f"usuarios_{date.today().isoformat()}.csv"
    )


# === Gym Subscription ===


@router.get("/api/gym/subscription")
async def api_gym_subscription(_=Depends(require_gestion_access)):
    """Get gym subscription status."""
    return {
        "subscription": {"active": True, "next_due_date": None},
        "days_until_due": None,
    }
