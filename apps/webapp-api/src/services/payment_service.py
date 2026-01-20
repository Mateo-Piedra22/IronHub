"""
Payment Service - SQLAlchemy ORM Implementation

Replaces legacy PaymentManager raw SQL with proper SQLAlchemy ORM.
All business logic preserved, only database access modernized.
"""

from datetime import datetime, timedelta, date, timezone
from typing import List, Optional, Dict, Any
import logging
import os

try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None

from sqlalchemy.orm import Session
from sqlalchemy import select, update, delete, func, text
from sqlalchemy.dialects.postgresql import insert

from src.services.base import BaseService
from src.database.repositories.payment_repository import PaymentRepository
from src.database.repositories.user_repository import UserRepository
from src.database.orm_models import (
    Pago, Usuario, MetodoPago, ConceptoPago, PagoDetalle, TipoCuota,
    NumeracionComprobante, ComprobantePago
)
from src.services.whatsapp_dispatch_service import WhatsAppDispatchService

logger = logging.getLogger(__name__)


class PaymentService(BaseService):
    """
    Payment service using SQLAlchemy ORM.
    Preserves all business logic from legacy PaymentManager.
    """

    def __init__(self, db: Session = None):
        super().__init__(db)
        self.payment_repo = PaymentRepository(self.db, None, None)
        self.user_repo = UserRepository(self.db, None, None)
        
        # Alert manager stub (for compatibility)
        self._alert_manager = None

    def _is_exempt_role(self, rol: Optional[str]) -> bool:
        try:
            r = str(rol or '').strip().lower()
        except Exception:
            r = ''
        return r in ('profesor', 'dueño', 'dueno', 'owner')

    def _get_app_timezone(self):
        tz_name = (
            os.getenv("APP_TIMEZONE")
            or os.getenv("TIMEZONE")
            or os.getenv("TZ")
            or "America/Argentina/Buenos_Aires"
        )
        if ZoneInfo is not None:
            try:
                return ZoneInfo(tz_name)
            except Exception:
                pass
        return timezone(timedelta(hours=-3))

    def _now_local_naive(self) -> datetime:
        tz = self._get_app_timezone()
        return datetime.now(timezone.utc).astimezone(tz).replace(tzinfo=None)

    def _today_local_date(self) -> date:
        return self._now_local_naive().date()

    # =========================================================================
    # CORE PAYMENT OPERATIONS
    # =========================================================================

    def registrar_pago(
        self, 
        usuario_id: int, 
        monto: float, 
        mes: int, 
        año: int, 
        metodo_pago_id: Optional[int] = None
    ) -> int:
        """
        Register a simple payment (legacy wrapper).
        Redirects to registrar_pago_avanzado, respecting explicit month/year.
        """
        # Create a generic concept for the payment
        concepto = {
            "descripcion": f"Cuota {mes}/{año}",
            "cantidad": 1,
            "precio_unitario": monto,
            "concepto_id": None
        }
        
        return self.registrar_pago_avanzado(
            usuario_id=usuario_id,
            metodo_pago_id=metodo_pago_id or 1,
            conceptos=[concepto],
            monto_personalizado=monto,
            override_mes=mes,
            override_año=año
        )

    def modificar_pago(self, pago_id: int, data: Dict[str, Any]) -> bool:
        """Update an existing payment."""
        pago = self.db.get(Pago, pago_id)
        if not pago:
            raise ValueError(f"Pago con ID {pago_id} no encontrado")

        for key, value in data.items():
            if hasattr(pago, key) and key != 'id':
                setattr(pago, key, value)

        self.db.commit()
        return True

    def modificar_pago_avanzado(
        self,
        pago_id: int,
        usuario_id: int,
        metodo_pago_id: Optional[int],
        conceptos: List[Dict[str, Any]],
        fecha_pago: Optional[datetime] = None
    ) -> int:
        """
        Update a payment with new concepts.
        Deletes existing details and creates new ones.
        """
        pago = self.db.get(Pago, pago_id)
        if not pago:
            raise ValueError(f"Pago con ID {pago_id} no encontrado")

        try:
            # Delete existing details
            self.db.execute(
                delete(PagoDetalle).where(PagoDetalle.pago_id == pago_id)
            )

            # Calculate total from concepts
            subtotal = sum(
                float(c.get('cantidad', 1)) * float(c.get('precio_unitario', 0))
                for c in conceptos
            )
            comision = self._calcular_comision(subtotal, metodo_pago_id)
            total = subtotal + comision

            # Update payment
            now = fecha_pago or getattr(pago, "fecha_pago", None) or self._now_local_naive()
            pago.usuario_id = usuario_id
            pago.monto = total
            if fecha_pago is not None:
                pago.mes = now.month
                pago.año = now.year
            pago.metodo_pago_id = metodo_pago_id
            pago.fecha_pago = now

            # Create new details
            for c in conceptos:
                cantidad = float(c.get('cantidad', 1))
                precio = float(c.get('precio_unitario', 0))
                line_total = cantidad * precio
                detalle = PagoDetalle(
                    pago_id=pago.id,
                    concepto_id=c.get('concepto_id'),
                    descripcion=c.get('descripcion', ''),
                    cantidad=cantidad,
                    precio_unitario=precio,
                    subtotal=line_total,
                    total=line_total
                )
                self.db.add(detalle)

            # Update user status
            usuario = self.db.get(Usuario, usuario_id)
            if usuario:
                self._actualizar_estado_usuario_tras_pago(usuario, now)

            self.db.commit()
            return pago.id


        except Exception as e:
            self.db.rollback()
            logger.error(f"Error en modificar_pago_avanzado: {e}")
            raise

    def actualizar_pago_con_diferencial(
        self,
        pago_id: int,
        nuevo_items: List[Dict[str, Any]],
        nuevo_tipo_cuota_nombre: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update a payment with differential calculation for user expiration.
        
        Algorithm:
        1. SNAPSHOT: Get duration of original item(s)
        2. IDENTIFY NEW: Get duration of new item(s)
        3. CALCULATE DELTA: dias_nuevos - dias_originales
        4. IMPACT USER: Adjust fecha_proximo_vencimiento by delta
        
        Rules:
        - Updates pago.tipo_cuota (historical record)
        - Adjusts usuario.fecha_proximo_vencimiento by delta
        - Does NOT change usuario.tipo_cuota (profile preference)
        """
        pago = self.db.get(Pago, pago_id)
        if not pago:
            raise ValueError(f"Pago con ID {pago_id} no encontrado")

        usuario = self.db.get(Usuario, pago.usuario_id)
        if not usuario:
            raise ValueError(f"Usuario con ID {pago.usuario_id} no encontrado")

        try:
            # ===========================================================
            # STEP 1: SNAPSHOT - Get duration of original item(s)
            # ===========================================================
            detalles_originales = self.db.execute(
                select(PagoDetalle).where(PagoDetalle.pago_id == pago_id)
            ).scalars().all()
            
            dias_originales = 0
            for detalle in detalles_originales:
                # Try to find TipoCuota by matching descripcion
                tipo_original = self.db.execute(
                    select(TipoCuota).where(TipoCuota.nombre == detalle.descripcion)
                ).scalar_one_or_none()
                if tipo_original and tipo_original.duracion_dias:
                    dias_originales += int(tipo_original.duracion_dias) * int(detalle.cantidad or 1)
                else:
                    # Default fallback: assume 30 days per unit
                    dias_originales += 30 * int(detalle.cantidad or 1)
            
            # ===========================================================
            # STEP 2: IDENTIFY NEW - Get duration of new item(s)
            # ===========================================================
            dias_nuevos = 0
            for item in nuevo_items:
                descripcion = str(item.get('descripcion', '')).strip()
                cantidad = int(item.get('cantidad', 1) or 1)
                
                # Try to find TipoCuota by matching descripcion
                tipo_nuevo = self.db.execute(
                    select(TipoCuota).where(TipoCuota.nombre == descripcion)
                ).scalar_one_or_none()
                if tipo_nuevo and tipo_nuevo.duracion_dias:
                    dias_nuevos += int(tipo_nuevo.duracion_dias) * cantidad
                else:
                    # Default fallback: assume 30 days per unit
                    dias_nuevos += 30 * cantidad
            
            # ===========================================================
            # STEP 3: CALCULATE DELTA
            # ===========================================================
            delta = dias_nuevos - dias_originales
            
            # ===========================================================
            # STEP 4: IMPACT USER - Adjust expiration date by delta
            # ===========================================================
            if delta != 0 and usuario.fecha_proximo_vencimiento:
                fecha_actual = usuario.fecha_proximo_vencimiento
                if isinstance(fecha_actual, datetime):
                    fecha_actual = fecha_actual.date()
                nueva_fecha = fecha_actual + timedelta(days=delta)
                usuario.fecha_proximo_vencimiento = nueva_fecha
                logger.info(
                    f"Ajustando vencimiento usuario {usuario.id}: "
                    f"{fecha_actual} -> {nueva_fecha} (delta={delta} días)"
                )
            
            # ===========================================================
            # STEP 5: UPDATE PAGO RECORD
            # ===========================================================
            # Delete existing details
            self.db.execute(
                delete(PagoDetalle).where(PagoDetalle.pago_id == pago_id)
            )
            
            # Calculate new total
            subtotal = sum(
                float(item.get('cantidad', 1)) * float(item.get('precio_unitario', 0))
                for item in nuevo_items
            )
            pago.monto = subtotal
            
            # Update concepto on PAGO record (stores tipo_cuota name for historical record)
            # Note: Using 'concepto' field since Pago model uses this for payment type
            if nuevo_tipo_cuota_nombre:
                pago.concepto = nuevo_tipo_cuota_nombre
            elif nuevo_items:
                # Use first item's descripcion as concepto
                pago.concepto = nuevo_items[0].get('descripcion', '')
            
            # Create new details
            for item in nuevo_items:
                cantidad = float(item.get('cantidad', 1))
                precio = float(item.get('precio_unitario', 0))
                line_total = cantidad * precio
                detalle = PagoDetalle(
                    pago_id=pago.id,
                    concepto_id=item.get('concepto_id'),
                    descripcion=item.get('descripcion', ''),
                    cantidad=cantidad,
                    precio_unitario=precio,
                    subtotal=line_total,
                    total=line_total
                )
                self.db.add(detalle)
            
            self.db.commit()
            
            return {
                'ok': True,
                'pago_id': pago.id,
                'dias_originales': dias_originales,
                'dias_nuevos': dias_nuevos,
                'delta': delta,
                'nuevo_monto': subtotal,
                'nueva_fecha_vencimiento': str(usuario.fecha_proximo_vencimiento) if usuario.fecha_proximo_vencimiento else None
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error en actualizar_pago_con_diferencial: {e}")
            raise


    def eliminar_pago(self, pago_id: int) -> bool:
        """Delete a payment and recalculate user status."""
        pago = self.db.get(Pago, pago_id)
        if not pago:
            return False

        usuario_id = pago.usuario_id
        self.db.delete(pago)
        
        # Also delete payment details
        self.db.execute(
            delete(PagoDetalle).where(PagoDetalle.pago_id == pago_id)
        )
        
        self.db.commit()

        # Recalculate user status
        self._recalcular_estado_usuario(usuario_id)
        
        return True

    def obtener_pago(self, pago_id: int) -> Optional[Pago]:
        """Get payment by ID."""
        return self.db.get(Pago, pago_id)

    def obtener_historial_pagos(
        self, 
        usuario_id: int, 
        limit: Optional[int] = None
    ) -> List[Pago]:
        """Get payment history for a user."""
        stmt = (
            select(Pago)
            .where(Pago.usuario_id == usuario_id)
            .order_by(Pago.fecha_pago.desc())
        )
        if limit:
            stmt = stmt.limit(limit)
        
        return list(self.db.execute(stmt).scalars().all())

    def verificar_pago_actual(
        self, 
        usuario_id: int, 
        mes: int, 
        año: int
    ) -> bool:
        """Check if user has paid for given month/year."""
        stmt = select(func.count(Pago.id)).where(
            Pago.usuario_id == usuario_id,
            Pago.mes == mes,
            Pago.año == año
        )
        count = self.db.execute(stmt).scalar()
        return count > 0

    # =========================================================================
    # ADVANCED PAYMENT (MULTI-CONCEPT)
    # =========================================================================

    def registrar_pago_avanzado(
        self,
        usuario_id: int,
        metodo_pago_id: int,
        conceptos: List[Dict[str, Any]],
        fecha_pago: Optional[datetime] = None,
        monto_personalizado: Optional[float] = None,
        override_mes: Optional[int] = None,
        override_año: Optional[int] = None
    ) -> int:
        """
        Register payment with multiple concepts/line items.
        
        Handles UniqueConstraint(usuario_id, mes, año) by MERGING into existing payment if present.
        
        Args:
            usuario_id: User ID.
            metodo_pago_id: Payment method ID.
            conceptos: List of concepts (items).
            fecha_pago: Actual date of the transaction (defaults to NOW).
            monto_personalizado: Optional total amount override.
            override_mes: Explicitly set the quota month (e.g. paying for past month).
            override_año: Explicitly set the quota year.
        """
        usuario = self.db.get(Usuario, usuario_id)
        if not usuario:
            raise ValueError(f"Usuario con ID {usuario_id} no encontrado")

        if not conceptos:
            raise ValueError("Se requiere al menos un concepto de pago")

        try:
            now = fecha_pago or self._now_local_naive()
            
            # Determine quota period (Effective Month/Year)
            # Use overrides if provided (for back-payments), otherwise use transaction date
            mes_eff = override_mes if override_mes is not None else now.month
            año_eff = override_año if override_año is not None else now.year
            
            # 1. Check for existing payment (Upsert Strategy)
            pago = self.db.execute(
                select(Pago).where(
                    Pago.usuario_id == usuario_id,
                    Pago.mes == mes_eff,
                    Pago.año == año_eff
                )
            ).scalar_one_or_none()
            
            # Calculate total for THIS transaction/batch
            subtotal_batch = sum(
                float(c.get('cantidad', 1)) * float(c.get('precio_unitario', 0))
                for c in conceptos
            )
            comision_batch = self._calcular_comision(subtotal_batch, metodo_pago_id)
            total_batch = subtotal_batch + comision_batch
            
            if monto_personalizado is not None:
                total_batch = float(monto_personalizado)

            if pago:
                # MERGE into existing payment
                pago.monto = total_batch
                pago.metodo_pago_id = metodo_pago_id # Update method to latest used
                pago.fecha_pago = now # Update effective date to latest transaction
                logger.info(f"Actualizando pago para usuario {usuario_id} (Mes {mes_eff}/{año_eff}): {total_batch}.")
            else:
                # CREATE new payment
                pago = Pago(
                    usuario_id=usuario_id,
                    monto=total_batch,
                    mes=mes_eff,
                    año=año_eff,
                    metodo_pago_id=metodo_pago_id,
                    fecha_pago=now
                )
                self.db.add(pago)
            
            self.db.flush() # Ensure we have pago.id

            if pago and pago.id:
                self.db.execute(
                    delete(PagoDetalle).where(PagoDetalle.pago_id == pago.id)
                )

            # Create payment details
            for c in conceptos:
                cantidad = float(c.get('cantidad', 1))
                precio = float(c.get('precio_unitario', 0))
                line_total = cantidad * precio
                detalle = PagoDetalle(
                    pago_id=pago.id,
                    concepto_id=c.get('concepto_id'),
                    descripcion=c.get('descripcion', ''),
                    cantidad=cantidad,
                    precio_unitario=precio,
                    subtotal=line_total,
                    total=line_total 
                )
                self.db.add(detalle)

            # Update user status
            self._actualizar_estado_usuario_tras_pago(usuario, now)

            self.db.commit()
            return pago.id

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error en pago avanzado: {e}")
            raise

    def obtener_datos_cuota_usuario(self, usuario_id: int) -> Optional[Dict[str, Any]]:
        """
        Get quota information for auto-filling payment forms.
        Based on user's assigned 'tipo_cuota'.
        """
        try:
            usuario = self.db.get(Usuario, usuario_id)
            if not usuario or not usuario.tipo_cuota:
                return None
            
            tipo = self.db.execute(
                select(TipoCuota).where(TipoCuota.nombre == usuario.tipo_cuota)
            ).scalar_one_or_none()
            
            if not tipo:
                return None
                
            return {
                "nombre": tipo.nombre,
                "precio": float(tipo.precio),
                "concepto_id": None # Could be mapped if 'conceptos' table had a link to tipos_cuota, but it doesn't seem so.
            }
        except Exception as e:
            logger.error(f"Error obteniendo datos cuota usuario {usuario_id}: {e}")
            return None

    def obtener_detalles_pago(self, pago_id: int) -> List[PagoDetalle]:
        """Get payment details/line items."""
        stmt = select(PagoDetalle).where(PagoDetalle.pago_id == pago_id)
        return list(self.db.execute(stmt).scalars().all())

    # =========================================================================
    # PAYMENT METHODS
    # =========================================================================

    def obtener_metodos_pago(self, solo_activos: bool = True) -> List[Dict]:
        """Get payment methods."""
        stmt = select(MetodoPago)
        if solo_activos:
            stmt = stmt.where(MetodoPago.activo == True)
        
        methods = self.db.execute(stmt).scalars().all()
        return [
            {
                'id': m.id,
                'nombre': m.nombre,
                'icono': m.icono,
                'color': m.color,
                'comision': float(m.comision or 0),
                'activo': m.activo,
                'descripcion': m.descripcion
            }
            for m in methods
        ]

    def obtener_metodo_pago(self, metodo_id: int) -> Optional[MetodoPago]:
        """Get payment method by ID."""
        return self.db.get(MetodoPago, metodo_id)

    def crear_metodo_pago(self, data: Dict[str, Any]) -> int:
        """Create a new payment method."""
        metodo = MetodoPago(
            nombre=data.get('nombre', ''),
            icono=data.get('icono'),
            color=data.get('color', '#3498db'),
            comision=float(data.get('comision', 0)),
            activo=data.get('activo', True),
            descripcion=data.get('descripcion')
        )
        self.db.add(metodo)
        self.db.commit()
        self.db.refresh(metodo)
        return metodo.id

    def actualizar_metodo_pago(self, metodo_id: int, data: Dict[str, Any]) -> bool:
        """Update a payment method."""
        metodo = self.db.get(MetodoPago, metodo_id)
        if not metodo:
            return False

        for key in ['nombre', 'icono', 'color', 'comision', 'activo', 'descripcion']:
            if key in data:
                setattr(metodo, key, data[key])

        self.db.commit()
        return True

    def eliminar_metodo_pago(self, metodo_id: int) -> bool:
        """Delete a payment method."""
        metodo = self.db.get(MetodoPago, metodo_id)
        if not metodo:
            return False
        
        self.db.delete(metodo)
        self.db.commit()
        return True

    # =========================================================================
    # PAYMENT CONCEPTS
    # =========================================================================

    def obtener_conceptos_pago(self, solo_activos: bool = True) -> List[Dict]:
        """Get payment concepts."""
        stmt = select(ConceptoPago)
        if solo_activos:
            stmt = stmt.where(ConceptoPago.activo == True)
        
        conceptos = self.db.execute(stmt).scalars().all()
        return [
            {
                'id': c.id,
                'nombre': c.nombre,
                'descripcion': c.descripcion,
                'precio_sugerido': float(c.precio_base or 0),
                'activo': c.activo
            }
            for c in conceptos
        ]

    def crear_concepto_pago(self, data: Dict[str, Any]) -> int:
        """Create a payment concept."""
        concepto = ConceptoPago(
            nombre=data.get('nombre', ''),
            descripcion=data.get('descripcion'),
            precio_base=float(data.get('precio_sugerido', 0)),
            activo=data.get('activo', True)
        )
        self.db.add(concepto)
        self.db.commit()
        self.db.refresh(concepto)
        return concepto.id

    def actualizar_concepto_pago(self, concepto_id: int, data: Dict[str, Any]) -> bool:
        """Update a payment concept."""
        concepto = self.db.get(ConceptoPago, concepto_id)
        if not concepto:
            return False

        for key in ['nombre', 'descripcion', 'activo']:
            if key in data:
                setattr(concepto, key, data[key])
        # Handle precio_sugerido -> precio_base mapping
        if 'precio_sugerido' in data:
            concepto.precio_base = data['precio_sugerido']

        self.db.commit()
        return True

    def eliminar_concepto_pago(self, concepto_id: int) -> bool:
        """Delete a payment concept."""
        concepto = self.db.get(ConceptoPago, concepto_id)
        if not concepto:
            return False
        
        self.db.delete(concepto)
        self.db.commit()
        return True

    # =========================================================================
    # USER STATUS MANAGEMENT
    # =========================================================================

    def _recalcular_estado_usuario(self, usuario_id: int) -> Dict[str, Any]:
        """
        Recalculate user's next due date, last payment, and overdue quotas.
        
        - Uses last payment if exists
        - Falls back to registration date
        - Deactivates if 3+ overdue quotas
        """
        usuario = self.db.get(Usuario, usuario_id)
        if not usuario:
            return {'error': 'Usuario no encontrado'}

        # Get user's quota type duration
        duracion_dias = 30
        if usuario.tipo_cuota:
            tipo = self.db.execute(
                select(TipoCuota).where(TipoCuota.nombre == usuario.tipo_cuota)
            ).scalar_one_or_none()
            if tipo:
                duracion_dias = tipo.duracion_dias or 30

        # Get last payment
        ultimo_pago = self.db.execute(
            select(Pago)
            .where(Pago.usuario_id == usuario_id)
            .order_by(Pago.fecha_pago.desc())
            .limit(1)
        ).scalar_one_or_none()

        hoy = self._today_local_date()
        cuotas_previas = usuario.cuotas_vencidas or 0

        if duracion_dias <= 0:
            duracion_dias = 30

        exento = self._is_exempt_role(getattr(usuario, 'rol', None))

        base_date: date
        ultimo_pago_date: Optional[date] = None
        if ultimo_pago and ultimo_pago.fecha_pago:
            fecha_ref = ultimo_pago.fecha_pago
            if isinstance(fecha_ref, datetime):
                fecha_ref = fecha_ref.date()
            ultimo_pago_date = fecha_ref
            base_date = fecha_ref
            usuario.ultimo_pago = fecha_ref
        else:
            fecha_registro = usuario.fecha_registro or hoy
            if isinstance(fecha_registro, datetime):
                fecha_registro = fecha_registro.date()
            base_date = fecha_registro

        primer_vencimiento = base_date + timedelta(days=duracion_dias)
        if hoy <= primer_vencimiento:
            proximo_vencimiento = primer_vencimiento
            cuotas_vencidas_calc = 0
        else:
            dias_desde_primer_venc = (hoy - primer_vencimiento).days
            ciclos_vencidos = (dias_desde_primer_venc + duracion_dias - 1) // duracion_dias
            if ciclos_vencidos < 1:
                ciclos_vencidos = 1
            cuotas_vencidas_calc = ciclos_vencidos
            proximo_vencimiento = primer_vencimiento + timedelta(days=duracion_dias * ciclos_vencidos)

        usuario.fecha_proximo_vencimiento = proximo_vencimiento

        if exento:
            cuotas_vencidas = 0
        else:
            cuotas_vencidas = int(cuotas_vencidas_calc)

        usuario.cuotas_vencidas = cuotas_vencidas

        if (not exento) and cuotas_vencidas >= 3 and cuotas_previas < 3:
            try:
                motivo = f"{cuotas_vencidas} cuotas vencidas"
                self.desactivar_usuario_por_cuotas_vencidas(int(usuario_id), motivo=motivo)
                usuario = self.db.get(Usuario, usuario_id) or usuario
                return {
                    'usuario_id': usuario_id,
                    'fecha_proximo_vencimiento': usuario.fecha_proximo_vencimiento,
                    'cuotas_vencidas': cuotas_vencidas,
                    'cuotas_previas': cuotas_previas,
                    'activo': False,
                    'desactivado': True,
                }
            except Exception:
                pass

        desactivado = False
        if (not exento) and cuotas_vencidas >= 3:
            desactivado = True
            if usuario.activo:
                usuario.activo = False
                logger.warning(f"Usuario {usuario_id} desactivado por {cuotas_vencidas} cuotas vencidas")

        self.db.commit()

        return {
            'usuario_id': usuario_id,
            'fecha_proximo_vencimiento': usuario.fecha_proximo_vencimiento,
            'cuotas_vencidas': cuotas_vencidas,
            'cuotas_previas': cuotas_previas,
            'activo': usuario.activo,
            'desactivado': desactivado,
        }

    def _verificar_y_procesar_morosidad(
        self, 
        usuario_id: int, 
        cuotas_previas: int, 
        cuotas_actuales: int
    ) -> bool:
        """
        Process delinquency when user crosses threshold from <3 to >=3 overdue quotas.
        """
        if cuotas_previas < 3 and cuotas_actuales >= 3:
            usuario = self.db.get(Usuario, usuario_id)
            if not usuario:
                return False

            rol = (usuario.rol or '').lower()
            if rol in ('profesor', 'dueño', 'owner'):
                return False

            self._desactivar_usuario_por_cuotas(usuario, cuotas_actuales)
            return True

        return False

    def _desactivar_usuario_por_cuotas(
        self, 
        usuario: Usuario, 
        cuotas_vencidas: int
    ) -> None:
        """Deactivate user due to overdue quotas."""
        usuario.activo = False
        
        # Log the action
        logger.warning(
            f"Usuario {usuario.id} ({usuario.nombre}) desactivado: "
            f"{cuotas_vencidas} cuotas vencidas"
        )
        
        self.db.commit()

    def _actualizar_estado_usuario_tras_pago(
        self, 
        usuario: Usuario, 
        fecha_pago: datetime
    ) -> None:
        """Update user status after payment."""
        duracion_dias = 30
        if usuario.tipo_cuota:
            tipo = self.db.execute(
                select(TipoCuota).where(TipoCuota.nombre == usuario.tipo_cuota)
            ).scalar_one_or_none()
            if tipo:
                duracion_dias = tipo.duracion_dias or 30

        fecha = fecha_pago.date() if isinstance(fecha_pago, datetime) else fecha_pago
        proximo = fecha + timedelta(days=duracion_dias)

        usuario.fecha_proximo_vencimiento = proximo
        usuario.ultimo_pago = fecha
        usuario.activo = True
        usuario.cuotas_vencidas = 0

    def desactivar_usuario_por_cuotas_vencidas(
        self, 
        usuario_id: int, 
        motivo: str = "3 cuotas vencidas"
    ) -> bool:
        """
        Deactivate a user due to overdue quotas.
        Respects role exemptions (professors, owners).
        """
        usuario = self.db.get(Usuario, usuario_id)
        if not usuario:
            return False

        if self._is_exempt_role(getattr(usuario, 'rol', None)):
            logger.info(f"Usuario {usuario_id} exento de desactivación (rol: {(getattr(usuario, 'rol', None) or '')})")
            return False

        usuario.activo = False
        
        # Register state change
        self.user_repo.registrar_cambio_estado(
            usuario_id, 
            'inactivo', 
            'desactivacion_cuotas', 
            motivo
        )
        
        self.db.commit()
        try:
            WhatsAppDispatchService(self.db).send_deactivation(int(usuario_id), str(motivo or "cuotas vencidas"))
        except Exception:
            pass
        return True

    # =========================================================================
    # COMMISSION CALCULATION
    # =========================================================================

    def _calcular_comision(
        self, 
        monto_base: float, 
        metodo_pago_id: Optional[int]
    ) -> float:
        """Calculate commission based on payment method."""
        if not metodo_pago_id:
            return 0.0

        metodo = self.db.get(MetodoPago, metodo_pago_id)
        if not metodo or not metodo.comision:
            return 0.0

        porcentaje = float(metodo.comision)
        return round(monto_base * porcentaje / 100, 2)

    def calcular_total_con_comision(
        self, 
        subtotal: float, 
        metodo_pago_id: Optional[int]
    ) -> Dict[str, float]:
        """Calculate total with commission breakdown."""
        comision = self._calcular_comision(subtotal, metodo_pago_id)
        return {
            'subtotal': subtotal,
            'comision': comision,
            'total': subtotal + comision
        }

    # =========================================================================
    # MOROSITY PROCESSING
    # =========================================================================

    def procesar_usuarios_morosos(self) -> Dict[str, Any]:
        """
        Process all delinquent users:
        - Increment overdue quotas
        - Deactivate those with 3+ overdue
        """
        hoy = self._today_local_date()
        
        # Get all active members with overdue payments
        stmt = select(Usuario).where(
            Usuario.activo == True,
            Usuario.rol == 'socio',
            Usuario.fecha_proximo_vencimiento < hoy
        )
        
        usuarios_morosos = self.db.execute(stmt).scalars().all()
        
        procesados = 0
        desactivados = 0
        
        for usuario in usuarios_morosos:
            resultado = self._recalcular_estado_usuario(usuario.id)
            procesados += 1
            
            if resultado.get('desactivado'):
                desactivados += 1

        return {
            'procesados': procesados,
            'desactivados': desactivados,
            'fecha_proceso': hoy.isoformat()
        }

    def procesar_usuarios_morosos_con_whatsapp(
        self, 
        enviar_recordatorios: bool = True,
        whatsapp_manager = None
    ) -> Dict[str, Any]:
        """
        Process all delinquent users with WhatsApp notifications:
        - Increment overdue quotas
        - Deactivate those with 3+ overdue
        - Send WhatsApp reminders
        
        Args:
            enviar_recordatorios: If True, send WhatsApp reminders
            whatsapp_manager: Optional WhatsAppManager instance for sending messages
        
        Returns:
            Dict with processed, deactivated, reminders_sent counts
        """
        hoy = self._today_local_date()
        
        # Get all active members with overdue payments
        stmt = select(Usuario).where(
            Usuario.activo == True,
            Usuario.rol == 'socio',
            Usuario.fecha_proximo_vencimiento < hoy
        )
        
        usuarios_morosos = self.db.execute(stmt).scalars().all()
        
        procesados = 0
        desactivados = 0
        recordatorios_enviados = 0
        errores_envio = []
        
        for usuario in usuarios_morosos:
            resultado = self._recalcular_estado_usuario(usuario.id)
            procesados += 1
            
            if resultado.get('desactivado'):
                desactivados += 1
                # Send deactivation notification via WhatsApp
                if enviar_recordatorios and whatsapp_manager:
                    try:
                        whatsapp_manager.enviar_notificacion_desactivacion(
                            usuario_id=usuario.id,
                            motivo=f"{resultado.get('cuotas_vencidas', 3)} cuotas vencidas",
                            force_send=False
                        )
                    except Exception as e:
                        errores_envio.append({'usuario_id': usuario.id, 'error': str(e)})
            elif enviar_recordatorios and whatsapp_manager:
                # Send overdue reminder for non-deactivated users
                cuotas = resultado.get('cuotas_vencidas', 0)
                if cuotas > 0:
                    try:
                        whatsapp_manager.enviar_recordatorio_cuota_vencida(usuario_id=usuario.id)
                        recordatorios_enviados += 1
                    except Exception as e:
                        errores_envio.append({'usuario_id': usuario.id, 'error': str(e)})

        return {
            'procesados': procesados,
            'desactivados': desactivados,
            'recordatorios_enviados': recordatorios_enviados,
            'errores_envio': len(errores_envio),
            'fecha_proceso': hoy.isoformat()
        }

    def procesar_recordatorios_proximos_vencimientos(
        self,
        dias_antes: int = 3,
        whatsapp_manager = None
    ) -> Dict[str, Any]:
        """
        Send reminders to users with upcoming payment due dates.
        
        Args:
            dias_antes: Days before due date to send reminder (default 3)
            whatsapp_manager: Optional WhatsAppManager instance for sending messages
        
        Returns:
            Dict with count of reminders sent
        """
        hoy = self._today_local_date()
        fecha_limite = hoy + timedelta(days=dias_antes)
        
        # Get users with payments due in the next N days
        stmt = select(Usuario).where(
            Usuario.activo == True,
            Usuario.rol == 'socio',
            Usuario.fecha_proximo_vencimiento >= hoy,
            Usuario.fecha_proximo_vencimiento <= fecha_limite
        )
        
        usuarios = self.db.execute(stmt).scalars().all()
        
        recordatorios_enviados = 0
        errores = []
        
        for usuario in usuarios:
            if whatsapp_manager and usuario.telefono:
                try:
                    # Calculate days until due
                    dias_restantes = (usuario.fecha_proximo_vencimiento - hoy).days if usuario.fecha_proximo_vencimiento else 0
                    
                    # Get gym name
                    result = self.db.execute(
                        text("SELECT valor FROM gym_config WHERE clave = 'gym_name' LIMIT 1")
                    )
                    row = result.fetchone()
                    gym_name = row[0] if row else 'el gimnasio'
                    
                    user_data = {
                        'phone': usuario.telefono,
                        'name': usuario.nombre or 'Usuario',
                        'due_date': usuario.fecha_proximo_vencimiento.strftime('%d/%m/%Y') if usuario.fecha_proximo_vencimiento else 'N/A',
                        'days_remaining': dias_restantes,
                        'gym_name': gym_name
                    }
                    
                    whatsapp_manager.send_overdue_payment_notification(user_data, to=usuario.telefono)
                    recordatorios_enviados += 1
                except Exception as e:
                    errores.append({'usuario_id': usuario.id, 'error': str(e)})
        
        return {
            'usuarios_proximos': len(usuarios),
            'recordatorios_enviados': recordatorios_enviados,
            'errores': len(errores),
            'fecha_proceso': hoy.isoformat()
        }

    def obtener_usuarios_morosos(self) -> List[Dict[str, Any]]:
        """Get list of delinquent users."""
        hoy = self._today_local_date()
        
        stmt = select(Usuario).where(
            Usuario.activo == True,
            Usuario.rol == 'socio',
            Usuario.fecha_proximo_vencimiento < hoy
        )
        
        usuarios = self.db.execute(stmt).scalars().all()
        
        return [
            {
                'id': u.id,
                'nombre': u.nombre,
                'telefono': u.telefono,
                'fecha_vencimiento': u.fecha_proximo_vencimiento.isoformat() 
                    if u.fecha_proximo_vencimiento else None,
                'cuotas_vencidas': u.cuotas_vencidas or 0
            }
            for u in usuarios
        ]

    # =========================================================================
    # STATISTICS
    # =========================================================================

    def obtener_estadisticas_pagos(self, año: Optional[int] = None) -> Dict[str, Any]:
        """Get payment statistics for a year."""
        año = año or self._today_local_date().year
        
        # Total payments and amount
        stmt = select(
            func.count(Pago.id),
            func.sum(Pago.monto)
        ).where(Pago.año == año)
        
        result = self.db.execute(stmt).first()
        total_pagos = result[0] or 0
        total_monto = float(result[1] or 0)

        # Monthly breakdown
        stmt_mensual = select(
            Pago.mes,
            func.count(Pago.id),
            func.sum(Pago.monto)
        ).where(Pago.año == año).group_by(Pago.mes)
        
        mensual = {}
        for row in self.db.execute(stmt_mensual):
            mensual[row[0]] = {
                'count': row[1],
                'total': float(row[2] or 0)
            }

        return {
            'año': año,
            'total_pagos': total_pagos,
            'total_monto': total_monto,
            'por_mes': mensual
        }

    # =========================================================================
    # SUBSCRIPTION TYPES (TIPOS DE CUOTA)
    # =========================================================================

    def obtener_tipos_cuota(self, solo_activos: bool = True) -> List[Dict]:
        """Get subscription types (quota types)."""
        stmt = select(TipoCuota)
        if solo_activos:
            stmt = stmt.where(TipoCuota.activo == True)
        
        tipos = self.db.execute(stmt).scalars().all()
        return [
            {
                'id': t.id,
                'nombre': t.nombre,
                'precio': float(t.precio or 0),
                'duracion_dias': t.duracion_dias or 30,
                'activo': t.activo,
                'descripcion': getattr(t, 'descripcion', None),
                'icono_path': getattr(t, 'icono_path', None)
            }
            for t in tipos
        ]

    def obtener_tipos_cuota_activos(self) -> List[Dict]:
        """Get active subscription types sorted by price."""
        tipos = self.obtener_tipos_cuota(solo_activos=True)
        return sorted(tipos, key=lambda t: (t.get('precio', 0), t.get('nombre', '')))

    def obtener_tipo_cuota(self, tipo_id: int) -> Optional[TipoCuota]:
        """Get subscription type by ID."""
        return self.db.get(TipoCuota, tipo_id)

    def crear_tipo_cuota(self, data: Dict[str, Any]) -> int:
        """Create a subscription type."""
        tipo = TipoCuota(
            nombre=data.get('nombre', ''),
            precio=float(data.get('precio', 0)),
            duracion_dias=int(data.get('duracion_dias', 30)),
            activo=data.get('activo', True)
        )
        # Set optional fields if present
        if 'descripcion' in data:
            tipo.descripcion = data['descripcion']
        if 'icono_path' in data:
            tipo.icono_path = data['icono_path']
            
        self.db.add(tipo)
        self.db.commit()
        self.db.refresh(tipo)
        return tipo.id

    def actualizar_tipo_cuota(self, tipo_id: int, data: Dict[str, Any]) -> bool:
        """Update a subscription type."""
        tipo = self.db.get(TipoCuota, tipo_id)
        if not tipo:
            return False

        for key in ['nombre', 'precio', 'duracion_dias', 'activo', 'descripcion', 'icono_path']:
            if key in data:
                val = data[key]
                if key == 'precio':
                    val = float(val)
                elif key == 'duracion_dias':
                    val = int(val)
                setattr(tipo, key, val)

        self.db.commit()
        return True

    def eliminar_tipo_cuota(self, tipo_id: int) -> bool:
        """Delete a subscription type."""
        tipo = self.db.get(TipoCuota, tipo_id)
        if not tipo:
            return False
        
        self.db.delete(tipo)
        self.db.commit()
        return True

    # =========================================================================
    # PAYMENTS QUERY BY DATE
    # =========================================================================

    def obtener_pagos_por_fecha(
        self, 
        start: Optional[str] = None, 
        end: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get payments within a date range."""
        from sqlalchemy.orm import joinedload
        
        stmt = (
            select(Pago)
            .options(joinedload(Pago.usuario))
            .order_by(Pago.fecha_pago.desc())
        )
        
        if start:
            try:
                start_date = datetime.strptime(start, "%Y-%m-%d").date()
                stmt = stmt.where(func.date(Pago.fecha_pago) >= start_date)
            except ValueError:
                pass
                
        if end:
            try:
                end_date = datetime.strptime(end, "%Y-%m-%d").date()
                stmt = stmt.where(func.date(Pago.fecha_pago) <= end_date)
            except ValueError:
                pass
        
        pagos = self.db.execute(stmt).scalars().all()

        # Map latest emitted receipt number (ComprobantePago.numero_comprobante) per payment
        recibo_por_pago: Dict[int, str] = {}
        try:
            pago_ids = [int(p.id) for p in pagos if getattr(p, 'id', None) is not None]
        except Exception:
            pago_ids = []
        if pago_ids:
            try:
                comps = (
                    self.db.execute(
                        select(ComprobantePago)
                        .where(
                            ComprobantePago.pago_id.in_(pago_ids),
                            ComprobantePago.estado == 'emitido',
                        )
                        .order_by(ComprobantePago.pago_id.asc(), ComprobantePago.fecha_creacion.desc())
                    )
                    .scalars()
                    .all()
                )
                for c in comps:
                    try:
                        pid = int(c.pago_id)
                    except Exception:
                        continue
                    if pid not in recibo_por_pago:
                        try:
                            recibo_por_pago[pid] = str(c.numero_comprobante)
                        except Exception:
                            pass
            except Exception:
                pass
        
        # Get payment method names
        metodos = {m.id: m.nombre for m in self.db.execute(select(MetodoPago)).scalars().all()}
        
        return [
            {
                'id': p.id,
                'usuario_id': p.usuario_id,
                'usuario_nombre': p.usuario.nombre if p.usuario else None,
                'dni': p.usuario.dni if p.usuario else None,
                'monto': float(p.monto or 0),
                'mes': p.mes,
                'año': p.año,
                'fecha_pago': p.fecha_pago.isoformat() if p.fecha_pago else None,
                'metodo_pago_id': p.metodo_pago_id,
                'metodo_pago': metodos.get(p.metodo_pago_id) if p.metodo_pago_id else None,
                'recibo_numero': recibo_por_pago.get(int(p.id))
            }
            for p in pagos
        ]

    def obtener_pagos_por_fecha_paginados(
        self,
        start: Optional[str] = None,
        end: Optional[str] = None,
        usuario_id: Optional[int] = None,
        metodo_id: Optional[int] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        from sqlalchemy.orm import joinedload

        try:
            lim = max(1, min(int(limit or 50), 100))
        except Exception:
            lim = 50
        try:
            off = max(0, int(offset or 0))
        except Exception:
            off = 0

        stmt = (
            select(Pago)
            .options(joinedload(Pago.usuario))
            .order_by(Pago.fecha_pago.desc())
        )

        count_stmt = select(func.count(Pago.id))

        if start:
            try:
                start_date = datetime.strptime(start, "%Y-%m-%d").date()
                stmt = stmt.where(func.date(Pago.fecha_pago) >= start_date)
                count_stmt = count_stmt.where(func.date(Pago.fecha_pago) >= start_date)
            except ValueError:
                pass

        if end:
            try:
                end_date = datetime.strptime(end, "%Y-%m-%d").date()
                stmt = stmt.where(func.date(Pago.fecha_pago) <= end_date)
                count_stmt = count_stmt.where(func.date(Pago.fecha_pago) <= end_date)
            except ValueError:
                pass

        if usuario_id is not None:
            try:
                uid = int(usuario_id)
                stmt = stmt.where(Pago.usuario_id == uid)
                count_stmt = count_stmt.where(Pago.usuario_id == uid)
            except Exception:
                pass

        if metodo_id is not None:
            try:
                mid = int(metodo_id)
                stmt = stmt.where(Pago.metodo_pago_id == mid)
                count_stmt = count_stmt.where(Pago.metodo_pago_id == mid)
            except Exception:
                pass

        total = 0
        try:
            total = int(self.db.execute(count_stmt).scalar() or 0)
        except Exception:
            total = 0

        pagos = self.db.execute(stmt.limit(lim).offset(off)).scalars().all()

        recibo_por_pago: Dict[int, str] = {}
        try:
            pago_ids = [int(p.id) for p in pagos if getattr(p, 'id', None) is not None]
        except Exception:
            pago_ids = []
        if pago_ids:
            try:
                comps = (
                    self.db.execute(
                        select(ComprobantePago)
                        .where(
                            ComprobantePago.pago_id.in_(pago_ids),
                            ComprobantePago.estado == 'emitido',
                        )
                        .order_by(ComprobantePago.pago_id.asc(), ComprobantePago.fecha_creacion.desc())
                    )
                    .scalars()
                    .all()
                )
                for c in comps:
                    try:
                        pid = int(c.pago_id)
                    except Exception:
                        continue
                    if pid not in recibo_por_pago:
                        try:
                            recibo_por_pago[pid] = str(c.numero_comprobante)
                        except Exception:
                            pass
            except Exception:
                pass

        metodos = {m.id: m.nombre for m in self.db.execute(select(MetodoPago)).scalars().all()}

        items = [
            {
                'id': p.id,
                'usuario_id': p.usuario_id,
                'usuario_nombre': p.usuario.nombre if p.usuario else None,
                'dni': p.usuario.dni if p.usuario else None,
                'monto': float(p.monto or 0),
                'mes': p.mes,
                'anio': p.año,
                'fecha_pago': p.fecha_pago.isoformat() if p.fecha_pago else None,
                'metodo_pago_id': p.metodo_pago_id,
                'metodo_pago': metodos.get(p.metodo_pago_id) if p.metodo_pago_id else None,
                'recibo_numero': recibo_por_pago.get(int(p.id)) if getattr(p, 'id', None) is not None else None,
                'estado': getattr(p, 'estado', None),
                # tipo_cuota: Use pago's concepto (historical), then fallback to user's tipo_cuota
                'tipo_cuota': getattr(p, 'concepto', None) or (p.usuario.tipo_cuota if p.usuario else None),
            }
            for p in pagos
        ]

        return {"items": items, "total": total}

    def obtener_usuario_por_id(self, usuario_id: int) -> Optional[Usuario]:
        """Get user by ID."""
        return self.db.get(Usuario, usuario_id)

    def obtener_pago_resumen(self, pago_id: int) -> Optional[Dict[str, Any]]:
        """
        Get complete payment info with user and details.
        Returns dict with pago, usuario_nombre, dni, detalles, etc.
        """
        pago = self.db.get(Pago, pago_id)
        if not pago:
            return None

        usuario = self.db.get(Usuario, pago.usuario_id)
        detalles = self.obtener_detalles_pago(pago_id)
        metodo = self.db.get(MetodoPago, pago.metodo_pago_id) if pago.metodo_pago_id else None

        # Calculate total from details
        total_detalles = sum(
            float(d.cantidad or 1) * float(d.precio_unitario or 0)
            for d in detalles
        )

        return {
            'id': pago.id,
            'usuario_id': pago.usuario_id,
            'usuario_nombre': usuario.nombre if usuario else None,
            'dni': usuario.dni if usuario else None,
            'monto': float(pago.monto or 0),
            'mes': pago.mes,
            'año': pago.año,
            'fecha_pago': pago.fecha_pago.isoformat() if pago.fecha_pago else None,
            'metodo_pago_id': pago.metodo_pago_id,
            'metodo_pago_nombre': metodo.nombre if metodo else None,
            'comision_porcentaje': float(metodo.comision or 0) if metodo else 0,
            'total_detalles': total_detalles,
            'cantidad_lineas': len(detalles),
            # tipo_cuota: Use pago's concepto (historical), then fallback to user's tipo_cuota
            'tipo_cuota_nombre': pago.concepto or (usuario.tipo_cuota if usuario else None),
            'detalles': [
                {
                    'id': d.id,
                    'pago_id': d.pago_id,
                    'concepto_id': d.concepto_id,
                    'descripcion': d.descripcion,
                    'cantidad': float(d.cantidad or 1),
                    'precio_unitario': float(d.precio_unitario or 0),
                    'subtotal': float(d.subtotal or 0)
                }
                for d in detalles
            ]
        }

    # ========== Receipt Numbering Config ==========

    _RECIBO_TIPO_COMPROBANTE = "recibo"

    def get_next_receipt_number(self) -> str:
        """Get next receipt number based on configured pattern."""
        try:
            config = self.get_receipt_numbering_config()
            prefix = config.get('prefix', 'REC')
            current = config.get('current_number', 1)
            padding = config.get('padding', 8) # Default 8 per legacy
            separador = config.get('separador', '-')
            
            # Legacy format often: REC-00000001
            # But let's follow config: prefix + separator + padded_number
            # If separator is empty, then just prefix + padded.
            
            num_str = str(current).zfill(padding)
            if separador:
                return f"{prefix}{separador}{num_str}"
            return f"{prefix}{num_str}"
            
        except Exception as e:
            logger.error(f"Error getting next receipt number: {e}")
            return "REC-00000001"

    def get_receipt_numbering_config(self) -> Dict[str, Any]:
        """Get receipt numbering configuration from NumeracionComprobantes."""
        try:
            stmt = (
                select(NumeracionComprobante)
                .where(
                    NumeracionComprobante.activo == True,
                    NumeracionComprobante.tipo_comprobante == self._RECIBO_TIPO_COMPROBANTE,
                )
                .limit(1)
            )
            nc = self.db.execute(stmt).scalar_one_or_none()
            
            if nc:
                return {
                    'prefix': nc.prefijo or 'REC',
                    'current_number': nc.numero_inicial,
                    'padding': nc.longitud_numero or 8,
                    'reset_yearly': nc.reiniciar_anual,
                    'separador': nc.separador or '-'
                }
            
            # Default if no config
            return {
                'prefix': 'REC',
                'current_number': 1,
                'padding': 8,
                'reset_yearly': False,
                'separador': '-'
            }
        except Exception as e:
            logger.error(f"Error getting receipt config: {e}")
            return {'prefix': 'REC', 'current_number': 1}

    def save_receipt_numbering_config(self, config: Dict[str, Any]) -> bool:
        """Save receipt numbering configuration."""
        try:
            stmt = (
                select(NumeracionComprobante)
                .where(
                    NumeracionComprobante.activo == True,
                    NumeracionComprobante.tipo_comprobante == self._RECIBO_TIPO_COMPROBANTE,
                )
                .limit(1)
            )
            nc = self.db.execute(stmt).scalar_one_or_none()
            
            if not nc:
                nc = NumeracionComprobante(activo=True, tipo_comprobante=self._RECIBO_TIPO_COMPROBANTE)
                self.db.add(nc)
            
            if 'prefix' in config:
                nc.prefijo = config['prefix']
            if 'current_number' in config:
                nc.numero_inicial = int(config['current_number'])
            if 'padding' in config:
                nc.longitud_numero = int(config['padding'])
            if 'reset_yearly' in config:
                nc.reiniciar_anual = bool(config['reset_yearly'])
            if 'separador' in config:
                nc.separador = config['separador']
                
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error saving receipt config: {e}")
            self.db.rollback()
            return False

    def increment_receipt_number(self) -> str:
        """Increment and return new receipt number."""
        try:
            stmt = (
                select(NumeracionComprobante)
                .where(
                    NumeracionComprobante.activo == True,
                    NumeracionComprobante.tipo_comprobante == self._RECIBO_TIPO_COMPROBANTE,
                )
                .limit(1)
            )
            nc = self.db.execute(stmt).scalar_one_or_none()
            
            if not nc:
                nc = NumeracionComprobante(
                    tipo_comprobante=self._RECIBO_TIPO_COMPROBANTE,
                    prefijo='REC', 
                    numero_inicial=1, 
                    longitud_numero=8, 
                    activo=True,
                    separador='-'
                )
                self.db.add(nc)
                self.db.commit()
                self.db.refresh(nc)
            
            current = nc.numero_inicial
            
            # Prepare formatted string BEFORE increment
            prefix = nc.prefijo or 'REC'
            padding = nc.longitud_numero or 8
            separador = nc.separador or '-'
            
            num_str = str(current).zfill(padding)
            formatted = f"{prefix}{separador}{num_str}" if separador else f"{prefix}{num_str}"
            
            # Increment for NEXT time
            nc.numero_inicial += 1
            self.db.commit()
            
            return formatted
        except Exception as e:
            logger.error(f"Error incrementing receipt: {e}")
            return "REC-ERROR"

    # ========== Comprobantes (Receipt Records) ==========

    def obtener_comprobante_por_pago(self, pago_id: int) -> Optional[Dict[str, Any]]:
        """Get last emitted comprobante for a payment using ORM."""
        try:
            stmt = (
                select(ComprobantePago)
                .where(ComprobantePago.pago_id == pago_id, ComprobantePago.estado == 'emitido')
                .order_by(ComprobantePago.fecha_creacion.desc())
                .limit(1)
            )
            comp = self.db.execute(stmt).scalar_one_or_none()
            
            if comp:
                return {
                    'id': comp.id,
                    'numero_comprobante': comp.numero_comprobante,
                    'fecha_creacion': comp.fecha_creacion,
                    'estado': comp.estado,
                    'archivo_pdf': comp.archivo_pdf
                }
            return None
        except Exception as e:
            logger.error(f"Error getting comprobante: {e}")
            return None

    def crear_comprobante(
        self,
        tipo_comprobante: str,
        pago_id: int,
        usuario_id: int,
        monto_total: float,
        emitido_por: Optional[str] = None
    ) -> Optional[int]:
        """Create a new comprobante (receipt record) using ORM."""
        try:
            numero = self.increment_receipt_number()
            
            nuevo_comprobante = ComprobantePago(
                tipo_comprobante=tipo_comprobante,
                pago_id=pago_id,
                usuario_id=usuario_id,
                monto_total=monto_total,
                numero_comprobante=numero,
                emitido_por=emitido_por,
                estado='emitido',
                fecha_creacion=self._now_local_naive()
            )
            
            self.db.add(nuevo_comprobante)
            self.db.commit()
            self.db.refresh(nuevo_comprobante)
            return nuevo_comprobante.id
            
        except Exception as e:
            logger.error(f"Error creating comprobante: {e}")
            self.db.rollback()
            return None

    def obtener_comprobante(self, comprobante_id: int) -> Optional[Dict[str, Any]]:
        """Get comprobante by ID using ORM."""
        try:
            comp = self.db.get(ComprobantePago, comprobante_id)
            if comp:
                return {
                    'id': comp.id,
                    'numero_comprobante': comp.numero_comprobante,
                    'fecha_creacion': comp.fecha_creacion,
                    'estado': comp.estado,
                    'archivo_pdf': comp.archivo_pdf
                }
            return None
        except Exception as e:
            logger.error(f"Error getting comprobante: {e}")
            return None

    def actualizar_comprobante_pdf(self, comprobante_id: int, filepath: str) -> bool:
        """Update comprobante with PDF file path using ORM."""
        try:
            comp = self.db.get(ComprobantePago, comprobante_id)
            if comp:
                comp.archivo_pdf = filepath
                self.db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Error updating comprobante PDF: {e}")
            self.db.rollback()
            return False

    def obtener_profesor_nombre(self, profesor_user_id: Optional[int] = None, profesor_id: Optional[int] = None) -> Optional[str]:
        """Get professor name from user ID or professor ID."""
        try:
            if profesor_user_id:
                result = self.db.execute(
                    text("SELECT nombre FROM usuarios WHERE id = :id"),
                    {'id': profesor_user_id}
                )
                row = result.fetchone()
                if row and row[0]:
                    return str(row[0])
            elif profesor_id:
                result = self.db.execute(
                    text("""
                        SELECT u.nombre FROM profesores p 
                        JOIN usuarios u ON p.usuario_id = u.id 
                        WHERE p.id = :id
                    """),
                    {'id': profesor_id}
                )
                row = result.fetchone()
                if row and row[0]:
                    return str(row[0])
            return None
        except Exception as e:
            logger.error(f"Error getting profesor nombre: {e}")
            return None
