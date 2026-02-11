import base64
import io
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

import qrcode
from jinja2 import BaseLoader, StrictUndefined, TemplateError
from jinja2.sandbox import SandboxedEnvironment
from reportlab.lib.colors import black, grey, lightgrey, white
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4, legal, landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch, mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

logger = logging.getLogger(__name__)

_MAX_IMAGE_BYTES = int(os.environ.get("PDF_MAX_IMAGE_BYTES", "600000"))
_MAX_COMPILED_TEMPLATES = int(os.environ.get("PDF_MAX_COMPILED_TEMPLATES", "500"))


class PDFEngine:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.custom_styles = self._create_custom_styles()
        self.jinja_env = SandboxedEnvironment(loader=BaseLoader(), undefined=StrictUndefined, autoescape=False)
        self._compiled_templates: Dict[str, Any] = {}

    def generate_pdf(
        self,
        template_config: Dict[str, Any],
        data: Dict[str, Any],
        output_path: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> Union[str, bytes]:
        layout = template_config.get("layout", {}) or {}
        pages = template_config.get("pages", []) or []
        variables = template_config.get("variables", {}) or {}
        qr_config = template_config.get("qr_code", {}) or {}

        resolved_data = self._resolve_variables(data, variables)

        page_size = self._get_page_size(layout.get("page_size", "A4"))
        if str(layout.get("orientation", "portrait")).strip().lower() == "landscape":
            page_size = landscape(page_size)

        margins = layout.get("margins", {}) or {}
        right_margin = self._to_points(margins.get("right", 20))
        left_margin = self._to_points(margins.get("left", 20))
        top_margin = self._to_points(margins.get("top", 20))
        bottom_margin = self._to_points(margins.get("bottom", 20))

        qr_position = str(qr_config.get("position") or "inline").strip().lower()
        if qr_position in ("separate_sheet", "sheet"):
            qr_position = "separate"

        qr_overlay_reader: Optional[ImageReader] = None
        qr_overlay_w = 0.0
        qr_overlay_h = 0.0
        if qr_config.get("enabled", False) and qr_position in ("header", "footer"):
            qr_data = self._get_qr_code_data(resolved_data, qr_config)
            if qr_data:
                try:
                    size_cfg = qr_config.get("size") or {}
                    if not isinstance(size_cfg, dict):
                        size_cfg = {}
                    qr_overlay_w = self._to_points(size_cfg.get("width", 40))
                    qr_overlay_h = self._to_points(size_cfg.get("height", 40))
                    qr_overlay_reader = self._build_qr_image_reader(qr_data)
                except Exception:
                    qr_overlay_reader = None

        def _draw_qr_overlay(canvas, doc) -> None:
            try:
                if qr_overlay_reader is None:
                    return
                if qr_position not in ("header", "footer"):
                    return
                if qr_overlay_w <= 0 or qr_overlay_h <= 0:
                    return
                x = float(doc.pagesize[0]) - float(doc.rightMargin) - float(qr_overlay_w)
                if qr_position == "header":
                    y = float(doc.height) + float(doc.bottomMargin) + max(0.0, (float(doc.topMargin) - float(qr_overlay_h)) / 2.0)
                else:
                    y = max(0.0, (float(doc.bottomMargin) - float(qr_overlay_h)) / 2.0)
                canvas.drawImage(qr_overlay_reader, x, y, width=qr_overlay_w, height=qr_overlay_h, mask="auto")
            except Exception:
                return

        buf = io.BytesIO()
        doc = SimpleDocTemplate(
            output_path or buf,
            pagesize=page_size,
            rightMargin=right_margin,
            leftMargin=left_margin,
            topMargin=top_margin,
            bottomMargin=bottom_margin,
        )

        story: List[Any] = []
        for page_index, page in enumerate(pages):
            if not isinstance(page, dict):
                continue
            sections = page.get("sections", []) or []
            for sec in sections:
                story.extend(self._render_section(sec, resolved_data, options or {}))
            if page_index < len(pages) - 1:
                story.append(PageBreak())

        if qr_config.get("enabled", False) and qr_position == "inline":
            qr_data = self._get_qr_code_data(resolved_data, qr_config)
            if qr_data:
                img = self._build_qr_image(qr_data, qr_config)
                if img is not None:
                    story.append(Spacer(1, 6))
                    story.append(img)

        if qr_config.get("enabled", False) and qr_position == "separate":
            qr_data = self._get_qr_code_data(resolved_data, qr_config)
            if qr_data:
                story.append(PageBreak())
                story.append(Paragraph("QR", self.custom_styles["section_header"]))
                story.append(Spacer(1, 12))
                img = self._build_qr_image(qr_data, qr_config, large=True)
                if img is not None:
                    story.append(img)

        doc.build(story, onFirstPage=_draw_qr_overlay, onLaterPages=_draw_qr_overlay)

        if output_path:
            return output_path
        return buf.getvalue()

    def validate_template_structure(self, template_config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        errors: List[str] = []
        if not isinstance(template_config, dict):
            return False, ["template_config debe ser un objeto"]
        for key in ("metadata", "layout", "pages", "variables"):
            if key not in template_config:
                errors.append(f"Falta '{key}'")
        pages = template_config.get("pages")
        if not isinstance(pages, list) or not pages:
            errors.append("pages debe ser una lista no vacía")
        else:
            for i, p in enumerate(pages):
                if not isinstance(p, dict):
                    errors.append(f"pages[{i}] inválida")
                    continue
                if "sections" not in p or not isinstance(p.get("sections"), list):
                    errors.append(f"pages[{i}].sections inválida")
        return len(errors) == 0, errors

    def _render_section(self, section: Any, data: Dict[str, Any], options: Dict[str, Any]) -> List[Any]:
        if not isinstance(section, dict):
            return []
        t = str(section.get("type") or "").strip().lower()
        if t == "header":
            content = section.get("content") or {}
            if not isinstance(content, dict):
                content = {}
            title = self._render_template_string(str(content.get("title") or ""), data).strip()
            subtitle = self._render_template_string(str(content.get("subtitle") or ""), data).strip()
            out: List[Any] = []
            if title:
                out.append(Paragraph(title, self.custom_styles["header"]))
            if subtitle:
                out.append(Spacer(1, self._to_points(2)))
                out.append(Paragraph(subtitle, self.custom_styles["small"]))
            if out:
                out.append(Spacer(1, self._to_points(section.get("spacing_after", 6))))
            return out
        if t in ("spacing", "spacer"):
            content = section.get("content") or {}
            h = content.get("height") if isinstance(content, dict) else section.get("height", 8)
            return [Spacer(1, self._to_points(h))]
        if t == "exercise_table":
            return self._render_exercise_table(section, data)
        if t == "qr_code":
            return self._render_qr_section(section, data)
        if t == "text":
            text = self._render_template_string(str(section.get("content") or ""), data)
            style_name = str(section.get("style") or "normal").strip().lower()
            style = self.custom_styles.get(style_name, self.styles["Normal"])
            return [Paragraph(text, style), Spacer(1, self._to_points(section.get("spacing_after", 4)))]
        if t == "spacer":
            return [Spacer(1, self._to_points(section.get("height", 8)))]
        if t == "table":
            return self._render_table(section, data)
        if t == "image":
            return self._render_image(section, data)
        if t == "page_break":
            return [PageBreak()]
        return []

    def _render_table(self, section: Dict[str, Any], data: Dict[str, Any]) -> List[Any]:
        rows = section.get("rows", []) or []
        if not isinstance(rows, list) or not rows:
            return []
        out_rows: List[List[Any]] = []
        for r in rows:
            if not isinstance(r, list):
                continue
            out_rows.append([self._render_template_string(str(c or ""), data) for c in r])
        table = Table(out_rows)
        table.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.5, grey),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )
        return [table, Spacer(1, self._to_points(section.get("spacing_after", 6)))]

    def _render_exercise_table(self, section: Dict[str, Any], data: Dict[str, Any]) -> List[Any]:
        content = section.get("content") or {}
        if not isinstance(content, dict):
            content = {}

        columns = content.get("columns")
        if not isinstance(columns, list) or not columns:
            columns = ["Ejercicio", "Series", "Repeticiones", "Descanso"]

        day_list: List[Dict[str, Any]] = []
        raw_dias = data.get("dias")
        if isinstance(raw_dias, list):
            day_list = [d for d in raw_dias if isinstance(d, dict)]
        else:
            rutina = data.get("rutina") or data.get("routine") or {}
            if isinstance(rutina, dict) and isinstance(rutina.get("dias"), list):
                day_list = [d for d in rutina.get("dias") if isinstance(d, dict)]

        if not day_list:
            return [Paragraph("Sin ejercicios", self.custom_styles["small"]), Spacer(1, self._to_points(6))]

        out: List[Any] = []
        for day in day_list:
            day_num = day.get("numero") or day.get("dayNumber") or day.get("dia_semana")
            day_title = str(day.get("nombre") or day.get("dayName") or "")
            if day_num:
                head = f"Día {day_num}"
                if day_title:
                    head = f"{head} - {day_title}"
            else:
                head = day_title or "Día"

            out.append(Paragraph(head, self.custom_styles["section_header"]))
            out.append(Spacer(1, self._to_points(3)))

            ejercicios = day.get("ejercicios") if isinstance(day.get("ejercicios"), list) else []
            rows: List[List[str]] = [list(map(str, columns))]
            for ex in ejercicios:
                if not isinstance(ex, dict):
                    continue
                nombre = str(ex.get("nombre") or ex.get("ejercicio_nombre") or ex.get("exercise_name") or "")
                series = ex.get("series")
                reps = ex.get("repeticiones") or ex.get("reps")
                descanso = ex.get("descanso") or ex.get("rest")
                rows.append(
                    [
                        nombre,
                        "" if series is None else str(series),
                        "" if reps is None else str(reps),
                        "" if descanso is None else str(descanso),
                    ]
                )

            table = Table(rows, repeatRows=1)
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), lightgrey),
                        ("TEXTCOLOR", (0, 0), (-1, 0), black),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 9),
                        ("GRID", (0, 0), (-1, -1), 0.5, grey),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("BACKGROUND", (0, 1), (-1, -1), white),
                    ]
                )
            )
            out.append(table)
            out.append(Spacer(1, self._to_points(content.get("spacing_after", 8))))

        return out

    def _render_qr_section(self, section: Dict[str, Any], data: Dict[str, Any]) -> List[Any]:
        content = section.get("content") or {}
        if not isinstance(content, dict):
            content = {}
        size = content.get("size", 60)
        qr_cfg = {"enabled": True, "data_source": "routine_uuid", "size": {"width": size, "height": size}}
        qr_data = self._get_qr_code_data(data, qr_cfg)
        if not qr_data:
            return []
        img = self._build_qr_image(qr_data, qr_cfg, large=bool(size and int(size) >= 80))
        if img is None:
            return []
        return [img, Spacer(1, self._to_points(section.get("spacing_after", 6)))]

    def _render_image(self, section: Dict[str, Any], data: Dict[str, Any]) -> List[Any]:
        src = self._render_template_string(str(section.get("src") or ""), data).strip()
        if not src:
            return []
        try:
            if src.startswith("data:image/"):
                _, b64 = src.split(",", 1)
                raw = base64.b64decode(b64, validate=True)
                if len(raw) > _MAX_IMAGE_BYTES:
                    return []
                reader = ImageReader(io.BytesIO(raw))
                width = self._to_points(section.get("width", 100))
                height = self._to_points(section.get("height", 60))
                img = Image(reader, width=width, height=height)
            else:
                return []
            return [img, Spacer(1, self._to_points(section.get("spacing_after", 6)))]
        except Exception:
            return []

    def _get_page_size(self, name: str):
        n = str(name or "").strip().lower()
        if n == "letter":
            return letter
        if n == "legal":
            return legal
        return A4

    def _to_points(self, value: Any) -> float:
        try:
            if isinstance(value, (int, float)):
                return float(value) * mm
            if isinstance(value, str):
                v = value.strip().lower()
                if v.endswith("mm"):
                    return float(v[:-2]) * mm
                if v.endswith("in"):
                    return float(v[:-2]) * inch
                return float(v) * mm
        except Exception:
            return 0.0
        return 0.0

    def _create_custom_styles(self) -> Dict[str, ParagraphStyle]:
        return {
            "normal": ParagraphStyle("NormalCustom", parent=self.styles["Normal"], fontSize=10, leading=12),
            "header": ParagraphStyle("HeaderCustom", parent=self.styles["Heading1"], alignment=TA_CENTER, textColor=black),
            "section_header": ParagraphStyle("SectionHeaderCustom", parent=self.styles["Heading2"], alignment=TA_LEFT, textColor=black),
            "small": ParagraphStyle("SmallCustom", parent=self.styles["Normal"], fontSize=8, leading=10, textColor=grey),
            "justify": ParagraphStyle("JustifyCustom", parent=self.styles["Normal"], alignment=TA_JUSTIFY),
        }

    def _resolve_variables(self, data: Dict[str, Any], variables: Dict[str, Any]) -> Dict[str, Any]:
        resolved = dict(data or {})
        resolved.setdefault("current_date", datetime.utcnow().strftime("%Y-%m-%d"))
        if isinstance(variables, dict):
            for name, cfg in variables.items():
                if name in resolved:
                    continue
                if isinstance(cfg, dict) and "default" in cfg:
                    resolved[name] = cfg.get("default")
        return resolved

    def _render_template_string(self, template_str: str, data: Dict[str, Any]) -> str:
        s = template_str or ""
        if "{{" not in s:
            return s
        try:
            tpl = self._compiled_templates.get(s)
            if tpl is None:
                if _MAX_COMPILED_TEMPLATES > 0 and len(self._compiled_templates) >= _MAX_COMPILED_TEMPLATES:
                    try:
                        self._compiled_templates.pop(next(iter(self._compiled_templates)))
                    except Exception:
                        self._compiled_templates = {}
                tpl = self.jinja_env.from_string(s)
                self._compiled_templates[s] = tpl
            return str(tpl.render(**data))
        except TemplateError:
            return s

    def _get_qr_code_data(self, resolved_data: Dict[str, Any], qr_cfg: Dict[str, Any]) -> Optional[str]:
        source = str(qr_cfg.get("data_source") or "routine_uuid").strip().lower()
        if source == "custom_url":
            return str(qr_cfg.get("custom_data") or "")
        if source == "user_data":
            u = resolved_data.get("user") or {}
            if isinstance(u, dict):
                return str(u.get("id") or u.get("dni") or "")
            return None
        r = resolved_data.get("routine") or {}
        if isinstance(r, dict):
            return str(r.get("uuid") or r.get("uuid_rutina") or "")
        return None

    def _build_qr_image_reader(self, qr_data: str) -> ImageReader:
        qr = qrcode.QRCode(border=1, box_size=4)
        qr.add_data(qr_data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return ImageReader(buf)

    def _build_qr_image(self, qr_data: str, qr_cfg: Dict[str, Any], large: bool = False) -> Optional[Image]:
        try:
            reader = self._build_qr_image_reader(qr_data)
            size_cfg = qr_cfg.get("size") or {}
            if not isinstance(size_cfg, dict):
                size_cfg = {}
            w = self._to_points(size_cfg.get("width", 60 if large else 40))
            h = self._to_points(size_cfg.get("height", 60 if large else 40))
            if w <= 0 or h <= 0:
                w = h = 40 * mm
            return Image(reader, width=w, height=h)
        except Exception:
            return None
