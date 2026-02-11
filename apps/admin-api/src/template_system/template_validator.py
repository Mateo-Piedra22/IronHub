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
                        "name": {"type": "string", "minLength": 1, "maxLength": 255},
                        "version": {"type": "string"},
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

