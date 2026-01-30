# Webapp API Database Package
from src.database.connection import SessionLocal, get_db
from src.database.tenant_connection import (
    get_tenant_session_factory,
    get_tenant_engine,
    set_current_tenant,
    get_current_tenant,
)


# DatabaseManager is a placeholder for compatibility - the actual
# functionality is provided by the tenant_connection module
class DatabaseManager:
    """Compatibility placeholder. Use tenant_connection functions instead."""

    pass


__all__ = [
    "SessionLocal",
    "get_db",
    "get_tenant_session_factory",
    "get_tenant_engine",
    "set_current_tenant",
    "get_current_tenant",
    "DatabaseManager",
]
