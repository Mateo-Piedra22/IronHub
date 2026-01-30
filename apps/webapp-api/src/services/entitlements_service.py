import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy import text
from sqlalchemy.orm import Session


def _utcnow_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _env_flag(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return bool(default)
    try:
        s = str(v).strip().lower()
    except Exception:
        return bool(default)
    return s in ("1", "true", "t", "yes", "y", "on")


@dataclass(frozen=True)
class BranchAccess:
    all_sucursales: bool
    allowed_sucursal_ids: Tuple[int, ...]
    denied_sucursal_ids: Tuple[int, ...] = tuple()


@dataclass(frozen=True)
class EntitlementsSummary:
    branch_access: BranchAccess
    class_allowlist_enabled: bool
    allowed_tipo_clase_ids: Tuple[int, ...]
    allowed_clase_ids: Tuple[int, ...]


class EntitlementsService:
    def __init__(self, db: Session):
        self.db = db
        env_enabled = _env_flag("ENTITLEMENTS_V2_ENABLED", False)
        flag_enabled = False
        try:
            from src.services.feature_flags_service import FeatureFlagsService

            flag_enabled = bool(FeatureFlagsService(self.db).is_enabled("entitlements_v2"))
        except Exception:
            flag_enabled = False
        self._enabled = bool(env_enabled or flag_enabled)
        self._cache_ttl_s = int(os.getenv("ENTITLEMENTS_CACHE_TTL_SECONDS") or 15)
        self._cache: Dict[str, Tuple[float, Any]] = {}

    def _cache_get(self, key: str) -> Optional[Any]:
        cur = self._cache.get(key)
        if not cur:
            return None
        ts, val = cur
        if (time.time() - float(ts)) > float(self._cache_ttl_s):
            self._cache.pop(key, None)
            return None
        return val

    def _cache_set(self, key: str, val: Any) -> None:
        self._cache[key] = (time.time(), val)

    def is_enabled(self) -> bool:
        return bool(self._enabled)

    def _get_user_role(self, usuario_id: int) -> str:
        try:
            row = (
                self.db.execute(
                    text(
                        "SELECT LOWER(COALESCE(rol,'socio')) AS rol FROM usuarios WHERE id = :id LIMIT 1"
                    ),
                    {"id": int(usuario_id)},
                )
                .mappings()
                .first()
            )
            return str((row or {}).get("rol") or "socio").strip().lower()
        except Exception:
            return "socio"

    def _is_privileged_role(self, role: str) -> bool:
        r = str(role or "").strip().lower()
        return r in ("owner", "dueño", "dueno", "admin", "administrador", "profesor")

    def _get_user_tipo_cuota_id(self, usuario_id: int) -> Optional[int]:
        try:
            row = (
                self.db.execute(
                    text(
                        """
                        SELECT tc.id AS tipo_cuota_id
                        FROM usuarios u
                        JOIN tipos_cuota tc ON LOWER(tc.nombre) = LOWER(COALESCE(u.tipo_cuota,''))
                        WHERE u.id = :uid
                        LIMIT 1
                        """
                    ),
                    {"uid": int(usuario_id)},
                )
                .mappings()
                .first()
            )
            if not row:
                return None
            v = row.get("tipo_cuota_id")
            return int(v) if v is not None else None
        except Exception:
            return None

    def _get_plan_branch_access(self, tipo_cuota_id: int) -> Optional[BranchAccess]:
        try:
            tc = (
                self.db.execute(
                    text(
                        "SELECT all_sucursales FROM tipos_cuota WHERE id = :id LIMIT 1"
                    ),
                    {"id": int(tipo_cuota_id)},
                )
                .mappings()
                .first()
            )
            if not tc:
                return None
            all_suc = bool(tc.get("all_sucursales"))
            if all_suc:
                return BranchAccess(all_sucursales=True, allowed_sucursal_ids=tuple(), denied_sucursal_ids=tuple())
            rows = (
                self.db.execute(
                    text(
                        "SELECT sucursal_id FROM tipo_cuota_sucursales WHERE tipo_cuota_id = :id ORDER BY sucursal_id ASC"
                    ),
                    {"id": int(tipo_cuota_id)},
                )
                .fetchall()
            )
            allowed: List[int] = []
            for r in rows or []:
                try:
                    allowed.append(int(r[0]))
                except Exception:
                    pass
            return BranchAccess(all_sucursales=False, allowed_sucursal_ids=tuple(allowed), denied_sucursal_ids=tuple())
        except Exception:
            return None

    def _get_membership_branch_access(self, usuario_id: int) -> Optional[BranchAccess]:
        try:
            from src.services.membership_service import MembershipService

            ms = MembershipService(self.db)
            m = ms.get_active_membership(int(usuario_id))
            if not m:
                return None
            if bool(m.get("all_sucursales")):
                return BranchAccess(all_sucursales=True, allowed_sucursal_ids=tuple(), denied_sucursal_ids=tuple())
            mid = m.get("id")
            if not mid:
                return BranchAccess(all_sucursales=False, allowed_sucursal_ids=tuple(), denied_sucursal_ids=tuple())
            allowed = ms.get_membership_sucursales(int(mid))
            out = []
            for x in allowed or []:
                try:
                    out.append(int(x))
                except Exception:
                    pass
            return BranchAccess(all_sucursales=False, allowed_sucursal_ids=tuple(sorted(set(out))), denied_sucursal_ids=tuple())
        except Exception:
            return None

    def _get_user_branch_override(self, usuario_id: int, sucursal_id: int) -> Optional[Tuple[bool, str]]:
        try:
            now = _utcnow_naive()
            row = (
                self.db.execute(
                    text(
                        """
                        SELECT allow, motivo, starts_at, ends_at
                        FROM usuario_accesos_sucursales
                        WHERE usuario_id = :uid AND sucursal_id = :sid
                        ORDER BY id DESC
                        LIMIT 1
                        """
                    ),
                    {"uid": int(usuario_id), "sid": int(sucursal_id)},
                )
                .mappings()
                .first()
            )
            if not row:
                return None
            starts_at = row.get("starts_at")
            ends_at = row.get("ends_at")
            if starts_at and isinstance(starts_at, datetime) and starts_at > now:
                return None
            if ends_at and isinstance(ends_at, datetime) and ends_at < now:
                return None
            allow = bool(row.get("allow"))
            motivo = str(row.get("motivo") or "").strip()
            return allow, motivo
        except Exception:
            return None

    def _merge_branch_access(self, a: Optional[BranchAccess], b: Optional[BranchAccess]) -> Optional[BranchAccess]:
        if a is None and b is None:
            return None
        if a is None:
            return b
        if b is None:
            return a
        if a.all_sucursales and b.all_sucursales:
            da = set(a.denied_sucursal_ids)
            db = set(b.denied_sucursal_ids)
            return BranchAccess(all_sucursales=True, allowed_sucursal_ids=tuple(), denied_sucursal_ids=tuple(sorted(da.union(db))))
        if a.all_sucursales and (not b.all_sucursales):
            return b
        if b.all_sucursales and (not a.all_sucursales):
            return a
        sa = set(a.allowed_sucursal_ids)
        sb = set(b.allowed_sucursal_ids)
        inter = tuple(sorted(sa.intersection(sb)))
        return BranchAccess(all_sucursales=False, allowed_sucursal_ids=inter, denied_sucursal_ids=tuple())

    def get_effective_branch_access(self, usuario_id: int) -> Optional[BranchAccess]:
        if not self._enabled:
            return None
        cache_key = f"branches:{usuario_id}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        role = self._get_user_role(int(usuario_id))
        if self._is_privileged_role(role):
            out = BranchAccess(all_sucursales=True, allowed_sucursal_ids=tuple(), denied_sucursal_ids=tuple())
            self._cache_set(cache_key, out)
            return out

        tipo_cuota_id = self._get_user_tipo_cuota_id(int(usuario_id))
        plan_access = self._get_plan_branch_access(int(tipo_cuota_id)) if tipo_cuota_id else None
        membership_access = self._get_membership_branch_access(int(usuario_id))
        baseline = self._merge_branch_access(plan_access, membership_access)

        if baseline is None:
            self._cache_set(cache_key, None)
            return None

        rows = (
            self.db.execute(
                text(
                    """
                    SELECT sucursal_id, allow, motivo, starts_at, ends_at
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
        now = _utcnow_naive()
        overrides: Dict[int, Tuple[bool, str]] = {}
        for r in rows or []:
            sid = r.get("sucursal_id")
            if sid is None:
                continue
            try:
                sid_i = int(sid)
            except Exception:
                continue
            if sid_i in overrides:
                continue
            st = r.get("starts_at")
            en = r.get("ends_at")
            if st and isinstance(st, datetime) and st > now:
                continue
            if en and isinstance(en, datetime) and en < now:
                continue
            overrides[sid_i] = (bool(r.get("allow")), str(r.get("motivo") or "").strip())

        if baseline.all_sucursales:
            denied = {sid for sid, (allow, _m) in overrides.items() if allow is False}
            if not denied:
                out = baseline
            else:
                out = BranchAccess(all_sucursales=True, allowed_sucursal_ids=tuple(), denied_sucursal_ids=tuple(sorted(denied)))
            self._cache_set(cache_key, out)
            return out

        allowed = set(baseline.allowed_sucursal_ids)
        for sid, (allow, _m) in overrides.items():
            if allow:
                allowed.add(int(sid))
            else:
                allowed.discard(int(sid))
        out = BranchAccess(all_sucursales=False, allowed_sucursal_ids=tuple(sorted(allowed)), denied_sucursal_ids=tuple())
        self._cache_set(cache_key, out)
        return out

    def check_branch_access(self, usuario_id: int, sucursal_id: int) -> Tuple[Optional[bool], str]:
        if not self._enabled:
            return None, ""
        role = self._get_user_role(int(usuario_id))
        if self._is_privileged_role(role):
            return True, ""

        override = self._get_user_branch_override(int(usuario_id), int(sucursal_id))
        baseline = self.get_effective_branch_access(int(usuario_id))
        if baseline is None:
            return None, ""
        if override is not None:
            allow, motivo = override
            if allow:
                return True, motivo
            return False, motivo or "Sucursal no habilitada"

        if baseline.all_sucursales:
            denied = set(baseline.denied_sucursal_ids)
            if int(sucursal_id) in denied:
                return False, "Sucursal no habilitada"
            return True, ""
        if int(sucursal_id) in set(baseline.allowed_sucursal_ids):
            return True, ""
        return False, "Sucursal no habilitada"

    def _get_plan_class_rules(
        self, tipo_cuota_id: int, sucursal_id: Optional[int]
    ) -> Tuple[bool, Set[Tuple[str, int]], Set[Tuple[str, int]]]:
        try:
            rows = (
                self.db.execute(
                    text(
                        """
                        SELECT target_type, target_id, allow
                        FROM tipo_cuota_clases_permisos
                        WHERE tipo_cuota_id = :tc
                          AND (sucursal_id IS NULL OR sucursal_id = :sid)
                        """
                    ),
                    {"tc": int(tipo_cuota_id), "sid": int(sucursal_id) if sucursal_id else None},
                )
                .mappings()
                .all()
            )
        except Exception:
            rows = []
        allow_set: Set[Tuple[str, int]] = set()
        deny_set: Set[Tuple[str, int]] = set()
        any_rule = False
        for r in rows or []:
            tt = str(r.get("target_type") or "").strip().lower()
            tid = r.get("target_id")
            if not tt or tid is None:
                continue
            try:
                tid_i = int(tid)
            except Exception:
                continue
            any_rule = True
            if bool(r.get("allow")):
                allow_set.add((tt, tid_i))
            else:
                deny_set.add((tt, tid_i))
        return any_rule, allow_set, deny_set

    def _get_user_class_override_rules(
        self, usuario_id: int, sucursal_id: Optional[int]
    ) -> Tuple[Set[Tuple[str, int]], Set[Tuple[str, int]]]:
        now = _utcnow_naive()
        try:
            rows = (
                self.db.execute(
                    text(
                        """
                        SELECT target_type, target_id, allow, starts_at, ends_at
                        FROM usuario_permisos_clases
                        WHERE usuario_id = :uid
                          AND (:sid IS NULL OR sucursal_id IS NULL OR sucursal_id = :sid)
                        ORDER BY id DESC
                        """
                    ),
                    {"uid": int(usuario_id), "sid": int(sucursal_id) if sucursal_id else None},
                )
                .mappings()
                .all()
            )
        except Exception:
            rows = []
        allow_set: Set[Tuple[str, int]] = set()
        deny_set: Set[Tuple[str, int]] = set()
        seen: Set[Tuple[str, int]] = set()
        for r in rows or []:
            tt = str(r.get("target_type") or "").strip().lower()
            tid = r.get("target_id")
            if not tt or tid is None:
                continue
            try:
                tid_i = int(tid)
            except Exception:
                continue
            k = (tt, tid_i)
            if k in seen:
                continue
            st = r.get("starts_at")
            en = r.get("ends_at")
            if st and isinstance(st, datetime) and st > now:
                continue
            if en and isinstance(en, datetime) and en < now:
                continue
            seen.add(k)
            if bool(r.get("allow")):
                allow_set.add(k)
            else:
                deny_set.add(k)
        return allow_set, deny_set

    def check_class_access(
        self, usuario_id: int, sucursal_id: int, *, clase_id: Optional[int] = None, tipo_clase_id: Optional[int] = None
    ) -> Tuple[Optional[bool], str]:
        if not self._enabled:
            return None, ""
        role = self._get_user_role(int(usuario_id))
        if self._is_privileged_role(role):
            return True, ""

        tipo_cuota_id = self._get_user_tipo_cuota_id(int(usuario_id))
        if not tipo_cuota_id:
            return None, ""

        any_rule, plan_allow, plan_deny = self._get_plan_class_rules(int(tipo_cuota_id), int(sucursal_id))
        user_allow, user_deny = self._get_user_class_override_rules(int(usuario_id), int(sucursal_id))

        targets: List[Tuple[str, int]] = []
        if clase_id is not None:
            targets.append(("clase", int(clase_id)))
        if tipo_clase_id is not None:
            targets.append(("tipo_clase", int(tipo_clase_id)))

        for t in targets:
            if t in user_deny or t in plan_deny:
                return False, "Clase no habilitada"

        if any_rule:
            for t in targets:
                if t in user_allow:
                    return True, ""
            for t in targets:
                if t in plan_allow:
                    return True, ""
            return False, "Clase no habilitada"

        if user_allow:
            for t in targets:
                if t in user_allow:
                    return True, ""
            return True, ""

        return True, ""

    def get_summary(self, usuario_id: int, sucursal_id: Optional[int]) -> Optional[EntitlementsSummary]:
        if not self._enabled:
            return None
        cache_key = f"summary:{usuario_id}:{sucursal_id or 0}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        branch = self.get_effective_branch_access(int(usuario_id))
        if branch is None:
            self._cache_set(cache_key, None)
            return None

        tipo_cuota_id = self._get_user_tipo_cuota_id(int(usuario_id))
        any_rule = False
        plan_allow: Set[Tuple[str, int]] = set()
        plan_deny: Set[Tuple[str, int]] = set()
        if tipo_cuota_id:
            any_rule, plan_allow, plan_deny = self._get_plan_class_rules(
                int(tipo_cuota_id), int(sucursal_id) if sucursal_id else None
            )
        user_allow, user_deny = self._get_user_class_override_rules(
            int(usuario_id), int(sucursal_id) if sucursal_id else None
        )

        allow_effective = set(plan_allow)
        deny_effective = set(plan_deny)
        allow_effective.update(user_allow)
        deny_effective.update(user_deny)

        allowed_tipo_clase_ids: Set[int] = set()
        allowed_clase_ids: Set[int] = set()
        for tt, tid in allow_effective:
            if tt == "tipo_clase":
                allowed_tipo_clase_ids.add(int(tid))
            elif tt == "clase":
                allowed_clase_ids.add(int(tid))

        summary = EntitlementsSummary(
            branch_access=branch,
            class_allowlist_enabled=bool(any_rule),
            allowed_tipo_clase_ids=tuple(sorted(allowed_tipo_clase_ids)),
            allowed_clase_ids=tuple(sorted(allowed_clase_ids)),
        )
        self._cache_set(cache_key, summary)
        return summary
