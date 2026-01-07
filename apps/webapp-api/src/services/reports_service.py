"""Reports Service - SQLAlchemy ORM for KPIs, statistics, and exports."""
from typing import Optional, Dict, Any, List
from datetime import date
import logging

from sqlalchemy.orm import Session
from sqlalchemy import text

from src.services.base import BaseService

logger = logging.getLogger(__name__)


class ReportsService(BaseService):
    """Service for reporting, KPIs, and data exports."""

    def __init__(self, db: Session):
        super().__init__(db)

    # ========== KPIs ==========
    
    def obtener_kpis(self) -> Dict[str, Any]:
        """Get main dashboard KPIs."""
        try:
            activos = self.db.execute(text("SELECT COUNT(*) FROM usuarios WHERE activo = TRUE")).fetchone()[0] or 0
            inactivos = self.db.execute(text("SELECT COUNT(*) FROM usuarios WHERE activo = FALSE")).fetchone()[0] or 0
            ingresos = float(self.db.execute(text("SELECT COALESCE(SUM(monto), 0) FROM pagos WHERE DATE_TRUNC('month', fecha) = DATE_TRUNC('month', CURRENT_DATE)")).fetchone()[0] or 0)
            asistencias = self.db.execute(text("SELECT COUNT(*) FROM asistencias WHERE DATE(created_at) = CURRENT_DATE")).fetchone()[0] or 0
            nuevos = self.db.execute(text("SELECT COUNT(*) FROM usuarios WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'")).fetchone()[0] or 0
            return {"total_activos": activos, "total_inactivos": inactivos, "ingresos_mes": ingresos, "asistencias_hoy": asistencias, "nuevos_30_dias": nuevos}
        except Exception as e:
            logger.error(f"Error getting KPIs: {e}")
            return {"total_activos": 0, "total_inactivos": 0, "ingresos_mes": 0, "asistencias_hoy": 0, "nuevos_30_dias": 0}

    def obtener_kpis_avanzados(self) -> Dict[str, Any]:
        """Get advanced KPIs (churn rate, avg payment)."""
        try:
            churned = self.db.execute(text("SELECT COUNT(*) FROM usuarios WHERE activo = FALSE AND updated_at >= CURRENT_DATE - INTERVAL '30 days'")).fetchone()[0] or 0
            total_start = self.db.execute(text("SELECT COUNT(*) FROM usuarios WHERE activo = TRUE OR (activo = FALSE AND updated_at >= CURRENT_DATE - INTERVAL '30 days')")).fetchone()[0] or 1
            avg_pago = float(self.db.execute(text("SELECT COALESCE(AVG(monto), 0) FROM pagos WHERE fecha >= CURRENT_DATE - INTERVAL '30 days'")).fetchone()[0] or 0)
            return {"churn_rate": round(churned / total_start * 100, 1), "avg_pago": round(avg_pago, 2), "churned_30d": churned}
        except Exception as e:
            logger.error(f"Error getting advanced KPIs: {e}")
            return {}

    def obtener_activos_inactivos(self) -> Dict[str, int]:
        """Get active/inactive user counts."""
        try:
            result = self.db.execute(text("SELECT activo, COUNT(*) FROM usuarios GROUP BY activo"))
            counts = {"activos": 0, "inactivos": 0}
            for row in result.fetchall():
                if row[0]: counts["activos"] = row[1]
                else: counts["inactivos"] = row[1]
            return counts
        except Exception as e:
            logger.error(f"Error getting active/inactive: {e}")
            return {"activos": 0, "inactivos": 0}

    # ========== 12-Month Trends ==========

    def obtener_ingresos_12m(self) -> List[Dict[str, Any]]:
        """Get income by month for last 12 months."""
        try:
            result = self.db.execute(text("""
                SELECT TO_CHAR(fecha, 'YYYY-MM') as mes, SUM(monto) as total
                FROM pagos WHERE fecha >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '11 months')
                GROUP BY TO_CHAR(fecha, 'YYYY-MM') ORDER BY mes
            """))
            return [{"mes": r[0], "total": float(r[1] or 0)} for r in result.fetchall()]
        except Exception as e:
            logger.error(f"Error getting ingresos 12m: {e}")
            return []

    def obtener_nuevos_12m(self) -> List[Dict[str, Any]]:
        """Get new users by month for last 12 months."""
        try:
            result = self.db.execute(text("""
                SELECT TO_CHAR(created_at, 'YYYY-MM') as mes, COUNT(*) as total
                FROM usuarios WHERE created_at >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '11 months')
                GROUP BY TO_CHAR(created_at, 'YYYY-MM') ORDER BY mes
            """))
            return [{"mes": r[0], "total": int(r[1] or 0)} for r in result.fetchall()]
        except Exception as e:
            logger.error(f"Error getting nuevos 12m: {e}")
            return []

    def obtener_arpu_12m(self) -> List[Dict[str, Any]]:
        """Get ARPU by month for last 12 months."""
        try:
            result = self.db.execute(text("""
                SELECT TO_CHAR(p.fecha, 'YYYY-MM') as mes, SUM(p.monto) / NULLIF(COUNT(DISTINCT p.usuario_id), 0) as arpu
                FROM pagos p WHERE p.fecha >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '11 months')
                GROUP BY TO_CHAR(p.fecha, 'YYYY-MM') ORDER BY mes
            """))
            return [{"mes": r[0], "arpu": float(r[1] or 0)} for r in result.fetchall()]
        except Exception as e:
            logger.error(f"Error getting ARPU 12m: {e}")
            return []

    # ========== Cohort and Retention ==========

    def obtener_cohort_6m(self) -> List[Dict[str, Any]]:
        """Get 6-month cohort retention data."""
        try:
            result = self.db.execute(text("""
                WITH cohorts AS (
                    SELECT id, DATE_TRUNC('month', created_at) as cohort_month, activo
                    FROM usuarios WHERE created_at >= CURRENT_DATE - INTERVAL '6 months'
                )
                SELECT TO_CHAR(cohort_month, 'YYYY-MM') as cohort, COUNT(*) as total, SUM(CASE WHEN activo THEN 1 ELSE 0 END) as retained
                FROM cohorts GROUP BY cohort_month ORDER BY cohort_month
            """))
            cohorts = []
            for r in result.fetchall():
                total, retained = int(r[1] or 0), int(r[2] or 0)
                cohorts.append({"cohort": r[0], "total": total, "retained": retained, "retention_rate": round(retained / total * 100, 1) if total > 0 else 0})
            return cohorts
        except Exception as e:
            logger.error(f"Error getting cohort: {e}")
            return []

    def obtener_arpa_por_tipo(self) -> List[Dict[str, Any]]:
        """Get ARPA by quota type."""
        try:
            result = self.db.execute(text("""
                SELECT COALESCE(tc.nombre, 'Sin tipo') as tipo, AVG(p.monto) as arpa
                FROM pagos p JOIN usuarios u ON p.usuario_id = u.id LEFT JOIN tipos_cuota tc ON u.tipo_cuota_id = tc.id
                WHERE p.fecha >= CURRENT_DATE - INTERVAL '3 months' GROUP BY tc.nombre ORDER BY arpa DESC
            """))
            return [{"tipo": r[0], "arpa": float(r[1] or 0)} for r in result.fetchall()]
        except Exception as e:
            logger.error(f"Error getting ARPA by type: {e}")
            return []

    def obtener_estado_pagos(self) -> Dict[str, int]:
        """Get payment status distribution."""
        try:
            al_dia = self.db.execute(text("""
                SELECT COUNT(DISTINCT u.id) FROM usuarios u JOIN pagos p ON u.id = p.usuario_id
                WHERE u.activo = TRUE AND p.fecha >= CURRENT_DATE - INTERVAL '35 days'
            """)).fetchone()[0] or 0
            
            vencido_result = self.db.execute(text("""
                SELECT COUNT(DISTINCT u.id) FROM usuarios u JOIN pagos p ON u.id = p.usuario_id
                WHERE u.activo = TRUE GROUP BY u.id HAVING MAX(p.fecha) < CURRENT_DATE - INTERVAL '35 days'
            """))
            vencido = len(vencido_result.fetchall())
            
            sin_pagos = self.db.execute(text("""
                SELECT COUNT(*) FROM usuarios u LEFT JOIN pagos p ON u.id = p.usuario_id WHERE u.activo = TRUE AND p.id IS NULL
            """)).fetchone()[0] or 0
            
            return {"al_dia": al_dia, "vencido": vencido, "sin_pagos": sin_pagos}
        except Exception as e:
            logger.error(f"Error getting payment status: {e}")
            return {"al_dia": 0, "vencido": 0, "sin_pagos": 0}

    def obtener_eventos_espera(self) -> List[Dict[str, Any]]:
        """Get recent waitlist events."""
        try:
            result = self.db.execute(text("""
                SELECT le.id, le.usuario_id, le.posicion, le.fecha_registro, u.nombre as usuario_nombre
                FROM lista_espera le JOIN usuarios u ON le.usuario_id = u.id ORDER BY le.fecha_registro DESC LIMIT 20
            """))
            return [{"id": r[0], "usuario_nombre": r[4], "posicion": r[2], "fecha": r[3].isoformat() if r[3] else None} for r in result.fetchall()]
        except Exception as e:
            logger.error(f"Error getting waitlist events: {e}")
            return []

    def obtener_alertas_morosidad(self) -> List[Dict[str, Any]]:
        """Get recent delinquency alerts."""
        try:
            result = self.db.execute(text("""
                SELECT u.id, u.nombre, MAX(p.fecha) as ultimo_pago FROM usuarios u LEFT JOIN pagos p ON u.id = p.usuario_id
                WHERE u.activo = FALSE AND (u.updated_at IS NULL OR u.updated_at >= CURRENT_DATE)
                GROUP BY u.id, u.nombre ORDER BY u.nombre LIMIT 20
            """))
            return [{"usuario_id": r[0], "usuario_nombre": r[1], "ultimo_pago": r[2].isoformat() if r[2] else None} for r in result.fetchall()]
        except Exception as e:
            logger.error(f"Error getting delinquency alerts: {e}")
            return []

    # ========== Exports ==========

    def exportar_usuarios(self) -> List[Dict[str, Any]]:
        """Export all users for CSV."""
        try:
            result = self.db.execute(text("SELECT id, nombre, dni, telefono, email, activo, rol, tipo_cuota_id, notas, created_at FROM usuarios ORDER BY nombre"))
            return [{"id": r[0], "nombre": r[1], "dni": r[2], "telefono": r[3], "email": r[4], "activo": r[5], "rol": r[6], "tipo_cuota_id": r[7], "notas": r[8], "created_at": r[9].isoformat() if r[9] else None} for r in result.fetchall()]
        except Exception as e:
            logger.error(f"Error exporting users: {e}")
            return []

    def exportar_pagos(self, desde: Optional[str] = None, hasta: Optional[str] = None) -> List[Dict[str, Any]]:
        """Export payments for CSV."""
        try:
            query = """
                SELECT p.id, p.usuario_id, u.nombre, p.monto, p.fecha, p.metodo_id, m.nombre as metodo, p.notas, p.created_at
                FROM pagos p LEFT JOIN usuarios u ON p.usuario_id = u.id LEFT JOIN metodos_pago m ON p.metodo_id = m.id WHERE 1=1
            """
            params = {}
            if desde: query += " AND p.fecha >= :desde"; params['desde'] = desde
            if hasta: query += " AND p.fecha <= :hasta"; params['hasta'] = hasta
            query += " ORDER BY p.fecha DESC"
            result = self.db.execute(text(query), params)
            return [{"id": r[0], "usuario_id": r[1], "usuario_nombre": r[2], "monto": float(r[3]) if r[3] else 0, "fecha": r[4].isoformat() if r[4] else None, "metodo_id": r[5], "metodo_nombre": r[6], "notas": r[7], "created_at": r[8].isoformat() if r[8] else None} for r in result.fetchall()]
        except Exception as e:
            logger.error(f"Error exporting payments: {e}")
            return []

    def exportar_asistencias(self, desde: Optional[str] = None, hasta: Optional[str] = None) -> List[Dict[str, Any]]:
        """Export attendance for CSV."""
        try:
            query = "SELECT a.id, a.usuario_id, u.nombre, a.created_at FROM asistencias a LEFT JOIN usuarios u ON a.usuario_id = u.id WHERE 1=1"
            params = {}
            if desde: query += " AND DATE(a.created_at) >= :desde"; params['desde'] = desde
            if hasta: query += " AND DATE(a.created_at) <= :hasta"; params['hasta'] = hasta
            query += " ORDER BY a.created_at DESC"
            result = self.db.execute(text(query), params)
            return [{"id": r[0], "usuario_id": r[1], "usuario_nombre": r[2], "created_at": r[3].isoformat() if r[3] else None} for r in result.fetchall()]
        except Exception as e:
            logger.error(f"Error exporting attendance: {e}")
            return []
