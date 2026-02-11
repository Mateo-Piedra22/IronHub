"""
Template Validation System

This module provides comprehensive validation for dynamic routine templates,
including JSON schema validation, business rule validation, and performance
impact assessment.
"""

import json
import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

try:
    import jsonschema  # type: ignore
except Exception:  # pragma: no cover
    jsonschema = None


class ValidationSeverity(Enum):
    """Validation error severity levels"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationResult:
    """Result of template validation"""
    is_valid: bool
    errors: List[Dict[str, Any]]
    warnings: List[Dict[str, Any]]
    info: List[Dict[str, Any]]
    performance_score: float  # 0-100
    security_score: float  # 0-100


class TemplateValidator:
    """Comprehensive template validation system"""
    
    def __init__(self):
        self.schema = self._get_template_schema()
        self.validator = (
            jsonschema.Draft7Validator(self.schema)
            if jsonschema is not None
            else None
        )
        self._allowed_builtin_vars = {
            "rutina_id",
            "uuid_rutina",
            "nombre_rutina",
            "descripcion",
            "categoria",
            "dias_semana",
            "current_week",
            "fecha_creacion",
            "usuario",
            "usuario_nombre",
            "gimnasio",
            "gym_name",
            "dias",
        }
        self._allowed_filters = {
            "lower",
            "upper",
            "title",
            "capitalize",
            "trim",
            "length",
            "default",
            "replace",
            "round",
            "int",
            "float",
            "string",
        }
    
    def _get_template_schema(self) -> Dict[str, Any]:
        """JSON Schema for template validation"""
        return {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "title": "Dynamic Routine Template",
            "description": "Template configuration for dynamic routine generation",
            "required": [
                "metadata",
                "layout",
                "pages",
                "variables"
            ],
            "properties": {
                "metadata": {
                    "type": "object",
                    "required": ["name", "version", "description"],
                    "properties": {
                        "name": {
                            "type": "string",
                            "minLength": 1,
                            "maxLength": 255,
                            "pattern": "^[a-zA-Z0-9_\\-\\s]+$"
                        },
                        "version": {
                            "type": "string",
                            "pattern": "^\\d+\\.\\d+\\.\\d+$"
                        },
                        "description": {
                            "type": "string",
                            "minLength": 1,
                            "maxLength": 1000
                        },
                        "author": {
                            "type": "string",
                            "maxLength": 255
                        },
                        "category": {
                            "type": "string",
                            "enum": ["strength", "cardio", "flexibility", "sports", "rehab", "general"]
                        },
                        "difficulty": {
                            "type": "string",
                            "enum": ["beginner", "intermediate", "advanced", "expert"]
                        },
                        "tags": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "minLength": 1,
                                "maxLength": 50
                            },
                            "maxItems": 10
                        },
                        "estimated_duration": {
                            "type": "integer",
                            "minimum": 5,
                            "maximum": 480
                        }
                    }
                },
                "layout": {
                    "type": "object",
                    "required": ["page_size", "orientation", "margins"],
                    "properties": {
                        "page_size": {
                            "type": "string",
                            "enum": ["A4", "Letter", "Legal"]
                        },
                        "orientation": {
                            "type": "string",
                            "enum": ["portrait", "landscape"]
                        },
                        "margins": {
                            "type": "object",
                            "required": ["top", "bottom", "left", "right"],
                            "properties": {
                                "top": {"type": "number", "minimum": 0},
                                "bottom": {"type": "number", "minimum": 0},
                                "left": {"type": "number", "minimum": 0},
                                "right": {"type": "number", "minimum": 0}
                            }
                        },
                        "header": {
                            "type": "object",
                            "properties": {
                                "enabled": {"type": "boolean"},
                                "height": {"type": "number", "minimum": 0},
                                "content": {"type": "string"}
                            }
                        },
                        "footer": {
                            "type": "object",
                            "properties": {
                                "enabled": {"type": "boolean"},
                                "height": {"type": "number", "minimum": 0},
                                "content": {"type": "string"}
                            }
                        }
                    }
                },
                "pages": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 20,
                    "items": {
                        "type": "object",
                        "required": ["name", "sections"],
                        "properties": {
                            "name": {
                                "type": "string",
                                "minLength": 1,
                                "maxLength": 100
                            },
                            "description": {
                                "type": "string",
                                "maxLength": 500
                            },
                            "sections": {
                                "type": "array",
                                "minItems": 1,
                                "items": {
                                    "$ref": "#/definitions/section"
                                }
                            }
                        }
                    }
                },
                "variables": {
                    "type": "object",
                    "patternProperties": {
                        "^[a-zA-Z_][a-zA-Z0-9_]*$": {
                            "$ref": "#/definitions/variable"
                        }
                    }
                },
                "qr_code": {
                    "type": "object",
                    "properties": {
                        "enabled": {"type": "boolean"},
                        "position": {
                            "type": "string",
                            "enum": ["header", "footer", "inline", "separate", "sheet", "none"]
                        },
                        "size": {
                            "type": "object",
                            "properties": {
                                "width": {"type": "number", "minimum": 10, "maximum": 200},
                                "height": {"type": "number", "minimum": 10, "maximum": 200}
                            }
                        },
                        "data_source": {
                            "type": "string",
                            "enum": ["routine_uuid", "custom_url", "user_data"]
                        },
                        "custom_data": {
                            "type": "string"
                        }
                    }
                },
                "styling": {
                    "type": "object",
                    "properties": {
                        "fonts": {
                            "type": "object",
                            "patternProperties": {
                                "^[a-zA-Z_][a-zA-Z0-9_]*$": {
                                    "type": "object",
                                    "properties": {
                                        "family": {"type": "string"},
                                        "size": {"type": "number", "minimum": 6, "maximum": 72},
                                        "bold": {"type": "boolean"},
                                        "italic": {"type": "boolean"},
                                        "color": {"type": "string", "pattern": "^#[0-9A-Fa-f]{6}$"}
                                    }
                                }
                            }
                        },
                        "colors": {
                            "type": "object",
                            "patternProperties": {
                                "^[a-zA-Z_][a-zA-Z0-9_]*$": {
                                    "type": "string",
                                    "pattern": "^#[0-9A-Fa-f]{6}$"
                                }
                            }
                        }
                    }
                }
            },
            "definitions": {
                "section": {
                    "type": "object",
                    "required": ["type"],
                    "properties": {
                        "type": {
                            "type": "string",
                            "enum": [
                                "header", "text", "table", "image", "qr_code",
                                "exercise_table", "progress_chart", "spacing"
                            ]
                        },
                        "name": {
                            "type": "string",
                            "maxLength": 100
                        },
                        "position": {
                            "type": "object",
                            "properties": {
                                "x": {"type": "number"},
                                "y": {"type": "number"},
                                "width": {"type": "number", "minimum": 0},
                                "height": {"type": "number", "minimum": 0}
                            }
                        },
                        "content": {
                            "type": "object"
                        },
                        "conditional": {
                            "type": "object",
                            "properties": {
                                "if": {"type": "string"},
                                "show": {"type": "boolean"}
                            }
                        }
                    }
                },
                "variable": {
                    "type": "object",
                    "required": ["type"],
                    "properties": {
                        "type": {
                            "type": "string",
                            "enum": [
                                "string", "number", "boolean", "date", "array",
                                "exercise_list", "user_data", "gym_data", "calculated"
                            ]
                        },
                        "default": {},
                        "required": {"type": "boolean"},
                        "description": {"type": "string"},
                        "validation": {
                            "type": "object",
                            "properties": {
                                "min": {"type": "number"},
                                "max": {"type": "number"},
                                "pattern": {"type": "string"},
                                "enum": {"type": "array"}
                            }
                        }
                    }
                }
            }
        }
    
    def validate_template(self, template_config: Dict[str, Any]) -> ValidationResult:
        """Validate template configuration comprehensively"""
        errors = []
        warnings = []
        info = []
        
        # 1. JSON Schema validation
        schema_errors = self._validate_schema(template_config)
        errors.extend(schema_errors)
        
        # 2. Business rule validation
        business_errors, business_warnings = self._validate_business_rules(template_config)
        errors.extend(business_errors)
        warnings.extend(business_warnings)
        
        # 3. Performance assessment
        performance_score, performance_warnings = self._assess_performance(template_config)
        warnings.extend(performance_warnings)
        
        # 4. Security assessment
        security_score, security_warnings = self._assess_security(template_config)
        warnings.extend(security_warnings)
        
        # 5. Best practices
        best_practice_warnings, best_practice_info = self._check_best_practices(template_config)
        warnings.extend(best_practice_warnings)
        info.extend(best_practice_info)
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            info=info,
            performance_score=performance_score,
            security_score=security_score
        )
    
    def _validate_schema(self, template_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Validate against JSON schema"""
        errors = []

        if jsonschema is None or self.validator is None:
            return [
                {
                    "severity": ValidationSeverity.WARNING.value,
                    "type": "schema_unavailable",
                    "message": "JSON schema validation skipped: 'jsonschema' dependency not installed",
                    "path": [],
                }
            ]
        
        try:
            schema_errors = sorted(
                self.validator.iter_errors(template_config),
                key=lambda e: (list(e.absolute_path), str(e.message)),
            )
            for e in schema_errors:
                errors.append(
                    {
                        "severity": ValidationSeverity.ERROR.value,
                        "type": "schema_validation",
                        "message": f"Schema validation failed: {e.message}",
                        "path": list(e.absolute_path),
                        "schema_path": list(e.schema_path),
                    }
                )
        except Exception as e:
            errors.append({
                "severity": ValidationSeverity.ERROR.value,
                "type": "schema_validation",
                "message": f"Schema validation failed: {e.message}",
                "path": [],
                "schema_path": [],
            })
        
        return errors
    
    def _validate_business_rules(self, template_config: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Validate business rules"""
        errors = []
        warnings = []
        
        # Check required sections for routine templates
        if not self._has_exercise_table(template_config):
            warnings.append({
                "severity": ValidationSeverity.WARNING.value,
                "type": "business_rule",
                "message": "Template does not contain an exercise table section",
                "path": ["pages"]
            })
        
        # Check variable references
        undefined_vars = self._find_undefined_variables(template_config)
        if undefined_vars:
            errors.extend([
                {
                    "severity": ValidationSeverity.ERROR.value,
                    "type": "business_rule",
                    "message": f"Undefined variable referenced: {var}",
                    "path": ["variables"]
                }
                for var in undefined_vars
            ])

        forbidden = self._find_forbidden_template_expressions(template_config)
        if forbidden:
            errors.extend(forbidden)

        whitelist_warnings = self._validate_template_expression_whitelist(template_config)
        if whitelist_warnings:
            warnings.extend(whitelist_warnings)

        section_errors, section_warnings = self._validate_section_semantics(template_config)
        if section_errors:
            errors.extend(section_errors)
        if section_warnings:
            warnings.extend(section_warnings)
        
        # Check page count limits
        page_count = len(template_config.get("pages", []))
        if page_count > 10:
            warnings.append({
                "severity": ValidationSeverity.WARNING.value,
                "type": "business_rule",
                "message": f"Template has {page_count} pages, which may impact performance",
                "path": ["pages"]
            })
        
        # Check QR code configuration
        qr_config = template_config.get("qr_code", {})
        if qr_config.get("enabled", False) and qr_config.get("data_source") == "custom_url":
            if not qr_config.get("custom_data"):
                errors.append({
                    "severity": ValidationSeverity.ERROR.value,
                    "type": "business_rule",
                    "message": "Custom QR code data source requires custom_data field",
                    "path": ["qr_code", "custom_data"]
                })
        
        return errors, warnings

    def _find_forbidden_template_expressions(self, template_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        errors: List[Dict[str, Any]] = []
        for s, path in self._iter_template_strings(template_config):
            lowered = s.lower()
            if "{%" in s or "{#" in s:
                errors.append(
                    {
                        "severity": ValidationSeverity.ERROR.value,
                        "type": "security",
                        "message": "Solo se permiten expresiones {{ ... }} (bloques/statement no permitidos)",
                        "path": path,
                    }
                )
            if "__" in s or "import" in lowered:
                errors.append(
                    {
                        "severity": ValidationSeverity.ERROR.value,
                        "type": "security",
                        "message": "Expresión de template no permitida",
                        "path": path,
                    }
                )
            for token in ("cycler", "joiner", "namespace", "self", "globals", "builtins"):
                if token in lowered:
                    errors.append(
                        {
                            "severity": ValidationSeverity.WARNING.value,
                            "type": "security",
                            "message": f"Uso potencialmente riesgoso en template: {token}",
                            "path": path,
                        }
                    )
        return errors

    def _iter_template_strings(self, obj: Any, path: Optional[List[Any]] = None):
        p = list(path or [])
        if isinstance(obj, dict):
            for k, v in obj.items():
                yield from self._iter_template_strings(v, p + [k])
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                yield from self._iter_template_strings(v, p + [i])
        elif isinstance(obj, str):
            if "{{" in obj:
                yield (obj, p)

    def _extract_template_expressions(self, template_config: Dict[str, Any]) -> List[Tuple[str, List[Any]]]:
        expressions: List[Tuple[str, List[Any]]] = []
        for s, path in self._iter_template_strings(template_config):
            try:
                matches = re.findall(r"\{\{\s*(.+?)\s*\}\}", s)
            except Exception:
                matches = []
            for expr in matches:
                if expr:
                    expressions.append((expr, path))
        return expressions

    def _parse_expression(self, expr: str) -> Tuple[Optional[str], List[str], bool]:
        raw = str(expr or "").strip()
        if not raw:
            return None, [], False
        parts = [p.strip() for p in raw.split("|")]
        base = parts[0]
        filters = []
        for part in parts[1:]:
            if not part:
                continue
            name = part.split("(", 1)[0].strip()
            if name:
                filters.append(name)
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*(\.[a-zA-Z_][a-zA-Z0-9_]*)*$", base):
            return base, filters, False
        return base, filters, True

    def _validate_template_expression_whitelist(self, template_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        warnings: List[Dict[str, Any]] = []
        defined_vars = set(template_config.get("variables", {}).keys())
        allowed_vars = set(defined_vars) | set(self._allowed_builtin_vars)
        for expr, path in self._extract_template_expressions(template_config):
            base, filters, valid_base = self._parse_expression(expr)
            if not base:
                continue
            if not valid_base:
                warnings.append(
                    {
                        "severity": ValidationSeverity.WARNING.value,
                        "type": "template_whitelist",
                        "message": f"Expresión de template fuera de whitelist: {expr}",
                        "path": path,
                    }
                )
                continue
            root = str(base).split(".", 1)[0]
            if root not in allowed_vars:
                warnings.append(
                    {
                        "severity": ValidationSeverity.WARNING.value,
                        "type": "template_whitelist",
                        "message": f"Variable fuera de whitelist: {root}",
                        "path": path,
                    }
                )
            for f in filters:
                if f not in self._allowed_filters:
                    warnings.append(
                        {
                            "severity": ValidationSeverity.WARNING.value,
                            "type": "template_whitelist",
                            "message": f"Filtro no permitido en whitelist: {f}",
                            "path": path,
                        }
                    )
    
    def _assess_performance(self, template_config: Dict[str, Any]) -> Tuple[float, List[Dict[str, Any]]]:
        """Assess template performance impact"""
        warnings = []
        score = 100
        
        # Penalize complex layouts
        sections_count = sum(len(page.get("sections", [])) for page in template_config.get("pages", []))
        if sections_count > 50:
            score -= 20
            warnings.append({
                "severity": ValidationSeverity.WARNING.value,
                "type": "performance",
                "message": f"Template has {sections_count} sections, which may impact rendering performance",
                "path": ["pages"]
            })
        elif sections_count > 30:
            score -= 10
        
        # Penalize heavy use of images
        image_sections = sum(
            1 for page in template_config.get("pages", [])
            for section in page.get("sections", [])
            if section.get("type") == "image"
        )
        if image_sections > 5:
            score -= 15
            warnings.append({
                "severity": ValidationSeverity.WARNING.value,
                "type": "performance",
                "message": f"Template has {image_sections} image sections, which may increase file size",
                "path": ["pages"]
            })
        
        # Penalize complex calculations
        calc_vars = sum(
            1 for var_config in template_config.get("variables", {}).values()
            if var_config.get("type") == "calculated"
        )
        if calc_vars > 10:
            score -= 10
            warnings.append({
                "severity": ValidationSeverity.WARNING.value,
                "type": "performance",
                "message": f"Template has {calc_vars} calculated variables, which may impact processing time",
                "path": ["variables"]
            })
        
        return max(0, score), warnings
    
    def _assess_security(self, template_config: Dict[str, Any]) -> Tuple[float, List[Dict[str, Any]]]:
        """Assess template security"""
        warnings = []
        score = 100
        
        # Check for potential XSS in text content
        text_sections = [
            section.get("content", {}).get("text", "")
            for page in template_config.get("pages", [])
            for section in page.get("sections", [])
            if section.get("type") == "text"
        ]
        
        for i, text in enumerate(text_sections):
            if "<script>" in text.lower() or "javascript:" in text.lower():
                score -= 50
                warnings.append({
                    "severity": ValidationSeverity.WARNING.value,
                    "type": "security",
                    "message": f"Potential XSS detected in text section {i}",
                    "path": ["pages"]
                })
        
        # Check custom QR code URLs
        qr_config = template_config.get("qr_code", {})
        if qr_config.get("data_source") == "custom_url":
            custom_url = qr_config.get("custom_data", "")
            if not custom_url.startswith(("http://", "https://", "mailto:")):
                score -= 30
                warnings.append({
                    "severity": ValidationSeverity.WARNING.value,
                    "type": "security",
                    "message": "Custom QR code URL should use secure protocol",
                    "path": ["qr_code", "custom_data"]
                })
        
        return max(0, score), warnings
    
    def _check_best_practices(self, template_config: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Check template best practices"""
        warnings = []
        info = []
        
        # Check for accessibility
        if not template_config.get("metadata", {}).get("description"):
            warnings.append({
                "severity": ValidationSeverity.WARNING.value,
                "type": "accessibility",
                "message": "Template missing description for better accessibility",
                "path": ["metadata", "description"]
            })
        
        # Check for responsive design considerations
        layout = template_config.get("layout", {})
        if layout.get("orientation") == "landscape":
            info.append({
                "severity": ValidationSeverity.INFO.value,
                "type": "usability",
                "message": "Landscape orientation may be less mobile-friendly",
                "path": ["layout", "orientation"]
            })
        
        # Check for font size consistency
        fonts = template_config.get("styling", {}).get("fonts", {})
        font_sizes = [font.get("size", 12) for font in fonts.values() if font.get("size")]
        if font_sizes and (min(font_sizes) < 8 or max(font_sizes) > 24):
            warnings.append({
                "severity": ValidationSeverity.WARNING.value,
                "type": "usability",
                "message": "Font sizes outside recommended range (8-24pt)",
                "path": ["styling", "fonts"]
            })
        
        return warnings, info
    
    def _has_exercise_table(self, template_config: Dict[str, Any]) -> bool:
        """Check if template has exercise table section"""
        for page in template_config.get("pages", []):
            for section in page.get("sections", []):
                if section.get("type") == "exercise_table":
                    return True
        return False
    
    def _find_undefined_variables(self, template_config: Dict[str, Any]) -> List[str]:
        """Find variables referenced but not defined"""
        defined_vars = set(template_config.get("variables", {}).keys())
        referenced_vars = set()
        for expr, _path in self._extract_template_expressions(template_config):
            base, _filters, valid_base = self._parse_expression(expr)
            if not base or not valid_base:
                continue
            root = str(base).split(".", 1)[0]
            referenced_vars.add(root)
        return list(referenced_vars - defined_vars - set(self._allowed_builtin_vars))

    def _validate_section_semantics(self, template_config: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        errors: List[Dict[str, Any]] = []
        warnings: List[Dict[str, Any]] = []
        pages = template_config.get("pages", [])
        if not isinstance(pages, list):
            return errors, warnings
        for p_idx, page in enumerate(pages):
            if not isinstance(page, dict):
                errors.append(
                    {
                        "severity": ValidationSeverity.ERROR.value,
                        "type": "section_semantics",
                        "message": "Página inválida",
                        "path": ["pages", p_idx],
                    }
                )
                continue
            sections = page.get("sections", [])
            if not isinstance(sections, list):
                errors.append(
                    {
                        "severity": ValidationSeverity.ERROR.value,
                        "type": "section_semantics",
                        "message": "Secciones inválidas",
                        "path": ["pages", p_idx, "sections"],
                    }
                )
                continue
            for s_idx, section in enumerate(sections):
                if not isinstance(section, dict):
                    errors.append(
                        {
                            "severity": ValidationSeverity.ERROR.value,
                            "type": "section_semantics",
                            "message": "Sección inválida",
                            "path": ["pages", p_idx, "sections", s_idx],
                        }
                    )
                    continue
                section_type = section.get("type")
                content = section.get("content", {})
                base_path = ["pages", p_idx, "sections", s_idx]
                if section_type == "progress_chart":
                    warnings.append(
                        {
                            "severity": ValidationSeverity.WARNING.value,
                            "type": "section_semantics",
                            "message": "Sección progress_chart no está soportada en exportación PDF",
                            "path": base_path + ["type"],
                        }
                    )
                conditional = section.get("conditional")
                if conditional is not None:
                    if not isinstance(conditional, dict):
                        errors.append(
                            {
                                "severity": ValidationSeverity.ERROR.value,
                                "type": "section_semantics",
                                "message": "Condicional inválido",
                                "path": base_path + ["conditional"],
                            }
                        )
                    else:
                        cond_if = conditional.get("if")
                        if cond_if is not None and not isinstance(cond_if, str):
                            errors.append(
                                {
                                    "severity": ValidationSeverity.ERROR.value,
                                    "type": "section_semantics",
                                    "message": "Condición inválida",
                                    "path": base_path + ["conditional", "if"],
                                }
                            )
                if not isinstance(content, dict):
                    errors.append(
                        {
                            "severity": ValidationSeverity.ERROR.value,
                            "type": "section_semantics",
                            "message": "Contenido inválido",
                            "path": base_path + ["content"],
                        }
                    )
                    continue
                if section_type == "header":
                    if "title" in content and not isinstance(content.get("title"), str):
                        errors.append(
                            {
                                "severity": ValidationSeverity.ERROR.value,
                                "type": "section_semantics",
                                "message": "Title inválido",
                                "path": base_path + ["content", "title"],
                            }
                        )
                    if "subtitle" in content and not isinstance(content.get("subtitle"), str):
                        errors.append(
                            {
                                "severity": ValidationSeverity.ERROR.value,
                                "type": "section_semantics",
                                "message": "Subtitle inválido",
                                "path": base_path + ["content", "subtitle"],
                            }
                        )
                elif section_type == "text":
                    text_val = content.get("text")
                    if text_val is None or text_val == "":
                        warnings.append(
                            {
                                "severity": ValidationSeverity.WARNING.value,
                                "type": "section_semantics",
                                "message": "Texto vacío en sección text",
                                "path": base_path + ["content", "text"],
                            }
                        )
                    elif not isinstance(text_val, str):
                        errors.append(
                            {
                                "severity": ValidationSeverity.ERROR.value,
                                "type": "section_semantics",
                                "message": "Texto inválido en sección text",
                                "path": base_path + ["content", "text"],
                            }
                        )
                    if "style" in content and not isinstance(content.get("style"), str):
                        errors.append(
                            {
                                "severity": ValidationSeverity.ERROR.value,
                                "type": "section_semantics",
                                "message": "Style inválido en sección text",
                                "path": base_path + ["content", "style"],
                            }
                        )
                elif section_type == "table":
                    headers = content.get("headers")
                    rows = content.get("rows")
                    if headers is None or rows is None:
                        warnings.append(
                            {
                                "severity": ValidationSeverity.WARNING.value,
                                "type": "section_semantics",
                                "message": "Tabla sin headers o rows",
                                "path": base_path + ["content"],
                            }
                        )
                    if headers is not None:
                        if not isinstance(headers, list) or any(not isinstance(h, (str, int, float)) for h in headers):
                            errors.append(
                                {
                                    "severity": ValidationSeverity.ERROR.value,
                                    "type": "section_semantics",
                                    "message": "Headers inválidos en tabla",
                                    "path": base_path + ["content", "headers"],
                                }
                            )
                    if rows is not None:
                        if not isinstance(rows, list) or any(not isinstance(r, list) for r in rows):
                            errors.append(
                                {
                                    "severity": ValidationSeverity.ERROR.value,
                                    "type": "section_semantics",
                                    "message": "Rows inválidos en tabla",
                                    "path": base_path + ["content", "rows"],
                                }
                            )
                elif section_type == "image":
                    path_val = content.get("path")
                    if not path_val:
                        warnings.append(
                            {
                                "severity": ValidationSeverity.WARNING.value,
                                "type": "section_semantics",
                                "message": "Imagen sin path",
                                "path": base_path + ["content", "path"],
                            }
                        )
                    elif not isinstance(path_val, str):
                        errors.append(
                            {
                                "severity": ValidationSeverity.ERROR.value,
                                "type": "section_semantics",
                                "message": "Path inválido en imagen",
                                "path": base_path + ["content", "path"],
                            }
                        )
                    for size_key in ("width", "height"):
                        if size_key in content and not isinstance(content.get(size_key), (int, float)):
                            errors.append(
                                {
                                    "severity": ValidationSeverity.ERROR.value,
                                    "type": "section_semantics",
                                    "message": f"{size_key} inválido en imagen",
                                    "path": base_path + ["content", size_key],
                                }
                            )
                elif section_type == "qr_code":
                    size_val = content.get("size")
                    if size_val is not None and not isinstance(size_val, (int, float)):
                        errors.append(
                            {
                                "severity": ValidationSeverity.ERROR.value,
                                "type": "section_semantics",
                                "message": "Size inválido en QR",
                                "path": base_path + ["content", "size"],
                            }
                        )
                elif section_type == "spacing":
                    height_val = content.get("height")
                    if height_val is None:
                        warnings.append(
                            {
                                "severity": ValidationSeverity.WARNING.value,
                                "type": "section_semantics",
                                "message": "Spacing sin height",
                                "path": base_path + ["content", "height"],
                            }
                        )
                    elif not isinstance(height_val, (int, float)):
                        errors.append(
                            {
                                "severity": ValidationSeverity.ERROR.value,
                                "type": "section_semantics",
                                "message": "Height inválido en spacing",
                                "path": base_path + ["content", "height"],
                            }
                        )
        return errors, warnings


# Template validation utilities
def validate_template_for_gym(template_config: Dict[str, Any], gym_config: Dict[str, Any]) -> ValidationResult:
    """Validate template for specific gym requirements"""
    validator = TemplateValidator()
    result = validator.validate_template(template_config)
    
    # Add gym-specific validations
    gym_warnings = []
    
    # Check if template supports gym's equipment
    required_equipment = _extract_required_equipment(template_config)
    available_equipment = set(gym_config.get("equipment", []))
    missing_equipment = required_equipment - available_equipment
    
    if missing_equipment:
        gym_warnings.append({
            "severity": ValidationSeverity.WARNING.value,
            "type": "gym_compatibility",
            "message": f"Template requires equipment not available: {', '.join(missing_equipment)}",
            "path": ["equipment"]
        })
    
    result.warnings.extend(gym_warnings)
    result.is_valid = len(result.errors) == 0
    
    return result


def _extract_required_equipment(template_config: Dict[str, Any]) -> set:
    """Extract equipment requirements from template"""
    # This would need to be implemented based on template structure
    # For now, return empty set
    return set()


# Export main classes
__all__ = [
    "TemplateValidator",
    "ValidationResult",
    "ValidationSeverity",
    "validate_template_for_gym"
]
