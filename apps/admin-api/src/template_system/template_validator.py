import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List

try:
    import jsonschema  # type: ignore
except Exception:
    jsonschema = None


class ValidationSeverity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[Dict[str, Any]]
    warnings: List[Dict[str, Any]]
    info: List[Dict[str, Any]]
    performance_score: float
    security_score: float


class TemplateValidator:
    def __init__(self):
        self.schema = self._get_template_schema()
        self.validator = jsonschema.Draft7Validator(self.schema) if jsonschema is not None else None

    def validate_template(self, template_config: Dict[str, Any]) -> ValidationResult:
        errors: List[Dict[str, Any]] = []
        warnings: List[Dict[str, Any]] = []
        info: List[Dict[str, Any]] = []

        if self.validator is None:
            errors.append(
                {
                    "severity": ValidationSeverity.ERROR.value,
                    "message": "jsonschema no está disponible",
                    "path": "",
                }
            )
            return ValidationResult(
                is_valid=False,
                errors=errors,
                warnings=warnings,
                info=info,
                performance_score=0.0,
                security_score=0.0,
            )

        try:
            self.validator.validate(template_config)
        except jsonschema.ValidationError as e:  # type: ignore[attr-defined]
            errors.append(
                {
                    "severity": ValidationSeverity.ERROR.value,
                    "message": str(e.message),
                    "path": ".".join([str(p) for p in e.absolute_path]) if e.absolute_path else "",
                }
            )
        except Exception as e:
            errors.append(
                {
                    "severity": ValidationSeverity.ERROR.value,
                    "message": f"Validation error: {str(e)}",
                    "path": "",
                }
            )

        self._assess_structure(template_config, errors, warnings, info)
        performance_score = self._assess_performance(template_config, warnings, info)
        security_score = self._assess_security(template_config, warnings, info)
        is_valid = len(errors) == 0

        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            info=info,
            performance_score=performance_score,
            security_score=security_score,
        )

    def _assess_performance(self, cfg: Dict[str, Any], warnings: List[Dict[str, Any]], info: List[Dict[str, Any]]) -> float:
        score = 100.0

        pages = cfg.get("pages", []) if isinstance(cfg.get("pages", []), list) else []
        if len(pages) > 10:
            warnings.append(
                {"severity": ValidationSeverity.WARNING.value, "message": "Muchas páginas pueden afectar performance", "path": "pages"}
            )
            score -= 10.0

        sections_count = 0
        for p in pages:
            if isinstance(p, dict) and isinstance(p.get("sections"), list):
                sections_count += len(p.get("sections") or [])
        if sections_count > 50:
            warnings.append(
                {
                    "severity": ValidationSeverity.WARNING.value,
                    "message": "Muchas secciones pueden afectar performance",
                    "path": "pages[].sections",
                }
            )
            score -= 15.0

        variables = cfg.get("variables", {}) if isinstance(cfg.get("variables", {}), dict) else {}
        if len(variables) > 100:
            warnings.append(
                {"severity": ValidationSeverity.WARNING.value, "message": "Muchas variables pueden afectar performance", "path": "variables"}
            )
            score -= 10.0

        score = max(0.0, min(100.0, score))
        info.append({"severity": ValidationSeverity.INFO.value, "message": f"Performance score: {score}", "path": ""})
        return score

    def _assess_security(self, cfg: Dict[str, Any], warnings: List[Dict[str, Any]], info: List[Dict[str, Any]]) -> float:
        score = 100.0

        raw = json.dumps(cfg, ensure_ascii=False)
        if "javascript:" in raw.lower():
            warnings.append(
                {
                    "severity": ValidationSeverity.WARNING.value,
                    "message": "Detectado contenido potencialmente peligroso (javascript:)",
                    "path": "",
                }
            )
            score -= 30.0

        score = max(0.0, min(100.0, score))
        info.append({"severity": ValidationSeverity.INFO.value, "message": f"Security score: {score}", "path": ""})
        return score

    def _assess_structure(
        self,
        cfg: Dict[str, Any],
        errors: List[Dict[str, Any]],
        warnings: List[Dict[str, Any]],
        info: List[Dict[str, Any]],
    ) -> None:
        if not isinstance(cfg, dict):
            errors.append(
                {
                    "severity": ValidationSeverity.ERROR.value,
                    "message": "template_config debe ser un objeto",
                    "path": "",
                }
            )
            return

        layout = cfg.get("layout") if isinstance(cfg.get("layout"), dict) else {}
        page_size = str(layout.get("page_size") or "").strip()
        orientation = str(layout.get("orientation") or "").strip().lower()
        if page_size and page_size.lower() not in {"a4", "letter", "legal"}:
            warnings.append(
                {
                    "severity": ValidationSeverity.WARNING.value,
                    "message": "page_size no reconocido",
                    "path": "layout.page_size",
                    "suggestion": "Usa A4, Letter o Legal",
                }
            )
        if orientation and orientation not in {"portrait", "landscape"}:
            warnings.append(
                {
                    "severity": ValidationSeverity.WARNING.value,
                    "message": "orientation no reconocido",
                    "path": "layout.orientation",
                    "suggestion": "Usa portrait o landscape",
                }
            )

        pages = cfg.get("pages")
        if not isinstance(pages, list):
            errors.append(
                {
                    "severity": ValidationSeverity.ERROR.value,
                    "message": "pages debe ser una lista",
                    "path": "pages",
                }
            )
            return
        if len(pages) == 0:
            warnings.append(
                {
                    "severity": ValidationSeverity.WARNING.value,
                    "message": "No hay páginas definidas",
                    "path": "pages",
                }
            )
            return

        supported_types = {
            "header",
            "excel_header",
            "spacing",
            "spacer",
            "exercise_table",
            "qr_code",
            "text",
            "table",
            "image",
            "page_break",
            "progress_chart",
        }

        for page_index, page in enumerate(pages):
            if not isinstance(page, dict):
                warnings.append(
                    {
                        "severity": ValidationSeverity.WARNING.value,
                        "message": "Página inválida",
                        "path": f"pages[{page_index}]",
                    }
                )
                continue
            sections = page.get("sections")
            if not isinstance(sections, list):
                warnings.append(
                    {
                        "severity": ValidationSeverity.WARNING.value,
                        "message": "Secciones inválidas",
                        "path": f"pages[{page_index}].sections",
                    }
                )
                continue
            if len(sections) == 0:
                warnings.append(
                    {
                        "severity": ValidationSeverity.WARNING.value,
                        "message": "Página sin secciones",
                        "path": f"pages[{page_index}].sections",
                    }
                )
            for section_index, section in enumerate(sections):
                if not isinstance(section, dict):
                    warnings.append(
                        {
                            "severity": ValidationSeverity.WARNING.value,
                            "message": "Sección inválida",
                            "path": f"pages[{page_index}].sections[{section_index}]",
                        }
                    )
                    continue
                section_type = str(section.get("type") or "").strip().lower()
                if not section_type:
                    warnings.append(
                        {
                            "severity": ValidationSeverity.WARNING.value,
                            "message": "Sección sin tipo",
                            "path": f"pages[{page_index}].sections[{section_index}].type",
                        }
                    )
                    continue
                if section_type not in supported_types:
                    warnings.append(
                        {
                            "severity": ValidationSeverity.WARNING.value,
                            "message": "Tipo de sección no soportado en export_pdf",
                            "path": f"pages[{page_index}].sections[{section_index}].type",
                            "suggestion": "Revisá el tipo o usá una sección compatible",
                        }
                    )
                    continue
                self._validate_section_payload(section, section_type, page_index, section_index, warnings)

        variables = cfg.get("variables")
        if isinstance(variables, dict):
            allowed_var_types = {"string", "number", "boolean", "date", "image"}
            for key, value in variables.items():
                if not isinstance(value, dict):
                    warnings.append(
                        {
                            "severity": ValidationSeverity.WARNING.value,
                            "message": "Variable inválida",
                            "path": f"variables.{key}",
                        }
                    )
                    continue
                vtype = str(value.get("type") or "").strip().lower()
                if vtype and vtype not in allowed_var_types:
                    warnings.append(
                        {
                            "severity": ValidationSeverity.WARNING.value,
                            "message": "Tipo de variable no reconocido",
                            "path": f"variables.{key}.type",
                        }
                    )
                if vtype == "image":
                    default = value.get("default")
                    if isinstance(default, str) and default and not default.startswith("data:image/"):
                        warnings.append(
                            {
                                "severity": ValidationSeverity.WARNING.value,
                                "message": "Imagen default debería ser data URI",
                                "path": f"variables.{key}.default",
                            }
                        )
                if value.get("required") and value.get("default") in (None, ""):
                    warnings.append(
                        {
                            "severity": ValidationSeverity.WARNING.value,
                            "message": "Variable requerida sin default",
                            "path": f"variables.{key}.default",
                        }
                    )
        else:
            warnings.append(
                {
                    "severity": ValidationSeverity.WARNING.value,
                    "message": "variables debería ser un objeto",
                    "path": "variables",
                }
            )

        qr_code = cfg.get("qr_code") if isinstance(cfg.get("qr_code"), dict) else {}
        if qr_code.get("enabled") and not qr_code.get("data_source") and not qr_code.get("custom_data"):
            warnings.append(
                {
                    "severity": ValidationSeverity.WARNING.value,
                    "message": "QR habilitado sin data_source",
                    "path": "qr_code.data_source",
                    "suggestion": "Definí data_source o custom_data",
                }
            )

    def _validate_section_payload(
        self,
        section: Dict[str, Any],
        section_type: str,
        page_index: int,
        section_index: int,
        warnings: List[Dict[str, Any]],
    ) -> None:
        base_path = f"pages[{page_index}].sections[{section_index}]"
        content = section.get("content")

        if section_type == "header":
            if not isinstance(content, dict):
                warnings.append(
                    {
                        "severity": ValidationSeverity.WARNING.value,
                        "message": "Header sin contenido",
                        "path": f"{base_path}.content",
                    }
                )
                return
            title = str(content.get("title") or "").strip()
            subtitle = str(content.get("subtitle") or "").strip()
            if not title and not subtitle:
                warnings.append(
                    {
                        "severity": ValidationSeverity.WARNING.value,
                        "message": "Header sin título ni subtítulo",
                        "path": f"{base_path}.content",
                    }
                )
            return

        if section_type in {"spacing", "spacer"}:
            height = None
            if isinstance(content, dict):
                height = content.get("height")
            if height is None:
                height = section.get("height")
            if height is not None and not isinstance(height, (int, float, str)):
                warnings.append(
                    {
                        "severity": ValidationSeverity.WARNING.value,
                        "message": "Altura de espaciador inválida",
                        "path": f"{base_path}.content.height",
                    }
                )
            return

        if section_type == "text":
            text = ""
            if isinstance(content, str):
                text = content
            elif content is not None:
                text = str(content)
            if not text.strip():
                warnings.append(
                    {
                        "severity": ValidationSeverity.WARNING.value,
                        "message": "Texto vacío",
                        "path": f"{base_path}.content",
                    }
                )
            return

        if section_type == "table":
            rows = section.get("rows")
            if not isinstance(rows, list) or not rows:
                warnings.append(
                    {
                        "severity": ValidationSeverity.WARNING.value,
                        "message": "Tabla sin filas",
                        "path": f"{base_path}.rows",
                    }
                )
            return

        if section_type == "image":
            src = str(section.get("src") or "").strip()
            if not src:
                warnings.append(
                    {
                        "severity": ValidationSeverity.WARNING.value,
                        "message": "Imagen sin src",
                        "path": f"{base_path}.src",
                    }
                )
            return

        if section_type == "exercise_table":
            if content is not None and not isinstance(content, dict):
                warnings.append(
                    {
                        "severity": ValidationSeverity.WARNING.value,
                        "message": "exercise_table con content inválido",
                        "path": f"{base_path}.content",
                    }
                )
                return
            if isinstance(content, dict) and str(content.get("format") or "").strip().lower() == "excel_weekly":
                weeks = content.get("weeks")
                if weeks is not None and not isinstance(weeks, (int, float, str)):
                    warnings.append(
                        {
                            "severity": ValidationSeverity.WARNING.value,
                            "message": "weeks inválido en excel_weekly",
                            "path": f"{base_path}.content.weeks",
                        }
                    )
            return

        if section_type == "qr_code":
            size = None
            if isinstance(content, dict):
                size = content.get("size")
            if size is not None and not isinstance(size, (int, float, str)):
                warnings.append(
                    {
                        "severity": ValidationSeverity.WARNING.value,
                        "message": "Tamaño de QR inválido",
                        "path": f"{base_path}.content.size",
                    }
                )

    def _get_template_schema(self) -> Dict[str, Any]:
        return {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "required": ["metadata", "layout", "pages", "variables"],
            "properties": {
                "metadata": {
                    "type": "object",
                    "required": ["name", "version", "description"],
                    "properties": {
                        "name": {"type": "string", "minLength": 1, "maxLength": 255, "pattern": "^[a-zA-Z0-9_\\-\\s]+$"},
                        "version": {"type": "string", "pattern": "^\\d+\\.\\d+\\.\\d+$"},
                        "description": {"type": "string", "minLength": 1, "maxLength": 1000},
                    },
                },
                "layout": {
                    "type": "object",
                    "required": ["page_size", "orientation", "margins"],
                    "properties": {
                        "page_size": {"type": "string"},
                        "orientation": {"type": "string"},
                        "margins": {
                            "type": "object",
                            "required": ["top", "bottom", "left", "right"],
                            "properties": {
                                "top": {"type": "number", "minimum": 0},
                                "bottom": {"type": "number", "minimum": 0},
                                "left": {"type": "number", "minimum": 0},
                                "right": {"type": "number", "minimum": 0},
                            },
                        },
                    },
                },
                "pages": {"type": "array"},
                "variables": {"type": "object"},
                "qr_code": {"type": "object"},
                "styling": {"type": "object"},
            },
        }
