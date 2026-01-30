"""
Audit Service - Centralized audit logging for sensitive actions.

Provides a simple interface to log all sensitive operations
such as deletions, role changes, status toggles, etc.
"""

import logging
import json
from typing import Optional, Dict, Any
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import select

from src.services.base import BaseService
from src.models.orm_models import AuditLog
from src.security.session_claims import get_claims

logger = logging.getLogger(__name__)


class AuditService(BaseService):
    """Service for audit logging using SQLAlchemy."""

    # Action types
    ACTION_CREATE = "CREATE"
    ACTION_UPDATE = "UPDATE"
    ACTION_DELETE = "DELETE"
    ACTION_TOGGLE_STATUS = "TOGGLE_STATUS"
    ACTION_ROLE_CHANGE = "ROLE_CHANGE"
    ACTION_LOGIN = "LOGIN"
    ACTION_LOGOUT = "LOGOUT"
    ACTION_PASSWORD_CHANGE = "PASSWORD_CHANGE"
    ACTION_PIN_CHANGE = "PIN_CHANGE"
    ACTION_PAYMENT_DELETE = "PAYMENT_DELETE"
    ACTION_USER_DEACTIVATE = "USER_DEACTIVATE"
    ACTION_USER_ACTIVATE = "USER_ACTIVATE"
    ACTION_BULK_ACTION = "BULK_ACTION"
    ACTION_CONFIG_CHANGE = "CONFIG_CHANGE"

    def __init__(self, db: Session):
        super().__init__(db)

    def log(
        self,
        action: str,
        table_name: str,
        record_id: Optional[int] = None,
        user_id: Optional[int] = None,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None,
        extra_details: Optional[Dict[str, Any]] = None,
    ) -> Optional[int]:
        """
        Log an audit event.

        Args:
            action: Type of action (use ACTION_* constants)
            table_name: Name of the affected table/entity
            record_id: ID of the affected record (if applicable)
            user_id: ID of the user performing the action
            old_values: Previous values (for updates/deletes)
            new_values: New values (for creates/updates)
            ip_address: Client IP address
            user_agent: Client user agent
            session_id: Session identifier
            extra_details: Additional context to include in new_values

        Returns:
            ID of the created audit log entry, or None if failed
        """
        try:
            # Serialize values to JSON strings
            old_json = None
            new_json = None

            if old_values:
                try:
                    old_json = json.dumps(old_values, default=str, ensure_ascii=False)
                except Exception:
                    old_json = str(old_values)

            if new_values or extra_details:
                combined = {}
                if new_values:
                    combined.update(new_values)
                if extra_details:
                    combined["_extra"] = extra_details
                try:
                    new_json = json.dumps(combined, default=str, ensure_ascii=False)
                except Exception:
                    new_json = str(combined)

            audit_entry = AuditLog(
                user_id=user_id,
                action=action,
                table_name=table_name,
                record_id=record_id,
                old_values=old_json,
                new_values=new_json,
                ip_address=ip_address,
                user_agent=user_agent,
                session_id=session_id,
                timestamp=datetime.utcnow(),
            )

            self.db.add(audit_entry)
            self.db.commit()

            logger.info(
                f"Audit log created: action={action} table={table_name} "
                f"record_id={record_id} user_id={user_id}"
            )

            return audit_entry.id

        except Exception as e:
            logger.error(f"Failed to create audit log: {e}")
            try:
                self.db.rollback()
            except Exception:
                pass
            return None

    def log_from_request(
        self,
        request,
        action: str,
        table_name: str,
        record_id: Optional[int] = None,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        extra_details: Optional[Dict[str, Any]] = None,
    ) -> Optional[int]:
        """
        Log an audit event, extracting user info from the request.

        Args:
            request: FastAPI/Starlette request object
            action: Type of action
            table_name: Name of the affected table/entity
            record_id: ID of the affected record
            old_values: Previous values
            new_values: New values
            extra_details: Additional context

        Returns:
            ID of the created audit log entry, or None if failed
        """
        try:
            # Extract user ID from session
            user_id = None
            session_id = None
            try:
                user_id = request.session.get("user_id") or request.session.get(
                    "gestion_profesor_user_id"
                )
                if user_id:
                    user_id = int(user_id)
                # Generate a session identifier from session keys (for debugging)
                session_id = (
                    str(hash(frozenset(request.session.keys())))[:16]
                    if request.session
                    else None
                )
            except Exception:
                pass

            # Extract IP address
            ip_address = None
            try:
                # Check for forwarded headers (behind proxy)
                forwarded = request.headers.get("x-forwarded-for")
                if forwarded:
                    ip_address = forwarded.split(",")[0].strip()
                else:
                    ip_address = request.client.host if request.client else None
            except Exception:
                pass

            # Extract user agent
            user_agent = None
            try:
                user_agent = request.headers.get("user-agent")
            except Exception:
                pass

            enriched_extra: Dict[str, Any] = {}
            try:
                claims = get_claims(request)
                for k in ("tenant", "role", "session_type", "sucursal_id"):
                    if k in claims and claims.get(k) is not None:
                        enriched_extra[k] = claims.get(k)
            except Exception:
                pass
            try:
                enriched_extra["path"] = str(getattr(request.url, "path", "") or "")
                enriched_extra["method"] = str(getattr(request, "method", "") or "")
            except Exception:
                pass
            if extra_details:
                enriched_extra.update(extra_details)

            return self.log(
                action=action,
                table_name=table_name,
                record_id=record_id,
                user_id=user_id,
                old_values=old_values,
                new_values=new_values,
                ip_address=ip_address,
                user_agent=user_agent,
                session_id=session_id,
                extra_details=enriched_extra or None,
            )

        except Exception as e:
            logger.error(f"Failed to log audit from request: {e}")
            return None

    def get_logs(
        self,
        user_id: Optional[int] = None,
        action: Optional[str] = None,
        table_name: Optional[str] = None,
        record_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        Query audit logs with optional filters.

        Returns:
            Dict with 'logs' (list) and 'total' (count)
        """
        try:
            query = select(AuditLog)

            if user_id is not None:
                query = query.where(AuditLog.user_id == user_id)
            if action:
                query = query.where(AuditLog.action == action)
            if table_name:
                query = query.where(AuditLog.table_name == table_name)
            if record_id is not None:
                query = query.where(AuditLog.record_id == record_id)
            if start_date:
                query = query.where(AuditLog.timestamp >= start_date)
            if end_date:
                query = query.where(AuditLog.timestamp <= end_date)

            # Count total
            from sqlalchemy import func

            count_query = select(func.count()).select_from(query.subquery())
            total = self.db.execute(count_query).scalar() or 0

            # Apply pagination and ordering
            query = query.order_by(AuditLog.timestamp.desc())
            query = query.limit(limit).offset(offset)

            results = self.db.execute(query).scalars().all()

            logs = []
            for entry in results:
                logs.append(
                    {
                        "id": entry.id,
                        "user_id": entry.user_id,
                        "action": entry.action,
                        "table_name": entry.table_name,
                        "record_id": entry.record_id,
                        "old_values": entry.old_values,
                        "new_values": entry.new_values,
                        "ip_address": str(entry.ip_address)
                        if entry.ip_address
                        else None,
                        "user_agent": entry.user_agent,
                        "session_id": entry.session_id,
                        "timestamp": entry.timestamp.isoformat()
                        if entry.timestamp
                        else None,
                    }
                )

            return {"logs": logs, "total": total}

        except Exception as e:
            logger.error(f"Failed to query audit logs: {e}")
            return {"logs": [], "total": 0, "error": str(e)}
