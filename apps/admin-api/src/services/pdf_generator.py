"""
PDF Receipt Generator for IronHub Admin API
Simplified version restored from deprecated/core/pdf_generator.py
"""

import os
import tempfile
from datetime import datetime
from typing import Optional, List, Dict

# Check for reportlab availability
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate,
        Table,
        TableStyle,
        Paragraph,
        Spacer,
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_RIGHT, TA_CENTER

    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


class PDFGenerator:
    """Simple PDF receipt generator for gym payments."""

    def __init__(self, gym_name: str = "IronHub Gym", gym_address: str = ""):
        self.gym_name = gym_name
        self.gym_address = gym_address

        # Ensure output directory exists
        pref_dir = os.environ.get("RECEIPTS_DIR", "recibos")
        try:
            os.makedirs(pref_dir, exist_ok=True)
            self.output_dir = pref_dir
        except Exception:
            self.output_dir = tempfile.gettempdir()

    def generar_recibo(
        self,
        pago_id: int,
        usuario_nombre: str,
        usuario_dni: Optional[str],
        monto: float,
        mes: int,
        año: int,
        fecha_pago: Optional[datetime] = None,
        metodo_pago: Optional[str] = None,
        tipo_cuota: Optional[str] = None,
        detalles: Optional[List[Dict]] = None,
        numero_comprobante: Optional[str] = None,
        observaciones: Optional[str] = None,
    ) -> str:
        """Generate a PDF receipt and return the file path."""

        if not REPORTLAB_AVAILABLE:
            raise ImportError(
                "reportlab is required for PDF generation. Install with: pip install reportlab"
            )

        fecha_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"recibo_{pago_id}_{fecha_str}.pdf"
        filepath = os.path.join(self.output_dir, filename)

        doc = SimpleDocTemplate(
            filepath,
            pagesize=letter,
            rightMargin=inch / 2,
            leftMargin=inch / 2,
            topMargin=inch / 2,
            bottomMargin=inch / 2,
        )

        styles = getSampleStyleSheet()
        elements = []

        # Colors
        header_bg = colors.HexColor("#434C5E")
        body_bg = colors.HexColor("#D8DEE9")

        # Header
        header_style = ParagraphStyle(
            "HeaderStyle",
            parent=styles["h1"],
            alignment=TA_CENTER,
            textColor=colors.darkblue,
            fontSize=24,
        )
        elements.append(Paragraph("RECIBO DE PAGO", header_style))
        elements.append(Spacer(1, 0.3 * inch))

        # Receipt info
        recibo_num = numero_comprobante or str(pago_id)
        fecha_disp = (fecha_pago or datetime.now()).strftime("%d/%m/%Y")

        info_style = ParagraphStyle(
            "InfoRight", parent=styles["Normal"], alignment=TA_RIGHT
        )
        elements.append(Paragraph(f"Comprobante N°: {recibo_num}", info_style))
        elements.append(Paragraph(f"Fecha: {fecha_disp}", info_style))
        elements.append(Spacer(1, 0.3 * inch))

        # User info table
        meses = [
            "Enero",
            "Febrero",
            "Marzo",
            "Abril",
            "Mayo",
            "Junio",
            "Julio",
            "Agosto",
            "Septiembre",
            "Octubre",
            "Noviembre",
            "Diciembre",
        ]
        periodo = f"{meses[mes - 1]} {año}"

        info_rows = [
            [Paragraph("<b>INFORMACIÓN DEL RECIBO</b>", styles["Normal"]), ""],
            ["Nombre", usuario_nombre or "No especificado"],
        ]
        if usuario_dni:
            info_rows.append(["DNI", str(usuario_dni)])
        if metodo_pago:
            info_rows.append(["Método de Pago", metodo_pago])
        if tipo_cuota:
            info_rows.append(["Tipo de Cuota", tipo_cuota])
        info_rows.append(["Periodo", periodo])

        info_table = Table(info_rows, colWidths=[2.4 * inch, 5.1 * inch])
        info_table.setStyle(
            TableStyle(
                [
                    ("SPAN", (0, 0), (1, 0)),
                    ("BACKGROUND", (0, 0), (1, 0), header_bg),
                    ("TEXTCOLOR", (0, 0), (1, 0), colors.whitesmoke),
                    ("FONTNAME", (0, 0), (1, 0), "Helvetica-Bold"),
                    ("BACKGROUND", (0, 1), (1, -1), body_bg),
                    ("GRID", (0, 0), (1, -1), 1, colors.black),
                    ("LEFTPADDING", (0, 1), (1, -1), 6),
                ]
            )
        )
        elements.append(info_table)
        elements.append(Spacer(1, 0.35 * inch))

        # Payment details table
        details_data = [["Descripción", "Cantidad", "Precio Unitario", "Subtotal"]]

        if detalles and len(detalles) > 0:
            for det in detalles:
                desc = (
                    det.get("descripcion") or det.get("concepto_nombre") or "Concepto"
                )
                cantidad = det.get("cantidad", 1)
                precio = det.get("precio_unitario", 0)
                subtotal = det.get("subtotal", cantidad * precio)
                details_data.append(
                    [
                        desc,
                        str(cantidad),
                        f"${precio:,.2f}",
                        f"${subtotal:,.2f}",
                    ]
                )
        else:
            # Default row
            details_data.append(
                [
                    f"Cuota mensual: {periodo}",
                    "1",
                    f"${monto:,.2f}",
                    f"${monto:,.2f}",
                ]
            )

        details_table = Table(
            details_data, colWidths=[3.5 * inch, 1 * inch, 1.5 * inch, 1.5 * inch]
        )
        details_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), header_bg),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("BACKGROUND", (0, 1), (-1, -1), body_bg),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                ]
            )
        )
        elements.append(details_table)
        elements.append(Spacer(1, 0.4 * inch))

        # Total
        total_rows = [["", "TOTAL:", f"${monto:,.2f}"]]
        total_table = Table(total_rows, colWidths=[5 * inch, 1 * inch, 1.5 * inch])
        total_table.setStyle(
            TableStyle(
                [
                    ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                    ("FONTNAME", (1, 0), (-1, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (1, 0), (-1, -1), 12),
                    ("BACKGROUND", (1, 0), (-1, 0), header_bg),
                    ("TEXTCOLOR", (1, 0), (-1, 0), colors.whitesmoke),
                ]
            )
        )
        elements.append(total_table)
        elements.append(Spacer(1, 0.5 * inch))

        # Observations
        if observaciones:
            elements.append(
                Paragraph(f"<b>Observaciones:</b> {observaciones}", styles["Normal"])
            )
            elements.append(Spacer(1, 0.3 * inch))

        # Footer
        elements.append(Paragraph("¡Gracias por tu pago!", styles["h3"]))
        if self.gym_name:
            elements.append(Paragraph(self.gym_name, styles["Normal"]))
        if self.gym_address:
            elements.append(Paragraph(self.gym_address, styles["Normal"]))

        doc.build(elements)
        return filepath

    @staticmethod
    def is_available() -> bool:
        """Check if PDF generation is available."""
        return REPORTLAB_AVAILABLE
