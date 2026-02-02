from typing import List, Optional, Dict, Any, Tuple, Set
from datetime import datetime, date, timedelta, timezone
import os

try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None
from sqlalchemy import select, func, text
from .base import BaseRepository
from ..orm_models import (
    Asistencia,
    Usuario,
    CheckinPending,
    Pago,
    ClaseAsistenciaHistorial,
)


class AttendanceRepository(BaseRepository):
    def _get_app_timezone(self):
        tz_name = (
            os.getenv("APP_TIMEZONE")
            or os.getenv("TIMEZONE")
            or os.getenv("TZ")
            or "America/Argentina/Buenos_Aires"
        )
        if ZoneInfo is not None:
            try:
                return ZoneInfo(tz_name)
            except Exception:
                pass
        return timezone(timedelta(hours=-3))

    def _now_utc_naive(self) -> datetime:
        return datetime.now(timezone.utc).replace(tzinfo=None)

    def _now_local(self) -> datetime:
        tz = self._get_app_timezone()
        return datetime.now(timezone.utc).astimezone(tz)

    def _today_local_date(self) -> date:
        return self._now_local().date()

    def registrar_asistencia_comun(
        self,
        usuario_id: int,
        fecha: date,
        *,
        allow_multiple: bool = False,
        sucursal_id: Optional[int] = None,
    ) -> int:
        user = self.db.get(Usuario, usuario_id)
        if not user:
            raise PermissionError(
                "El usuario está inactivo: no se puede registrar asistencia"
            )

        rol = str(getattr(user, "rol", "") or "").strip().lower()
        exento = rol in ("profesor", "dueño", "dueno", "owner")
        activo = (
            bool(user.activo) if getattr(user, "activo", None) is not None else True
        )
        if (not exento) and (not activo):
            raise PermissionError(
                "El usuario está inactivo: no se puede registrar asistencia"
            )

        now = self._now_utc_naive()
        sid = int(sucursal_id) if sucursal_id is not None else None

        if bool(allow_multiple):
            asistencia = Asistencia(
                usuario_id=usuario_id,
                fecha=fecha,
                hora_registro=now,
                sucursal_id=sid,
            )
            self.db.add(asistencia)
            self.db.commit()
            self.db.refresh(asistencia)
            self._invalidate_cache("asistencias")
            return asistencia.id

        if sid is None:
            row = self.db.execute(
                text(
                    """
                    INSERT INTO asistencias (usuario_id, sucursal_id, fecha, hora_registro)
                    SELECT :uid, NULL, :f, :hr
                    WHERE NOT EXISTS (
                        SELECT 1 FROM asistencias
                        WHERE usuario_id = :uid AND fecha = :f AND sucursal_id IS NULL
                    )
                    RETURNING id
                    """
                ),
                {"uid": int(usuario_id), "f": fecha, "hr": now},
            ).fetchone()
        else:
            row = self.db.execute(
                text(
                    """
                    INSERT INTO asistencias (usuario_id, sucursal_id, fecha, hora_registro)
                    SELECT :uid, :sid, :f, :hr
                    WHERE NOT EXISTS (
                        SELECT 1 FROM asistencias
                        WHERE usuario_id = :uid AND fecha = :f AND sucursal_id = :sid
                    )
                    RETURNING id
                    """
                ),
                {"uid": int(usuario_id), "sid": sid, "f": fecha, "hr": now},
            ).fetchone()

        if not row:
            raise ValueError(
                f"Ya existe una asistencia registrada para este usuario en la fecha {fecha}"
            )
        self.db.commit()
        self._invalidate_cache("asistencias")
        return int(row[0])

    def obtener_ids_asistencia_hoy(self) -> Set[int]:
        hoy = self._today_local_date()
        stmt = select(Asistencia.usuario_id).where(Asistencia.fecha == hoy)
        return set(self.db.scalars(stmt).all())

    def obtener_asistencias_por_fecha(self, fecha) -> List[Dict]:
        if isinstance(fecha, str):
            try:
                fecha = datetime.fromisoformat(fecha).date()
            except:
                pass

        stmt = (
            select(Asistencia, Usuario)
            .join(Usuario)
            .where(Asistencia.fecha == fecha)
            .order_by(Asistencia.hora_registro.desc())
        )
        results = self.db.execute(stmt).all()

        return [
            {
                "id": a.id,
                "usuario_id": a.usuario_id,
                "nombre_usuario": u.nombre,
                "dni_usuario": u.dni,
                "fecha": a.fecha,
                "hora_registro": a.hora_registro,
            }
            for a, u in results
        ]

    def registrar_asistencia(
        self,
        usuario_id: int,
        fecha: date = None,
        *,
        allow_multiple: bool = False,
        sucursal_id: Optional[int] = None,
    ) -> int:
        if fecha is None:
            fecha = self._today_local_date()
        return self.registrar_asistencia_comun(
            usuario_id, fecha, allow_multiple=allow_multiple, sucursal_id=sucursal_id
        )

    def registrar_asistencias_batch(
        self, asistencias: List[Dict[str, Any]], *, allow_multiple: bool = False
    ) -> Dict[str, Any]:
        result = {"insertados": [], "omitidos": [], "count": 0}
        now = self._now_utc_naive()

        for item in asistencias:
            try:
                uid = int(item.get("usuario_id"))
                f = item.get("fecha")
                if not f:
                    f = self._today_local_date()
                elif isinstance(f, str):
                    f = datetime.fromisoformat(f).date()

                user = self.db.get(Usuario, uid)
                if not user or not user.activo:
                    result["omitidos"].append(
                        {"usuario_id": uid, "fecha": f, "motivo": "usuario inactivo"}
                    )
                    continue

                if not bool(allow_multiple):
                    try:
                        lock = self.db.execute(
                            text(
                                """
                                INSERT INTO asistencias_diarias (usuario_id, fecha)
                                VALUES (:uid, :f)
                                ON CONFLICT DO NOTHING
                                RETURNING 1
                                """
                            ),
                            {"uid": int(uid), "f": f},
                        ).fetchone()
                        if not lock:
                            result["omitidos"].append(
                                {"usuario_id": uid, "fecha": f, "motivo": "duplicado"}
                            )
                            continue
                    except Exception:
                        existing = self.db.scalar(
                            select(Asistencia).where(
                                Asistencia.usuario_id == uid, Asistencia.fecha == f
                            )
                        )
                        if existing:
                            result["omitidos"].append(
                                {"usuario_id": uid, "fecha": f, "motivo": "duplicado"}
                            )
                            continue

                new_a = Asistencia(usuario_id=uid, fecha=f, hora_registro=now)
                self.db.add(new_a)
                self.db.flush()
                result["insertados"].append(new_a.id)

            except Exception as e:
                result["omitidos"].append(
                    {"usuario_id": item.get("usuario_id"), "motivo": str(e)}
                )

        self.db.commit()
        result["count"] = len(result["insertados"])
        self._invalidate_cache("asistencias")
        return result

    def crear_checkin_token(
        self,
        usuario_id: int,
        token: str,
        expires_minutes: int = 5,
        sucursal_id: Optional[int] = None,
    ) -> int:
        user = self.db.get(Usuario, usuario_id)
        if not user:
            raise PermissionError("El usuario está inactivo")

        rol = str(getattr(user, "rol", "") or "").strip().lower()
        exento = rol in ("profesor", "dueño", "dueno", "owner")
        activo = (
            bool(user.activo) if getattr(user, "activo", None) is not None else True
        )
        if (not exento) and (not activo):
            raise PermissionError("El usuario está inactivo")

        expires_at = self._now_utc_naive() + timedelta(minutes=expires_minutes)
        cp = CheckinPending(
            usuario_id=usuario_id,
            token=token,
            expires_at=expires_at,
            sucursal_id=int(sucursal_id) if sucursal_id is not None else None,
        )
        self.db.add(cp)
        self.db.commit()
        self.db.refresh(cp)
        return cp.id

    def obtener_checkin_por_token(self, token: str) -> Optional[Dict]:
        cp = self.db.scalar(select(CheckinPending).where(CheckinPending.token == token))
        if cp:
            return {
                "id": cp.id,
                "usuario_id": cp.usuario_id,
                "token": cp.token,
                "created_at": cp.created_at,
                "expires_at": cp.expires_at,
                "used": cp.used,
                "sucursal_id": getattr(cp, "sucursal_id", None),
            }
        return None

    def marcar_checkin_usado(self, token: str) -> None:
        cp = self.db.scalar(select(CheckinPending).where(CheckinPending.token == token))
        if cp:
            cp.used = True
            self.db.commit()

    def validar_token_y_registrar_asistencia(
        self, token: str, socio_id: int
    ) -> Tuple[bool, str]:
        now = self._now_utc_naive()
        cp = self.db.scalar(select(CheckinPending).where(CheckinPending.token == token))

        if not cp:
            return (False, "Token inválido")
        if cp.used:
            return (False, "Token ya utilizado")
        if cp.expires_at <= now:
            return (False, "Token expirado")
        if cp.usuario_id != socio_id:
            return (False, "El token no corresponde al socio autenticado")

        try:
            self.registrar_asistencia(socio_id, self._today_local_date())
            cp.used = True
            self.db.commit()
            return (True, "Asistencia registrada")
        except ValueError:
            cp.used = True
            self.db.commit()
            return (True, "Asistencia ya registrada para hoy")  # Consider success
        except Exception as e:
            return (False, str(e))

    def obtener_asistencias_fecha(self, fecha: date) -> List[dict]:
        return self.obtener_asistencias_por_fecha(fecha)

    def eliminar_asistencia(self, asistencia_id: int):
        a = self.db.get(Asistencia, asistencia_id)
        if a:
            uid = int(a.usuario_id) if a.usuario_id is not None else None
            f = a.fecha
            self.db.delete(a)
            self.db.commit()
            self._invalidate_cache("asistencias")
            if uid is not None and f is not None:
                try:
                    remaining = int(
                        self.db.execute(
                            text(
                                "SELECT COUNT(*) FROM asistencias WHERE usuario_id = :uid AND fecha = :f"
                            ),
                            {"uid": uid, "f": f},
                        ).scalar()
                        or 0
                    )
                    if remaining == 0:
                        self.db.execute(
                            text(
                                "DELETE FROM asistencias_diarias WHERE usuario_id = :uid AND fecha = :f"
                            ),
                            {"uid": uid, "f": f},
                        )
                        self.db.commit()
                except Exception:
                    try:
                        self.db.rollback()
                    except Exception:
                        pass

    def obtener_estadisticas_asistencias(
        self, fecha_inicio: date = None, fecha_fin: date = None
    ) -> dict:
        if not fecha_inicio:
            fecha_inicio = date.today().replace(day=1)
        if not fecha_fin:
            fecha_fin = date.today()

        stmt = select(
            func.count(Asistencia.id),
            func.count(func.distinct(Asistencia.usuario_id)),
            func.count(func.distinct(Asistencia.fecha)),
        ).where(Asistencia.fecha.between(fecha_inicio, fecha_fin))
        row = self.db.execute(stmt).first()

        stats = {
            "periodo": {
                "fecha_inicio": fecha_inicio.isoformat(),
                "fecha_fin": fecha_fin.isoformat(),
            },
            "total_asistencias": row[0] or 0,
            "usuarios_unicos": row[1] or 0,
            "dias_con_asistencias": row[2] or 0,
            "promedio_diario": round(
                (row[0] or 0) / max((fecha_fin - fecha_inicio).days + 1, 1), 2
            ),
        }
        return stats

    def obtener_asistencias_por_dia(self, dias: int = 30):
        fecha_limite = self._today_local_date() - timedelta(days=dias)
        stmt = (
            select(Asistencia.fecha, func.count(Asistencia.id))
            .where(Asistencia.fecha >= fecha_limite)
            .group_by(Asistencia.fecha)
            .order_by(Asistencia.fecha)
        )
        return list(self.db.execute(stmt).all())

    # --- Class Attendance (Restored) ---

    def registrar_asistencia_clase(
        self,
        clase_horario_id: int,
        usuario_id: int,
        fecha_clase: date = None,
        estado: str = "presente",
        observaciones: str = None,
        registrado_por: int = None,
    ) -> int:
        if not fecha_clase:
            fecha_clase = self._today_local_date()

        existing = self.db.scalar(
            select(ClaseAsistenciaHistorial).where(
                ClaseAsistenciaHistorial.clase_horario_id == clase_horario_id,
                ClaseAsistenciaHistorial.usuario_id == usuario_id,
                ClaseAsistenciaHistorial.fecha_clase == fecha_clase,
            )
        )

        if existing:
            existing.estado_asistencia = estado
            existing.observaciones = observaciones
            existing.hora_llegada = self._now_local().time().replace(microsecond=0)
            existing.fecha_registro = self._now_utc_naive()
            self.db.commit()
            return existing.id

        hist = ClaseAsistenciaHistorial(
            clase_horario_id=clase_horario_id,
            usuario_id=usuario_id,
            fecha_clase=fecha_clase,
            estado_asistencia=estado,
            observaciones=observaciones,
            registrado_por=registrado_por,
            hora_llegada=self._now_local().time().replace(microsecond=0),
            fecha_registro=self._now_utc_naive(),
        )
        self.db.add(hist)
        self.db.commit()
        self.db.refresh(hist)
        return hist.id

    def obtener_historial_asistencia_clase(
        self, clase_horario_id: int, limit: int = 50
    ) -> List[Dict]:
        stmt = (
            select(ClaseAsistenciaHistorial, Usuario)
            .join(Usuario, ClaseAsistenciaHistorial.usuario_id == Usuario.id)
            .where(ClaseAsistenciaHistorial.clase_horario_id == clase_horario_id)
            .order_by(ClaseAsistenciaHistorial.fecha_clase.desc())
            .limit(limit)
        )

        results = self.db.execute(stmt).all()
        return [
            {
                "id": h.id,
                "usuario_id": h.usuario_id,
                "nombre_usuario": u.nombre,
                "fecha_clase": h.fecha_clase,
                "estado": h.estado_asistencia,
                "hora_llegada": h.hora_llegada,
            }
            for h, u in results
        ]

    # Legacy Income methods (kept for compatibility, using ORM)
    def calcular_ingresos_totales(self, fecha_inicio=None, fecha_fin=None) -> float:
        stmt = select(func.sum(Pago.monto))
        if fecha_inicio and fecha_fin:
            stmt = stmt.where(Pago.fecha_pago.between(fecha_inicio, fecha_fin))
        return float(self.db.scalar(stmt) or 0.0)

    def obtener_tendencia_ingresos(
        self, fecha_inicio=None, fecha_fin=None, periodo="6_meses"
    ) -> list:
        stmt = (
            select(
                func.to_char(Pago.fecha_pago, "YYYY-MM").label("mes"),
                func.sum(Pago.monto),
            )
            .group_by("mes")
            .order_by("mes")
        )

        if fecha_inicio and fecha_fin:
            stmt = stmt.where(Pago.fecha_pago.between(fecha_inicio, fecha_fin))

        results = self.db.execute(stmt).all()
        return [{"mes": r[0], "total_ingresos": float(r[1])} for r in results]
