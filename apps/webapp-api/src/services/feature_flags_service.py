from typing import Any, Dict, Optional, List

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
        "bulk_actions": False,
        "soporte": True,
        "novedades": True,
        "accesos": True,
    }
    ,
    "features": {
        "bulk_actions": {
            "usuarios_import": True,
        }
        ,
        "usuarios": {
            "create": True,
            "update": True,
            "delete": True,
            "pin": True,
        },
        "pagos": {
            "create": True,
            "update": True,
            "delete": True,
            "export": True,
        },
    },
}


class FeatureFlagsService:
    def __init__(self, db: Session):
        self.db = db

    def _merge_bool_tree(self, base: Any, other: Any) -> Any:
        if isinstance(base, dict) and isinstance(other, dict):
            out: Dict[str, Any] = {str(k): v for k, v in base.items()}
            for k, v in other.items():
                ks = str(k)
                if ks in out:
                    out[ks] = self._merge_bool_tree(out[ks], v)
                else:
                    out[ks] = self._merge_bool_tree({}, v) if isinstance(v, dict) else bool(v)
            return out
        if isinstance(other, dict):
            return {str(k): self._merge_bool_tree({}, v) for k, v in other.items()}
        return bool(other)

    def _merge_flags(self, base: Dict[str, Any], other: Dict[str, Any]) -> Dict[str, Any]:
        out: Dict[str, Any] = dict(base or {})

        bm = (base or {}).get("modules") if isinstance(base, dict) else None
        om = (other or {}).get("modules") if isinstance(other, dict) else None
        modules = dict(bm or {}) if isinstance(bm, dict) else {}
        if isinstance(om, dict):
            modules.update({str(k): bool(v) for k, v in om.items()})
        out["modules"] = modules

        bf = (base or {}).get("features") if isinstance(base, dict) else None
        of = (other or {}).get("features") if isinstance(other, dict) else None
        features = dict(bf or {}) if isinstance(bf, dict) else {}
        if isinstance(of, dict):
            features = self._merge_bool_tree(features, of)
        out["features"] = features

        try:
            if isinstance(other, dict):
                for k, v in other.items():
                    if k in ("modules", "features"):
                        continue
                    out[k] = v
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
        parts = [p.strip() for p in k.split(":") if str(p).strip()]
        if not parts:
            return False

        flags = self.get_flags(sucursal_id=sucursal_id)
        modules = flags.get("modules") if isinstance(flags, dict) else {}
        default_modules = DEFAULT_FEATURE_FLAGS.get("modules") if isinstance(DEFAULT_FEATURE_FLAGS, dict) else {}

        module_key = parts[0]
        module_val = None
        try:
            if isinstance(modules, dict) and module_key in modules:
                module_val = bool(modules.get(module_key))
        except Exception:
            module_val = None
        if module_val is None:
            module_val = bool(default_modules.get(module_key, False)) if isinstance(default_modules, dict) else False
        if not module_val:
            return False
        if len(parts) == 1:
            return True

        def _get_tree_value(tree: Any, path: List[str]) -> Optional[Any]:
            node = tree
            for seg in path:
                if not isinstance(node, dict):
                    return None
                if seg not in node:
                    return None
                node = node.get(seg)
            return node

        features = flags.get("features") if isinstance(flags, dict) else {}
        defaults = DEFAULT_FEATURE_FLAGS.get("features") if isinstance(DEFAULT_FEATURE_FLAGS, dict) else {}
        v = _get_tree_value(features, parts)
        if v is None:
            v = _get_tree_value(defaults, parts)
        if v is None:
            return False
        try:
            return bool(v)
        except Exception:
            return False
