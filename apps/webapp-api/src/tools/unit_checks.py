def run() -> int:
    try:
        from src.database.tenant_connection import validate_tenant_name
    except Exception:
        return 20

    ok = True
    try:
        assert validate_tenant_name("demo")[0] is True
        assert validate_tenant_name("demo-1")[0] is True
        assert validate_tenant_name("www")[0] is False
        assert validate_tenant_name("api")[0] is False
        assert validate_tenant_name("admin")[0] is False
        assert validate_tenant_name("..")[0] is False
        assert validate_tenant_name("a" * 80)[0] is False
        assert validate_tenant_name("Demo")[0] is True
    except Exception:
        ok = False

    try:
        import os

        os.environ["RATE_LIMIT_BACKEND"] = "memory"
        from src.rate_limit_store import incr_and_check

        limited, c1 = incr_and_check("t", 10, 2)
        limited2, c2 = incr_and_check("t", 10, 2)
        limited3, c3 = incr_and_check("t", 10, 2)
        assert limited is False and c1 == 1
        assert limited2 is False and c2 == 2
        assert limited3 is True and c3 == 3
    except Exception:
        ok = False

    try:
        from src.services.feature_flags_service import DEFAULT_FEATURE_FLAGS, FeatureFlagsService

        assert "entitlements_v2" in (DEFAULT_FEATURE_FLAGS.get("modules") or {})
        ffs = FeatureFlagsService(db=None)  # type: ignore[arg-type]
        base = {"modules": {"a": True, "b": False}}
        other = {"modules": {"b": True, "c": False}}
        merged = ffs._merge_flags(base, other)
        assert merged["modules"]["a"] is True
        assert merged["modules"]["b"] is True
        assert merged["modules"]["c"] is False
    except Exception:
        ok = False

    try:
        from src.services.entitlements_service import BranchAccess

        a = BranchAccess(all_sucursales=True, allowed_sucursal_ids=tuple())
        assert a.all_sucursales is True
        assert isinstance(a.denied_sucursal_ids, tuple)
    except Exception:
        ok = False

    return 0 if ok else 21
