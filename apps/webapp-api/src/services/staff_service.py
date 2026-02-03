from __future__ import annotations

from datetime import datetime, date
from typing import Any, Dict, List, Optional

from sqlalchemy import select, func, text
from sqlalchemy.orm import Session

from src.services.base import BaseService
from src.models.orm_models import StaffProfile, StaffPermission, StaffSession, Usuario


class StaffService(BaseService):
    def __init__(self, db: Session):
        super().__init__(db)

    def _ensure_staff_profile(self, usuario_id: int) -> StaffProfile:
        uid = int(usuario_id)
        prof = self.db.scalars(
            select(StaffProfile).where(StaffProfile.usuario_id == uid)
        ).first()
        if prof is None:
            prof = StaffProfile(usuario_id=uid)
            self.db.add(prof)
            self.db.flush()
        return prof

    def list_staff(
        self,
        *,
        search: str = "",
        sucursal_id: Optional[int] = None,
        show_all: bool = False,
    ) -> List[Dict[str, Any]]:
        term = str(search or "").strip().lower()
        staff_like_roles = [
            "profesor",
            "empleado",
            "recepcionista",
            "staff",
            "admin",
            "administrador",
        ]
        roles = list({*staff_like_roles})
        stmt = (
            select(Usuario)
            .where(Usuario.rol.in_(roles))
            .order_by(Usuario.nombre.asc())
        )
        if not show_all and sucursal_id is not None:
            try:
                sid = int(sucursal_id)
            except Exception:
                sid = None
            if sid is not None and sid > 0:
                stmt = stmt.where(
                    text(
                        "EXISTS (SELECT 1 FROM usuario_sucursales us WHERE us.usuario_id = usuarios.id AND us.sucursal_id = :sid)"
                    )
                ).params(sid=sid)
        if term:
            like = f"%{term}%"
            stmt = stmt.where(
                func.lower(Usuario.nombre).like(like)
                | func.lower(Usuario.dni).like(like)
            )

        users = list(self.db.scalars(stmt).all())
        if not users:
            return []

        user_ids = [int(u.id) for u in users if getattr(u, "id", None) is not None]
        profiles = {
            int(p.usuario_id): p
            for p in self.db.scalars(
                select(StaffProfile).where(StaffProfile.usuario_id.in_(user_ids))
            ).all()
        }
        perms = {
            int(p.usuario_id): p
            for p in self.db.scalars(
                select(StaffPermission).where(StaffPermission.usuario_id.in_(user_ids))
            ).all()
        }

        branches_rows = (
            self.db.execute(
                text(
                    """
                    SELECT usuario_id, ARRAY_AGG(sucursal_id ORDER BY sucursal_id) AS sucursales
                    FROM usuario_sucursales
                    WHERE usuario_id = ANY(:ids)
                    GROUP BY usuario_id
                    """
                ),
                {"ids": user_ids},
            )
            .mappings()
            .all()
        )
        branch_map: Dict[int, List[int]] = {}
        for r in branches_rows or []:
            try:
                uid = int(r.get("usuario_id"))
            except Exception:
                continue
            arr = r.get("sucursales") or []
            out_ids: List[int] = []
            for x in arr:
                try:
                    out_ids.append(int(x))
                except Exception:
                    pass
            branch_map[uid] = out_ids

        out: List[Dict[str, Any]] = []
        for u in users:
            uid = int(u.id)
            prof = profiles.get(uid)
            perm = perms.get(uid)
            scopes_val = []
            if perm is not None:
                try:
                    scopes_val = list(perm.scopes or [])
                except Exception:
                    scopes_val = []
            out.append(
                {
                    "id": uid,
                    "nombre": u.nombre or "",
                    "dni": u.dni or "",
                    "email": getattr(u, "email", None) or "",
                    "rol": (u.rol or "").strip().lower(),
                    "activo": bool(u.activo),
                    "staff": {
                        "tipo": (getattr(prof, "tipo", None) or "").strip().lower() or None,
                        "estado": (getattr(prof, "estado", None) or "").strip().lower() or None,
                    }
                    if prof is not None
                    else None,
                    "sucursales": branch_map.get(uid, []),
                    "scopes": scopes_val,
                }
            )
        return out

    def get_staff_item(self, usuario_id: int) -> Optional[Dict[str, Any]]:
        uid = int(usuario_id)
        u = self.db.get(Usuario, uid)
        if not u:
            return None

        prof = self.db.scalars(
            select(StaffProfile).where(StaffProfile.usuario_id == uid)
        ).first()
        perm = self.db.scalars(
            select(StaffPermission).where(StaffPermission.usuario_id == uid)
        ).first()
        scopes_val: List[str] = []
        if perm is not None:
            try:
                scopes_val = list(perm.scopes or [])
            except Exception:
                scopes_val = []

        branch_rows = (
            self.db.execute(
                text(
                    "SELECT sucursal_id FROM usuario_sucursales WHERE usuario_id = :uid ORDER BY sucursal_id"
                ),
                {"uid": uid},
            )
            .scalars()
            .all()
        )
        sucursales: List[int] = []
        for x in branch_rows or []:
            try:
                sucursales.append(int(x))
            except Exception:
                pass

        return {
            "id": uid,
            "nombre": u.nombre or "",
            "dni": u.dni or "",
            "email": getattr(u, "email", None) or "",
            "rol": (u.rol or "").strip().lower(),
            "activo": bool(u.activo),
            "staff": {
                "tipo": (getattr(prof, "tipo", None) or "").strip().lower() or None,
                "estado": (getattr(prof, "estado", None) or "").strip().lower() or None,
            }
            if prof is not None
            else None,
            "sucursales": sucursales,
            "scopes": scopes_val,
        }

    def upsert_staff_profile(
        self, usuario_id: int, *, tipo: Optional[str] = None, estado: Optional[str] = None
    ) -> None:
        prof = self.db.scalars(
            select(StaffProfile).where(StaffProfile.usuario_id == int(usuario_id))
        ).first()
        if prof is None:
            prof = StaffProfile(usuario_id=int(usuario_id))
            self.db.add(prof)
        if tipo is not None:
            prof.tipo = str(tipo or "").strip().lower() or "empleado"
        if estado is not None:
            prof.estado = str(estado or "").strip().lower() or "activo"
        try:
            prof.fecha_actualizacion = datetime.utcnow()
        except Exception:
            pass

    def set_user_role(self, usuario_id: int, rol: str) -> None:
        u = self.db.get(Usuario, int(usuario_id))
        if not u:
            raise ValueError("Usuario no encontrado")
        u.rol = str(rol or "").strip().lower() or "empleado"

    def set_user_active(self, usuario_id: int, activo: bool) -> None:
        u = self.db.get(Usuario, int(usuario_id))
        if not u:
            raise ValueError("Usuario no encontrado")
        u.activo = bool(activo)

    def set_user_branches(self, usuario_id: int, sucursal_ids: List[int]) -> None:
        uid = int(usuario_id)
        clean: List[int] = []
        for sid in sucursal_ids or []:
            try:
                iv = int(sid)
            except Exception:
                continue
            if iv > 0 and iv not in clean:
                clean.append(iv)
        self.db.execute(text("DELETE FROM usuario_sucursales WHERE usuario_id = :uid"), {"uid": uid})
        for sid in clean:
            self.db.execute(
                text("INSERT INTO usuario_sucursales(usuario_id, sucursal_id) VALUES (:uid, :sid)"),
                {"uid": uid, "sid": sid},
            )

    def set_scopes(self, usuario_id: int, scopes: List[str]) -> None:
        uid = int(usuario_id)
        clean: List[str] = []
        for s in scopes or []:
            st = str(s or "").strip()
            if st and st not in clean:
                clean.append(st)
        self.db.execute(
            text(
                """
                INSERT INTO staff_permissions(usuario_id, scopes, updated_at)
                VALUES (:uid, :scopes::jsonb, NOW())
                ON CONFLICT (usuario_id)
                DO UPDATE SET scopes = EXCLUDED.scopes, updated_at = NOW()
                """
            ),
            {"uid": uid, "scopes": json_dumps(clean)},
        )

    def start_session(self, usuario_id: int, sucursal_id: Optional[int]) -> int:
        uid = int(usuario_id)
        prof = self.db.scalars(
            select(StaffProfile).where(StaffProfile.usuario_id == uid)
        ).first()
        if prof is None:
            prof = StaffProfile(usuario_id=uid)
            self.db.add(prof)
            self.db.flush()
        now = datetime.utcnow()
        today = date.today()
        existing = self.db.scalars(
            select(StaffSession).where(
                StaffSession.staff_id == int(prof.id), StaffSession.hora_fin.is_(None)
            )
        ).first()
        if existing is not None:
            return int(existing.id)
        sess = StaffSession(
            staff_id=int(prof.id),
            sucursal_id=int(sucursal_id) if sucursal_id else None,
            fecha=today,
            hora_inicio=now,
        )
        self.db.add(sess)
        self.db.flush()
        return int(sess.id)

    def end_session(self, usuario_id: int) -> bool:
        uid = int(usuario_id)
        prof = self.db.scalars(
            select(StaffProfile).where(StaffProfile.usuario_id == uid)
        ).first()
        if prof is None:
            return False
        sess = self.db.scalars(
            select(StaffSession).where(
                StaffSession.staff_id == int(prof.id), StaffSession.hora_fin.is_(None)
            )
        ).first()
        if sess is None:
            return False
        now = datetime.utcnow()
        try:
            self.db.execute(
                text(
                    """
                    UPDATE work_session_pauses
                    SET ended_at = :now
                    WHERE session_kind = 'staff' AND session_id = :sid AND ended_at IS NULL
                    """
                ),
                {"now": now, "sid": int(sess.id)},
            )
        except Exception:
            pass
        sess.hora_fin = now
        try:
            paused_seconds = 0
            try:
                rows = (
                    self.db.execute(
                        text(
                            """
                            SELECT started_at, ended_at
                            FROM work_session_pauses
                            WHERE session_kind = 'staff' AND session_id = :sid
                            ORDER BY started_at ASC
                            """
                        ),
                        {"sid": int(sess.id)},
                    )
                    .fetchall()
                    or []
                )
                for r in rows:
                    try:
                        st = r[0]
                        en = r[1]
                        if st and en:
                            paused_seconds += int((en - st).total_seconds())
                    except Exception:
                        pass
            except Exception:
                paused_seconds = 0
            total_seconds = int((now - sess.hora_inicio).total_seconds())
            effective = max(0, total_seconds - int(paused_seconds))
            mins = int(effective // 60)
            sess.minutos_totales = mins
        except Exception:
            pass
        return True

    def list_sessions(
        self,
        usuario_id: int,
        *,
        desde: Optional[str] = None,
        hasta: Optional[str] = None,
        page: int = 1,
        limit: int = 50,
    ) -> Dict[str, Any]:
        uid = int(usuario_id)
        prof = self.db.scalars(
            select(StaffProfile).where(StaffProfile.usuario_id == uid)
        ).first()
        if prof is None:
            return {"items": [], "total": 0, "page": int(page), "limit": int(limit)}

        try:
            p = int(page or 1)
        except Exception:
            p = 1
        if p < 1:
            p = 1
        try:
            lim = int(limit or 50)
        except Exception:
            lim = 50
        if lim < 1:
            lim = 1
        if lim > 200:
            lim = 200
        offset = (p - 1) * lim

        where = ["staff_id = :sid"]
        params: Dict[str, Any] = {"sid": int(prof.id), "limit": lim, "offset": offset}
        if desde:
            where.append("fecha >= :desde")
            params["desde"] = str(desde)
        if hasta:
            where.append("fecha <= :hasta")
            params["hasta"] = str(hasta)
        where_sql = " AND ".join(where)

        total = (
            self.db.execute(
                text(f"SELECT COUNT(*) FROM staff_sessions WHERE {where_sql}"), params
            ).scalar()
            or 0
        )
        rows = (
            self.db.execute(
                text(
                    f"""
                    SELECT id, staff_id, sucursal_id, fecha, hora_inicio, hora_fin, minutos_totales, notas
                    FROM staff_sessions
                    WHERE {where_sql}
                    ORDER BY COALESCE(hora_inicio, fecha) DESC, id DESC
                    LIMIT :limit OFFSET :offset
                    """
                ),
                params,
            )
            .mappings()
            .all()
        )
        items: List[Dict[str, Any]] = []
        for r in rows or []:
            items.append(
                {
                    "id": int(r.get("id")),
                    "usuario_id": uid,
                    "staff_id": int(r.get("staff_id")),
                    "sucursal_id": r.get("sucursal_id"),
                    "fecha": str(r.get("fecha")) if r.get("fecha") else None,
                    "inicio": str(r.get("hora_inicio")) if r.get("hora_inicio") else None,
                    "fin": str(r.get("hora_fin")) if r.get("hora_fin") else None,
                    "minutos": int(r.get("minutos_totales") or 0),
                    "notas": r.get("notas"),
                }
            )
        return {"items": items, "total": int(total), "page": int(p), "limit": int(lim)}

    def get_active_session(self, usuario_id: int) -> Optional[Dict[str, Any]]:
        uid = int(usuario_id)
        prof = self.db.scalars(
            select(StaffProfile).where(StaffProfile.usuario_id == uid)
        ).first()
        if prof is None:
            return None
        sess = self.db.scalars(
            select(StaffSession).where(
                StaffSession.staff_id == int(prof.id), StaffSession.hora_fin.is_(None)
            )
        ).first()
        if sess is None:
            return None
        return {
            "id": int(sess.id),
            "usuario_id": uid,
            "staff_id": int(prof.id),
            "sucursal_id": getattr(sess, "sucursal_id", None),
            "fecha": sess.fecha.isoformat() if getattr(sess, "fecha", None) else None,
            "inicio": str(getattr(sess, "hora_inicio", None) or ""),
            "fin": None,
            "minutos": int(getattr(sess, "minutos_totales", None) or 0),
            "notas": getattr(sess, "notas", None),
        }

    def create_session(
        self,
        usuario_id: int,
        *,
        sucursal_id: Optional[int],
        hora_inicio: datetime,
        hora_fin: Optional[datetime],
        notas: Optional[str] = None,
    ) -> int:
        prof = self._ensure_staff_profile(int(usuario_id))
        sess = StaffSession(
            staff_id=int(prof.id),
            sucursal_id=int(sucursal_id) if sucursal_id else None,
            fecha=date.fromisoformat(hora_inicio.date().isoformat()),
            hora_inicio=hora_inicio,
            hora_fin=hora_fin,
            notas=notas,
        )
        if hora_fin is not None:
            try:
                mins = int((hora_fin - hora_inicio).total_seconds() // 60)
                sess.minutos_totales = max(0, mins)
            except Exception:
                pass
        self.db.add(sess)
        self.db.flush()
        return int(sess.id)

    def update_session(
        self,
        sesion_id: int,
        *,
        sucursal_id: Optional[int] = None,
        hora_inicio: Optional[datetime] = None,
        hora_fin: Optional[datetime] = None,
        notas: Optional[str] = None,
    ) -> bool:
        sess = self.db.get(StaffSession, int(sesion_id))
        if sess is None:
            return False
        if sucursal_id is not None:
            sess.sucursal_id = int(sucursal_id) if sucursal_id else None
        if hora_inicio is not None:
            sess.hora_inicio = hora_inicio
            sess.fecha = date.fromisoformat(hora_inicio.date().isoformat())
        if hora_fin is not None:
            sess.hora_fin = hora_fin
        if notas is not None:
            sess.notas = notas
        try:
            if sess.hora_inicio and sess.hora_fin:
                mins = int((sess.hora_fin - sess.hora_inicio).total_seconds() // 60)
                sess.minutos_totales = max(0, mins)
        except Exception:
            pass
        return True

    def delete_session(self, sesion_id: int) -> bool:
        sess = self.db.get(StaffSession, int(sesion_id))
        if sess is None:
            return False
        self.db.delete(sess)
        return True

    def commit(self) -> None:
        self.db.commit()


def json_dumps(value: Any) -> str:
    import json

    try:
        return json.dumps(value, ensure_ascii=False)
    except Exception:
        return "[]"
