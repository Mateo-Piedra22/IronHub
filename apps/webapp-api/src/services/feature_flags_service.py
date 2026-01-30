from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database.orm_models import FeatureFlags, FeatureFlagsOverride


DEFAULT_FEATURE_FLAGS: Dict[str, Any] = {
    "modules": {
        "usuarios": True,
        "pagos": True,
        "profesores": True,
        "empleados": True,
        "rutinas": True,
        "ejercicios": True,
        "clases": True,
        "asistencias": True,
        "whatsapp": True,
        "configuracion": True,
        "reportes": True,
        "entitlements_v2": True,
    }
}


class FeatureFlagsService:
    def __init__(self, db: Session):
        self.db = db

    def _merge_flags(self, base: Dict[str, Any], other: Dict[str, Any]) -> Dict[str, Any]:
        out: Dict[str, Any] = {"modules": dict(base.get("modules") or {})}
        try:
            om = other.get("modules") if isinstance(other, dict) else None
            if isinstance(om, dict):
                out["modules"].update({str(k): bool(v) for k, v in om.items()})
        except Exception:
            pass
        return out

    def get_flags(self, sucursal_id: Optional[int] = None) -> Dict[str, Any]:
        base_flags: Dict[str, Any] = dict(DEFAULT_FEATURE_FLAGS)
        try:
            flags = self.db.scalar(
                select(FeatureFlags.flags).where(FeatureFlags.id == 1).limit(1)
            )
            if flags:
                base_flags = self._merge_flags(dict(DEFAULT_FEATURE_FLAGS), dict(flags))
        except Exception:
            base_flags = dict(DEFAULT_FEATURE_FLAGS)

        sid: Optional[int] = None
        try:
            sid = int(sucursal_id) if sucursal_id is not None else None
        except Exception:
            sid = None
        if sid is None or sid <= 0:
            return base_flags

        try:
            flags = self.db.scalar(
                select(FeatureFlagsOverride.flags)
                .where(FeatureFlagsOverride.sucursal_id == int(sid))
                .limit(1)
            )
            if flags:
                return self._merge_flags(base_flags, dict(flags))
        except Exception:
            return base_flags
        return base_flags

    def set_flags(self, flags: Dict[str, Any], sucursal_id: Optional[int] = None) -> None:
        try:
            payload = self._merge_flags(dict(DEFAULT_FEATURE_FLAGS), dict(flags or {}))
            sid: Optional[int] = None
            try:
                sid = int(sucursal_id) if sucursal_id is not None else None
            except Exception:
                sid = None
            if sid is None or sid <= 0:
                row = self.db.get(FeatureFlags, 1)
                if row is None:
                    row = FeatureFlags(id=1, flags=payload)
                    self.db.add(row)
                else:
                    row.flags = payload
            else:
                row = self.db.get(FeatureFlagsOverride, int(sid))
                if row is None:
                    row = FeatureFlagsOverride(sucursal_id=int(sid), flags=payload)
                    self.db.add(row)
                else:
                    row.flags = payload
            self.db.commit()
        except Exception:
            try:
                self.db.rollback()
            except Exception:
                pass

    def is_enabled(self, key: str, sucursal_id: Optional[int] = None) -> bool:
        try:
            k = str(key or "").strip()
        except Exception:
            k = ""
        if not k:
            return False
        flags = self.get_flags(sucursal_id=sucursal_id)
        modules = flags.get("modules") if isinstance(flags, dict) else None
        if isinstance(modules, dict) and k in modules:
            try:
                return bool(modules.get(k))
            except Exception:
                return bool(DEFAULT_FEATURE_FLAGS.get("modules", {}).get(k, False))
        return bool(DEFAULT_FEATURE_FLAGS.get("modules", {}).get(k, False))
