from __future__ import annotations

import sys
from pathlib import Path

_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_root))


def main() -> int:
    from src.services.feature_flags_service import FeatureFlagsService, DEFAULT_FEATURE_FLAGS
    from src.services.staff_service import StaffService
    from src.services.whatsapp_dispatch_service import WhatsAppDispatchService
    from src.services.whatsapp_service import WhatsAppService
    from src.services.work_session_service import WorkSessionService

    svc = FeatureFlagsService(None)
    merged = svc._merge_flags(
        dict(DEFAULT_FEATURE_FLAGS),
        {"modules": {"usuarios": False, "empleados": True}},
    )
    if not isinstance(merged, dict):
        return 2
    mods = merged.get("modules")
    if not isinstance(mods, dict):
        return 3
    if mods.get("usuarios") is not False:
        return 4
    if "pagos" not in mods:
        return 5
    if "empleados" not in mods:
        return 6

    if not hasattr(StaffService, "get_staff_item"):
        return 7
    if not hasattr(WhatsAppDispatchService, "send_payment_confirmation"):
        return 8
    if not hasattr(WhatsAppService, "list_messages"):
        return 9
    if not hasattr(WorkSessionService, "start_my_session"):
        return 10

    try:
        from src.tools.unit_checks import run as run_unit_checks

        rc = int(run_unit_checks())
        if rc != 0:
            return rc
    except Exception:
        return 22

    try:
        main_py = (_root / "src" / "main.py").read_text(encoding="utf-8", errors="ignore")
        if "allow_origin_regex=rf\"^https://" not in main_py:
            return 23
        if "vercel\\.app" in main_py:
            return 24
        if "ironhub_csrf" not in main_py:
            return 25
        if "include_router(entitlements.router" not in main_py:
            return 27
    except Exception:
        return 26

    try:
        attendance_py = (_root / "src" / "services" / "attendance_service.py").read_text(encoding="utf-8", errors="ignore")
        if "EntitlementsService" not in attendance_py:
            return 28
        branches_py = (_root / "src" / "routers" / "branches.py").read_text(encoding="utf-8", errors="ignore")
        if "EntitlementsService" not in branches_py:
            return 29
        payments_py = (_root / "src" / "services" / "payment_service.py").read_text(encoding="utf-8", errors="ignore")
        if "sucursal_id" not in payments_py or "tipo_cuota_id" not in payments_py:
            return 30
    except Exception:
        return 31
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
