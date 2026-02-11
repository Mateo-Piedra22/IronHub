"""
Template Validation System

This module provides comprehensive validation for dynamic routine templates,
including JSON schema validation, business rule validation, and performance
impact assessment.
"""

import json
import jsonschema
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


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
        self.validator = jsonschema.Draft7Validator(self.schema)
    
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
                            "enum": ["header", "footer", "inline", "separate", "none"]
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
        
        try:
            jsonschema.validate(template_config, self.schema)
        except jsonschema.ValidationError as e:
            errors.append({
                "severity": ValidationSeverity.ERROR.value,
                "type": "schema_validation",
                "message": f"Schema validation failed: {e.message}",
                "path": list(e.absolute_path),
                "schema_path": list(e.schema_path)
            })
        except jsonschema.SchemaError as e:
            errors.append({
                "severity": ValidationSeverity.ERROR.value,
                "type": "schema_error",
                "message": f"Schema error: {e.message}",
                "path": []
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
        
        # Simple variable reference detection (can be enhanced)
        template_str = json.dumps(template_config)
        import re
        var_pattern = r'\{\{(\w+)\}\}'
        referenced_vars.update(re.findall(var_pattern, template_str))
        
        return list(referenced_vars - defined_vars)


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
