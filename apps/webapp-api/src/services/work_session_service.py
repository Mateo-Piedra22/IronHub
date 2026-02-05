from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone, date
from typing import Any, Dict, Optional, Tuple

try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from src.models.orm_models import (
    Profesor,
    ProfesorHoraTrabajada,
    StaffProfile,
    StaffSession,
    WorkSessionPause,
)


class WorkSessionService:
    def __init__(self, db: Session):
        self.db = db

    def _now_utc_naive(self) -> datetime:
        return datetime.now(timezone.utc).replace(tzinfo=None)

    def _today_local_date(self) -> date:
        tz_name = (
            os.getenv("APP_TIMEZONE")
            or os.getenv("TIMEZONE")
            or os.getenv("TZ")
            or "America/Argentina/Buenos_Aires"
        )
        tz = None
        if ZoneInfo is not None:
            try:
                tz = ZoneInfo(tz_name)
            except Exception:
                tz = None
        if tz is None:
            tz = timezone(timedelta(hours=-3))
        return datetime.now(timezone.utc).astimezone(tz).date()

    def _resolve_profesor_id(
        self, *, user_id: int, session_profesor_id: Optional[int]
    ) -> Optional[int]:
        if session_profesor_id is not None:
            try:
                pid = int(session_profesor_id)
                if pid > 0:
                    return pid
            except Exception:
                pass
        try:
            pid = (
                self.db.execute(
                    select(Profesor.id)
                    .where(Profesor.usuario_id == int(user_id))
                    .limit(1)
                )
                .scalars()
                .first()
            )
            return int(pid) if pid is not None else None
        except Exception:
            return None

    def _resolve_staff_profile(self, user_id: int) -> Optional[StaffProfile]:
        uid = int(user_id)
        prof = self.db.scalars(
            select(StaffProfile).where(StaffProfile.usuario_id == uid)
        ).first()
        if prof is None:
            return None
        estado = str(getattr(prof, "estado", "") or "").strip().lower()
        if estado == "inactivo":
            return None
        return prof

    def _get_active_profesor_session(
        self, profesor_id: int
    ) -> Optional[ProfesorHoraTrabajada]:
        return (
            self.db.scalars(
                select(ProfesorHoraTrabajada)
                .where(
                    ProfesorHoraTrabajada.profesor_id == int(profesor_id),
                    ProfesorHoraTrabajada.hora_fin.is_(None),
                )
                .order_by(ProfesorHoraTrabajada.hora_inicio.desc())
                .limit(1)
            ).first()
            if profesor_id
            else None
        )

    def _get_active_staff_session(self, staff_profile_id: int) -> Optional[StaffSession]:
        return (
            self.db.scalars(
                select(StaffSession)
                .where(
                    StaffSession.staff_id == int(staff_profile_id),
                    StaffSession.hora_fin.is_(None),
                )
                .order_by(StaffSession.hora_inicio.desc())
                .limit(1)
            ).first()
            if staff_profile_id
            else None
        )

    def _pause_state(
        self, *, kind: str, session_id: int, now: datetime
    ) -> Tuple[bool, Optional[datetime], int]:
        paused_row = self.db.scalars(
            select(WorkSessionPause)
            .where(
                WorkSessionPause.session_kind == str(kind),
                WorkSessionPause.session_id == int(session_id),
                WorkSessionPause.ended_at.is_(None),
            )
            .limit(1)
        ).first()
        paused = paused_row is not None
        paused_since = paused_row.started_at if paused_row is not None else None

        total_paused = 0
        rows = self.db.scalars(
            select(WorkSessionPause)
            .where(
                WorkSessionPause.session_kind == str(kind),
                WorkSessionPause.session_id == int(session_id),
            )
            .order_by(WorkSessionPause.started_at.asc())
        ).all()
        for r in rows or []:
            if r.ended_at is not None:
                total_paused += int((r.ended_at - r.started_at).total_seconds())
            elif r.started_at is not None:
                total_paused += int((now - r.started_at).total_seconds())
        return paused, paused_since, total_paused

    def get_my_state(
        self,
        *,
        role: str,
        user_id: Optional[int],
        session_profesor_id: Optional[int],
    ) -> Dict[str, Any]:
        if not user_id:
            return {"ok": False, "allowed": False}
        r = str(role or "").strip().lower()
        if r in ("dueño", "dueno", "owner", "admin", "administrador"):
            return {"ok": True, "allowed": False, "kind": None}
        kind = "profesor" if r == "profesor" else "staff"
        now = self._now_utc_naive()

        if kind == "profesor":
            pid = self._resolve_profesor_id(
                user_id=int(user_id), session_profesor_id=session_profesor_id
            )
            if not pid:
                return {"ok": True, "allowed": False, "kind": "profesor"}
            sess = self._get_active_profesor_session(int(pid))
            if not sess:
                return {"ok": True, "allowed": True, "kind": "profesor", "active": None}
            paused, paused_since, paused_seconds = self._pause_state(
                kind="profesor", session_id=int(sess.id), now=now
            )
            elapsed = int((now - sess.hora_inicio).total_seconds())
            effective = max(0, elapsed - int(paused_seconds))
            return {
                "ok": True,
                "allowed": True,
                "kind": "profesor",
                "active": {
                    "session_id": int(sess.id),
                    "profesor_id": int(pid),
                    "sucursal_id": getattr(sess, "sucursal_id", None),
                    "started_at": sess.hora_inicio.isoformat() if sess.hora_inicio else None,
                    "paused": bool(paused),
                    "paused_since": paused_since.isoformat() if paused_since else None,
                    "elapsed_seconds": int(elapsed),
                    "effective_elapsed_seconds": int(effective),
                },
            }

        prof = self._resolve_staff_profile(int(user_id))
        if not prof:
            return {"ok": True, "allowed": False, "kind": "staff"}
        sess = self._get_active_staff_session(int(prof.id))
        if not sess:
            return {"ok": True, "allowed": True, "kind": "staff", "active": None}
        paused, paused_since, paused_seconds = self._pause_state(
            kind="staff", session_id=int(sess.id), now=now
        )
        elapsed = int((now - sess.hora_inicio).total_seconds())
        effective = max(0, elapsed - int(paused_seconds))
        return {
            "ok": True,
            "allowed": True,
            "kind": "staff",
            "active": {
                "session_id": int(sess.id),
                "staff_profile_id": int(prof.id),
                "sucursal_id": getattr(sess, "sucursal_id", None),
                "started_at": sess.hora_inicio.isoformat() if sess.hora_inicio else None,
                "paused": bool(paused),
                "paused_since": paused_since.isoformat() if paused_since else None,
                "elapsed_seconds": int(elapsed),
                "effective_elapsed_seconds": int(effective),
            },
        }

    def start_my_session(
        self,
        *,
        role: str,
        user_id: Optional[int],
        session_profesor_id: Optional[int],
        sucursal_id: Optional[int],
    ) -> Dict[str, Any]:
        if not user_id:
            return {"ok": False, "error": "Unauthorized"}
        r = str(role or "").strip().lower()
        if r in ("dueño", "dueno", "owner", "admin", "administrador"):
            return {"ok": False, "error": "Forbidden"}
        kind = "profesor" if r == "profesor" else "staff"
        now = self._now_utc_naive()

        if kind == "profesor":
            pid = self._resolve_profesor_id(
                user_id=int(user_id), session_profesor_id=session_profesor_id
            )
            if not pid:
                return {"ok": False, "error": "Profesor no encontrado"}
            fecha_local = self._today_local_date()
            row = self.db.execute(
                text(
                    """
                    INSERT INTO profesor_horas_trabajadas (profesor_id, sucursal_id, fecha, hora_inicio, hora_fin)
                    VALUES (:pid, :sid, :fecha, :inicio, NULL)
                    ON CONFLICT (profesor_id) WHERE hora_fin IS NULL DO NOTHING
                    RETURNING id, hora_inicio, sucursal_id
                    """
                ),
                {
                    "pid": int(pid),
                    "sid": int(sucursal_id) if sucursal_id else None,
                    "fecha": fecha_local,
                    "inicio": now,
                },
            ).fetchone()
            if row:
                self.db.commit()
                return {
                    "ok": True,
                    "kind": "profesor",
                    "session_id": int(row[0]),
                    "started_at": (row[1] or now).isoformat(),
                    "sucursal_id": row[2],
                    "already_active": False,
                }
            active = self._get_active_profesor_session(int(pid))
            if not active:
                self.db.rollback()
                return {"ok": False, "error": "No se pudo iniciar la sesión"}
            return {
                "ok": True,
                "kind": "profesor",
                "session_id": int(active.id),
                "started_at": active.hora_inicio.isoformat() if active.hora_inicio else None,
                "sucursal_id": getattr(active, "sucursal_id", None),
                "already_active": True,
            }

        prof = self._resolve_staff_profile(int(user_id))
        if not prof:
            return {"ok": False, "error": "Staff no encontrado"}
        existing = self._get_active_staff_session(int(prof.id))
        if existing is not None:
            return {
                "ok": True,
                "kind": "staff",
                "session_id": int(existing.id),
                "started_at": existing.hora_inicio.isoformat() if existing.hora_inicio else None,
                "sucursal_id": getattr(existing, "sucursal_id", None),
                "already_active": True,
            }
        sess = StaffSession(
            staff_id=int(prof.id),
            sucursal_id=int(sucursal_id) if sucursal_id else None,
            fecha=self._today_local_date(),
            hora_inicio=now,
        )
        self.db.add(sess)
        self.db.commit()
        self.db.refresh(sess)
        return {
            "ok": True,
            "kind": "staff",
            "session_id": int(sess.id),
            "started_at": sess.hora_inicio.isoformat() if sess.hora_inicio else None,
            "sucursal_id": getattr(sess, "sucursal_id", None),
            "already_active": False,
        }

    def pause_my_session(
        self,
        *,
        role: str,
        user_id: Optional[int],
        session_profesor_id: Optional[int],
    ) -> Dict[str, Any]:
        st = self.get_my_state(
            role=role, user_id=user_id, session_profesor_id=session_profesor_id
        )
        active = (st or {}).get("active")
        if not st.get("allowed") or not active:
            return {"ok": False, "error": "No hay sesión activa"}
        if active.get("paused"):
            return {"ok": True, "already_paused": True}
        now = self._now_utc_naive()
        self.db.add(
            WorkSessionPause(
                session_kind=str(st.get("kind")),
                session_id=int(active.get("session_id")),
                started_at=now,
            )
        )
        self.db.commit()
        return {"ok": True}

    def resume_my_session(
        self,
        *,
        role: str,
        user_id: Optional[int],
        session_profesor_id: Optional[int],
    ) -> Dict[str, Any]:
        st = self.get_my_state(
            role=role, user_id=user_id, session_profesor_id=session_profesor_id
        )
        active = (st or {}).get("active")
        if not st.get("allowed") or not active:
            return {"ok": False, "error": "No hay sesión activa"}
        if not active.get("paused"):
            return {"ok": True, "already_running": True}
        now = self._now_utc_naive()
        row = self.db.scalars(
            select(WorkSessionPause)
            .where(
                WorkSessionPause.session_kind == str(st.get("kind")),
                WorkSessionPause.session_id == int(active.get("session_id")),
                WorkSessionPause.ended_at.is_(None),
            )
            .limit(1)
        ).first()
        if row is None:
            return {"ok": True, "already_running": True}
        row.ended_at = now
        self.db.commit()
        return {"ok": True}

    def end_my_session(
        self,
        *,
        role: str,
        user_id: Optional[int],
        session_profesor_id: Optional[int],
    ) -> Dict[str, Any]:
        st = self.get_my_state(
            role=role, user_id=user_id, session_profesor_id=session_profesor_id
        )
        active = (st or {}).get("active")
        if not st.get("allowed") or not active:
            return {"ok": False, "error": "No hay sesión activa"}
        kind = str(st.get("kind"))
        sid = int(active.get("session_id"))
        now = self._now_utc_naive()

        row = self.db.scalars(
            select(WorkSessionPause)
            .where(
                WorkSessionPause.session_kind == kind,
                WorkSessionPause.session_id == sid,
                WorkSessionPause.ended_at.is_(None),
            )
            .limit(1)
        ).first()
        if row is not None:
            row.ended_at = now

        paused, _, paused_seconds = self._pause_state(kind=kind, session_id=sid, now=now)
        try:
            if kind == "profesor":
                sess = self.db.get(ProfesorHoraTrabajada, sid)
                if not sess or sess.hora_fin is not None:
                    self.db.rollback()
                    return {"ok": False, "error": "Sesión no encontrada"}
                sess.hora_fin = now
                total = int((now - sess.hora_inicio).total_seconds())
                effective = max(0, total - int(paused_seconds))
                mins = int(effective // 60)
                sess.minutos_totales = mins
                sess.horas_totales = round(mins / 60.0, 2)
                self.db.commit()
                return {"ok": True, "minutos": mins}

            sess = self.db.get(StaffSession, sid)
            if not sess or sess.hora_fin is not None:
                self.db.rollback()
                return {"ok": False, "error": "Sesión no encontrada"}
            sess.hora_fin = now
            total = int((now - sess.hora_inicio).total_seconds())
            effective = max(0, total - int(paused_seconds))
            mins = int(effective // 60)
            sess.minutos_totales = mins
            self.db.commit()
            return {"ok": True, "minutos": mins}
        except Exception as e:
            self.db.rollback()
            return {"ok": False, "error": str(e)}
