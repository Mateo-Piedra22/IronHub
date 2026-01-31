"""WhatsApp Service - SQLAlchemy ORM for whatsapp message database operations."""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta, timezone
import logging

from sqlalchemy.orm import Session
from sqlalchemy import text

from src.services.base import BaseService

logger = logging.getLogger(__name__)


class WhatsAppService(BaseService):
    """Service for WhatsApp message database operations."""

    def __init__(self, db: Session):
        super().__init__(db)

    def _now_utc_naive(self) -> datetime:
        return datetime.now(timezone.utc).replace(tzinfo=None)

    def obtener_resumen_mensajes(
        self, dias: int = 30, limite: int = 300, sucursal_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        try:
            since = self._now_utc_naive() - timedelta(days=int(dias or 0))
            sid = None
            try:
                sid = int(sucursal_id) if sucursal_id is not None else None
            except Exception:
                sid = None
            if sid is not None and sid <= 0:
                sid = None
            result = self.db.execute(
                text("""
                    SELECT wm.id, wm.user_id,
                           COALESCE(u.nombre,'') AS usuario_nombre,
                           COALESCE(u.telefono,'') AS usuario_telefono,
                           wm.sucursal_id, COALESCE(s.nombre,'') AS sucursal_nombre,
                           wm.phone_number, wm.message_type, wm.template_name, wm.message_content,
                           COALESCE(wm.status,'') AS status, wm.message_id, wm.sent_at, wm.created_at
                    FROM whatsapp_messages wm
                    LEFT JOIN usuarios u ON u.id = wm.user_id
                    LEFT JOIN sucursales s ON s.id = wm.sucursal_id
                    WHERE wm.sent_at >= :since
                      AND (:sid IS NULL OR wm.sucursal_id = :sid)
                    ORDER BY wm.sent_at DESC
                    LIMIT :limite
                """),
                {"since": since, "limite": int(limite or 0), "sid": sid},
            )
            return [
                {
                    "id": r[0],
                    "user_id": r[1],
                    "usuario_nombre": r[2],
                    "usuario_telefono": r[3],
                    "sucursal_id": r[4],
                    "sucursal_nombre": r[5],
                    "phone_number": r[6],
                    "message_type": r[7],
                    "template_name": r[8],
                    "message_content": r[9],
                    "status": r[10],
                    "message_id": r[11],
                    "sent_at": str(r[12]) if r[12] else None,
                    "created_at": str(r[13]) if r[13] else None,
                }
                for r in result.fetchall()
            ]
        except Exception as e:
            logger.error(f"Error getting whatsapp resumen mensajes: {e}")
            return []

    def list_messages(
        self,
        *,
        dias: int = 30,
        status: Optional[str] = None,
        page: int = 1,
        limit: int = 25,
        sucursal_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        try:
            d = int(dias or 30)
        except Exception:
            d = 30
        if d < 1:
            d = 1
        if d > 365:
            d = 365
        try:
            p = int(page or 1)
        except Exception:
            p = 1
        if p < 1:
            p = 1
        try:
            lim = int(limit or 25)
        except Exception:
            lim = 25
        if lim < 1:
            lim = 1
        if lim > 200:
            lim = 200
        offset = (p - 1) * lim

        since = self._now_utc_naive() - timedelta(days=int(d or 0))
        st = str(status or "").strip().lower() or None

        where = ["wm.sent_at >= :since"]
        params: Dict[str, Any] = {"since": since, "limit": lim, "offset": offset}
        if st:
            where.append("wm.status = :status")
            params["status"] = st
        if sucursal_id is not None:
            where.append("wm.sucursal_id = :sid")
            params["sid"] = int(sucursal_id)
        where_sql = " AND ".join(where)

        total = (
            self.db.execute(
                text(f"SELECT COUNT(*) FROM whatsapp_messages wm WHERE {where_sql}"),
                params,
            ).scalar()
            or 0
        )

        totals_by_status: Dict[str, int] = {}
        totals_by_type: Dict[str, int] = {}
        try:
            where_for_totals = ["wm.sent_at >= :since"]
            params_tot = {"since": since}
            if sucursal_id is not None:
                where_for_totals.append("wm.sucursal_id = :sid")
                params_tot["sid"] = int(sucursal_id)
            rows = (
                self.db.execute(
                    text(
                        f"""
                        SELECT COALESCE(wm.status,'') AS status, COUNT(*) as c
                        FROM whatsapp_messages wm
                        WHERE {' AND '.join(where_for_totals)}
                        GROUP BY COALESCE(wm.status,'')
                        """
                    ),
                    params_tot,
                )
                .mappings()
                .all()
            )
            for r in rows or []:
                k = str(r.get("status") or "").strip().lower()
                if not k:
                    continue
                try:
                    totals_by_status[k] = int(r.get("c") or 0)
                except Exception:
                    totals_by_status[k] = 0
            trows = (
                self.db.execute(
                    text(
                        f"""
                        SELECT COALESCE(wm.message_type,'') AS message_type, COUNT(*) as c
                        FROM whatsapp_messages wm
                        WHERE {' AND '.join(where_for_totals)}
                        GROUP BY COALESCE(wm.message_type,'')
                        """
                    ),
                    params_tot,
                )
                .mappings()
                .all()
            )
            for r in trows or []:
                k = str(r.get("message_type") or "").strip().lower()
                if not k:
                    continue
                try:
                    totals_by_type[k] = int(r.get("c") or 0)
                except Exception:
                    totals_by_type[k] = 0
        except Exception:
            totals_by_status = {}
            totals_by_type = {}

        result = self.db.execute(
            text(
                f"""
                SELECT wm.id, wm.user_id,
                       COALESCE(u.nombre,'') AS usuario_nombre,
                       COALESCE(u.telefono,'') AS usuario_telefono,
                       wm.sucursal_id,
                       wm.phone_number, wm.message_type, wm.template_name, wm.message_content,
                       COALESCE(wm.status,'') AS status, wm.message_id, wm.sent_at, wm.created_at
                FROM whatsapp_messages wm
                LEFT JOIN usuarios u ON u.id = wm.user_id
                WHERE {where_sql}
                ORDER BY wm.sent_at DESC NULLS LAST, wm.id DESC
                LIMIT :limit OFFSET :offset
                """
            ),
            params,
        )
        items = []
        for r in result.fetchall():
            items.append(
                {
                    "id": r[0],
                    "user_id": r[1],
                    "usuario_nombre": r[2],
                    "usuario_telefono": r[3],
                    "sucursal_id": r[4],
                    "phone_number": r[5],
                    "message_type": r[6],
                    "template_name": r[7],
                    "message_content": r[8],
                    "status": r[9],
                    "message_id": r[10],
                    "sent_at": str(r[11]) if r[11] else None,
                    "created_at": str(r[12]) if r[12] else None,
                }
            )
        return {
            "ok": True,
            "items": items,
            "total": int(total),
            "page": int(p),
            "limit": int(lim),
            "dias": int(d),
            "totals_by_status": totals_by_status,
            "totals_by_type": totals_by_type,
        }

    def obtener_mensaje_por_id(self, mensaje_id: int) -> Optional[Dict[str, Any]]:
        try:
            row = self.db.execute(
                text("""
                    SELECT id, user_id, message_type, template_name, phone_number, message_content, status, message_id, sent_at, created_at
                    FROM whatsapp_messages WHERE id = :id LIMIT 1
                """),
                {"id": int(mensaje_id)},
            ).fetchone()
            if not row:
                return None
            return {
                "id": row[0],
                "user_id": row[1],
                "message_type": row[2],
                "template_name": row[3],
                "phone_number": row[4],
                "message_content": row[5],
                "status": row[6],
                "message_id": row[7],
                "sent_at": str(row[8]) if row[8] else None,
                "created_at": str(row[9]) if row[9] else None,
            }
        except Exception as e:
            logger.error(f"Error getting whatsapp message by id: {e}")
            return None

    # ========== Pendings/Failed Messages ==========

    def obtener_mensajes_fallidos(
        self, dias: int = 30, limite: int = 200
    ) -> List[Dict[str, Any]]:
        """Get failed WhatsApp messages."""
        try:
            since = self._now_utc_naive() - timedelta(days=int(dias or 0))
            result = self.db.execute(
                text("""
                    SELECT wm.id, wm.user_id,
                           COALESCE(u.nombre,'') AS usuario_nombre, COALESCE(u.telefono,'') AS usuario_telefono,
                           wm.phone_number, wm.message_type, wm.template_name, wm.message_content,
                           wm.status, wm.message_id, wm.sent_at AS fecha_envio
                    FROM whatsapp_messages wm LEFT JOIN usuarios u ON u.id = wm.user_id
                    WHERE wm.status = 'failed' AND wm.sent_at >= :since
                    ORDER BY wm.sent_at DESC LIMIT :limite
                """),
                {"since": since, "limite": limite},
            )
            return [
                {
                    "id": r[0],
                    "user_id": r[1],
                    "usuario_nombre": r[2],
                    "usuario_telefono": r[3],
                    "phone_number": r[4],
                    "message_type": r[5],
                    "template_name": r[6],
                    "message_content": r[7],
                    "status": r[8],
                    "message_id": r[9],
                    "fecha_envio": str(r[10]) if r[10] else None,
                }
                for r in result.fetchall()
            ]
        except Exception as e:
            logger.error(f"Error getting failed messages: {e}")
            return []

    def obtener_ultimo_fallido(
        self, telefono: Optional[str] = None, usuario_id: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Get last failed message for retry."""
        try:
            if telefono:
                result = self.db.execute(
                    text("""
                    SELECT message_type, template_name, message_content FROM whatsapp_messages
                    WHERE phone_number = :tel AND status = 'failed' ORDER BY sent_at DESC LIMIT 1
                """),
                    {"tel": telefono},
                )
            else:
                result = self.db.execute(
                    text("""
                    SELECT message_type, template_name, message_content FROM whatsapp_messages
                    WHERE user_id = :uid AND status = 'failed' ORDER BY sent_at DESC LIMIT 1
                """),
                    {"uid": usuario_id},
                )
            row = result.fetchone()
            return (
                {
                    "message_type": row[0],
                    "template_name": row[1],
                    "message_content": row[2],
                }
                if row
                else None
            )
        except Exception as e:
            logger.error(f"Error getting last failed: {e}")
            return None

    def limpiar_fallidos(
        self, telefono: Optional[str] = None, dias: int = 30
    ) -> Dict[str, Any]:
        """Clear failed messages. Returns count deleted and phones affected."""
        try:
            since = self._now_utc_naive() - timedelta(days=int(dias or 0))
            deleted = 0
            phones = []

            if telefono:
                result = self.db.execute(
                    text("""
                    DELETE FROM whatsapp_messages WHERE phone_number = :tel AND status = 'failed'
                    AND sent_at >= :since
                """),
                    {"tel": telefono, "since": since},
                )
                deleted = result.rowcount or 0
                phones = [telefono]
            else:
                ph_result = self.db.execute(
                    text("""
                    SELECT DISTINCT phone_number FROM whatsapp_messages
                    WHERE status = 'failed' AND sent_at >= :since
                """),
                    {"since": since},
                )
                phones = [r[0] for r in ph_result.fetchall() if r[0]]
                r = self.db.execute(
                    text("""
                        DELETE FROM whatsapp_messages
                        WHERE status = 'failed'
                          AND sent_at >= :since
                    """),
                    {"since": since},
                )
                deleted = r.rowcount or 0

            self.db.commit()
            return {"deleted": deleted, "phones": phones}
        except Exception as e:
            logger.error(f"Error clearing failures: {e}")
            self.db.rollback()
            return {"deleted": 0, "phones": [], "error": str(e)}

    # ========== User Messages ==========

    def obtener_historial_usuario(
        self, usuario_id: int, tipo: Optional[str] = None, limite: int = 50
    ) -> List[Dict[str, Any]]:
        """Get message history for a user."""
        try:
            if tipo:
                result = self.db.execute(
                    text("""
                    SELECT id, user_id, message_type, template_name, phone_number, message_content, status, message_id, sent_at, created_at
                    FROM whatsapp_messages WHERE user_id = :uid AND message_type = :tipo ORDER BY sent_at DESC LIMIT :limite
                """),
                    {"uid": usuario_id, "tipo": tipo, "limite": limite},
                )
            else:
                result = self.db.execute(
                    text("""
                    SELECT id, user_id, message_type, template_name, phone_number, message_content, status, message_id, sent_at, created_at
                    FROM whatsapp_messages WHERE user_id = :uid ORDER BY sent_at DESC LIMIT :limite
                """),
                    {"uid": usuario_id, "limite": limite},
                )

            return [
                {
                    "id": r[0],
                    "user_id": r[1],
                    "message_type": r[2],
                    "template_name": r[3],
                    "phone_number": r[4],
                    "message_content": r[5],
                    "status": r[6],
                    "message_id": r[7],
                    "sent_at": str(r[8]) if r[8] else None,
                    "created_at": str(r[9]) if r[9] else None,
                }
                for r in result.fetchall()
            ]
        except Exception as e:
            logger.error(f"Error getting user history: {e}")
            return []

    def obtener_ultimo_mensaje(
        self,
        usuario_id: int,
        tipo: Optional[str] = None,
        direccion: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Get last message for a user."""
        try:
            query = "SELECT id, user_id, message_type, template_name, phone_number, message_content, status, message_id, sent_at FROM whatsapp_messages WHERE user_id = :uid"
            params = {"uid": usuario_id}
            if tipo:
                query += " AND message_type = :tipo"
                params["tipo"] = tipo
            if direccion == "enviado":
                query += " AND status IN ('sent', 'delivered', 'read', 'failed')"
            elif direccion == "recibido":
                query += " AND status = 'received'"
            query += " ORDER BY sent_at DESC LIMIT 1"

            result = self.db.execute(text(query), params)
            row = result.fetchone()
            if not row:
                return None
            return {
                "id": row[0],
                "user_id": row[1],
                "message_type": row[2],
                "template_name": row[3],
                "phone_number": row[4],
                "message_content": row[5],
                "status": row[6],
                "message_id": row[7],
                "sent_at": str(row[8]) if row[8] else None,
            }
        except Exception as e:
            logger.error(f"Error getting last message: {e}")
            return None

    def eliminar_mensaje_por_pk(self, usuario_id: int, message_pk: int) -> bool:
        """Delete message by primary key."""
        try:
            result = self.db.execute(
                text("DELETE FROM whatsapp_messages WHERE id = :pk AND user_id = :uid"),
                {"pk": message_pk, "uid": usuario_id},
            )
            self.db.commit()
            return (result.rowcount or 0) > 0
        except Exception as e:
            logger.error(f"Error deleting message: {e}")
            self.db.rollback()
            return False

    def eliminar_mensaje_por_mid(self, usuario_id: int, message_id: str) -> bool:
        """Delete message by WhatsApp message_id."""
        try:
            result = self.db.execute(
                text(
                    "DELETE FROM whatsapp_messages WHERE message_id = :mid AND user_id = :uid"
                ),
                {"mid": message_id, "uid": usuario_id},
            )
            self.db.commit()
            return (result.rowcount or 0) > 0
        except Exception as e:
            logger.error(f"Error deleting message by mid: {e}")
            self.db.rollback()
            return False

    def obtener_mensaje_por_pk(
        self, usuario_id: int, message_pk: int
    ) -> Optional[Dict[str, Any]]:
        """Get message by primary key for audit."""
        try:
            result = self.db.execute(
                text("""
                SELECT id, user_id, message_type, template_name, phone_number, message_content, status, message_id, sent_at
                FROM whatsapp_messages WHERE id = :pk AND user_id = :uid
            """),
                {"pk": message_pk, "uid": usuario_id},
            )
            row = result.fetchone()
            if not row:
                return None
            return {
                "id": row[0],
                "user_id": row[1],
                "message_type": row[2],
                "template_name": row[3],
                "phone_number": row[4],
                "message_content": row[5],
                "status": row[6],
                "message_id": row[7],
                "sent_at": str(row[8]) if row[8] else None,
            }
        except Exception as e:
            logger.error(f"Error getting message: {e}")
            return None

    # ========== Webhook Operations ==========

    def actualizar_estado_mensaje(self, message_id: str, status: str) -> bool:
        """Update message status from webhook."""
        try:
            self.db.execute(
                text(
                    "UPDATE whatsapp_messages SET status = :status WHERE message_id = :mid"
                ),
                {"status": status, "mid": message_id},
            )
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating message status: {e}")
            self.db.rollback()
            return False

    def registrar_mensaje_entrante(
        self,
        user_id: Optional[int],
        sucursal_id: Optional[int],
        phone_number: str,
        message_content: str,
        message_id: str,
    ) -> bool:
        """Register incoming message from webhook."""
        try:
            sent_at = self._now_utc_naive()
            try:
                self.db.execute(
                    text(
                        """
                        INSERT INTO whatsapp_messages (user_id, sucursal_id, message_type, template_name, phone_number, message_content, status, message_id, sent_at)
                        VALUES (:uid, :sid, 'welcome', 'incoming', :phone, :content, 'received', :mid, :sent_at)
                        """
                    ),
                    {
                        "uid": user_id,
                        "sid": int(sucursal_id) if sucursal_id is not None else None,
                        "phone": phone_number,
                        "content": message_content,
                        "mid": message_id,
                        "sent_at": sent_at,
                    },
                )
            except Exception:
                self.db.execute(
                    text(
                        """
                        INSERT INTO whatsapp_messages (user_id, message_type, template_name, phone_number, message_content, status, message_id, sent_at)
                        VALUES (:uid, 'welcome', 'incoming', :phone, :content, 'received', :mid, :sent_at)
                        """
                    ),
                    {
                        "uid": user_id,
                        "phone": phone_number,
                        "content": message_content,
                        "mid": message_id,
                        "sent_at": sent_at,
                    },
                )
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error registering incoming message: {e}")
            self.db.rollback()
            return False

    def obtener_usuario_id_por_telefono(self, telefono: str) -> Optional[int]:
        """Get user ID by phone number."""
        try:
            # Normalize phone number
            tel = telefono.strip().replace("+", "").replace(" ", "").replace("-", "")
            result = self.db.execute(
                text("""
                SELECT id FROM usuarios WHERE REPLACE(REPLACE(REPLACE(telefono, '+', ''), ' ', ''), '-', '') LIKE '%' || :tel
                ORDER BY id LIMIT 1
            """),
                {"tel": tel[-10:] if len(tel) >= 10 else tel},
            )
            row = result.fetchone()
            return row[0] if row else None
        except Exception as e:
            logger.error(f"Error getting user by phone: {e}")
            return None
