"""
Variable Resolver

This module provides advanced variable resolution for dynamic templates,
including calculated variables, user data access, gym data, and custom expressions.
"""

import re
import json
from typing import Dict, Any, List, Optional, Union, Callable
from datetime import datetime, date, timedelta
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class VariableType(Enum):
    """Variable types for template processing"""
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    DATE = "date"
    ARRAY = "array"
    EXERCISE_LIST = "exercise_list"
    USER_DATA = "user_data"
    GYM_DATA = "gym_data"
    CALCULATED = "calculated"
    CONDITIONAL = "conditional"


@dataclass
class VariableContext:
    """Context for variable resolution"""
    template_data: Dict[str, Any]
    user_data: Optional[Dict[str, Any]] = None
    gym_data: Optional[Dict[str, Any]] = None
    routine_data: Optional[Dict[str, Any]] = None
    exercise_data: Optional[List[Dict[str, Any]]] = None
    global_vars: Optional[Dict[str, Any]] = None
    functions: Optional[Dict[str, Callable]] = None


class VariableResolver:
    """Advanced variable resolution system"""
    
    def __init__(self):
        self.built_in_functions = self._initialize_built_in_functions()
        self.expression_cache = {}
    
    def resolve_variables(
        self,
        template_config: Dict[str, Any],
        context: VariableContext
    ) -> Dict[str, Any]:
        """Resolve all template variables"""
        resolved = {}
        variables = template_config.get("variables", {})
        
        # Resolve each variable
        for var_name, var_config in variables.items():
            try:
                value = self.resolve_variable(var_name, var_config, context)
                resolved[var_name] = value
            except Exception as e:
                logger.warning(f"Error resolving variable {var_name}: {e}")
                # Use default value or empty string
                resolved[var_name] = var_config.get("default", "")
        
        # Add global variables
        if context.global_vars:
            resolved.update(context.global_vars)
        
        return resolved
    
    def resolve_variable(
        self,
        var_name: str,
        var_config: Dict[str, Any],
        context: VariableContext
    ) -> Any:
        """Resolve a single variable"""
        var_type = var_config.get("type", VariableType.STRING.value)
        
        # Check if variable already exists in context
        if var_name in context.template_data:
            return context.template_data[var_name]
        
        # Resolve based on type
        if var_type == VariableType.CALCULATED.value:
            return self._resolve_calculated_variable(var_name, var_config, context)
        elif var_type == VariableType.USER_DATA.value:
            return self._resolve_user_data_variable(var_name, var_config, context)
        elif var_type == VariableType.GYM_DATA.value:
            return self._resolve_gym_data_variable(var_name, var_config, context)
        elif var_type == VariableType.EXERCISE_LIST.value:
            return self._resolve_exercise_list_variable(var_name, var_config, context)
        elif var_type == VariableType.CONDITIONAL.value:
            return self._resolve_conditional_variable(var_name, var_config, context)
        elif var_type == VariableType.DATE.value:
            return self._resolve_date_variable(var_name, var_config, context)
        elif var_type == VariableType.ARRAY.value:
            return self._resolve_array_variable(var_name, var_config, context)
        else:
            # Default to string/number/boolean
            return self._resolve_simple_variable(var_name, var_config, context)
    
    def resolve_template_string(
        self,
        template_str: str,
        context: VariableContext
    ) -> str:
        """Resolve variables in template string"""
        if not template_str:
            return ""
        
        # Find all variable references
        pattern = r'\{\{([^}]+)\}\}'
        matches = re.findall(pattern, template_str)
        
        result = template_str
        for match in matches:
            var_name = match.strip()
            
            # Handle nested property access (e.g., "usuario.nombre")
            if "." in var_name:
                value = self._resolve_nested_property(var_name, context)
            else:
                # Check if it's a variable definition
                if var_name in context.template_data:
                    value = context.template_data[var_name]
                else:
                    # Try to resolve as simple variable
                    value = self._resolve_simple_value(var_name, context)
            
            result = result.replace(f"{{{{{var_name}}}}}", str(value))
        
        return result
    
    def evaluate_expression(
        self,
        expression: str,
        context: VariableContext
    ) -> Any:
        """Evaluate mathematical or logical expression"""
        # Cache expressions for performance
        if expression in self.expression_cache:
            func = self.expression_cache[expression]
        else:
            func = self._compile_expression(expression)
            self.expression_cache[expression] = func
        
        return func(context)
    
    # === Variable Type Resolvers ===
    
    def _resolve_calculated_variable(
        self,
        var_name: str,
        var_config: Dict[str, Any],
        context: VariableContext
    ) -> Any:
        """Resolve calculated variable"""
        calculation = var_config.get("calculation", "")
        
        if not calculation:
            return var_config.get("default", 0)
        
        try:
            # Evaluate calculation
            return self.evaluate_expression(calculation, context)
        except Exception as e:
            logger.warning(f"Error in calculation for {var_name}: {e}")
            return var_config.get("default", 0)
    
    def _resolve_user_data_variable(
        self,
        var_name: str,
        var_config: Dict[str, Any],
        context: VariableContext
    ) -> Any:
        """Resolve user data variable"""
        if not context.user_data:
            return var_config.get("default", "")
        
        field_path = var_config.get("field", var_name)
        return self._get_nested_value(context.user_data, field_path, var_config.get("default", ""))
    
    def _resolve_gym_data_variable(
        self,
        var_name: str,
        var_config: Dict[str, Any],
        context: VariableContext
    ) -> Any:
        """Resolve gym data variable"""
        if not context.gym_data:
            return var_config.get("default", "")
        
        field_path = var_config.get("field", var_name)
        return self._get_nested_value(context.gym_data, field_path, var_config.get("default", ""))
    
    def _resolve_exercise_list_variable(
        self,
        var_name: str,
        var_config: Dict[str, Any],
        context: VariableContext
    ) -> Any:
        """Resolve exercise list variable"""
        if not context.exercise_data:
            return var_config.get("default", [])
        
        operation = var_config.get("operation", "list")
        day_filter = var_config.get("day_filter")
        
        if operation == "count":
            if day_filter is not None:
                # Count exercises for specific day
                day_exercises = next(
                    (d.get("ejercicios", []) for d in context.exercise_data if d.get("numero") == day_filter),
                    []
                )
                return len(day_exercises)
            else:
                # Count all exercises
                return sum(len(d.get("ejercicios", [])) for d in context.exercise_data)
        
        elif operation == "list":
            if day_filter is not None:
                # Get exercises for specific day
                day_data = next(
                    (d for d in context.exercise_data if d.get("numero") == day_filter),
                    None
                )
                return day_data.get("ejercicios", []) if day_data else []
            else:
                # Get all exercises
                all_exercises = []
                for day in context.exercise_data:
                    all_exercises.extend(day.get("ejercicios", []))
                return all_exercises
        
        elif operation == "names":
            exercises = self._resolve_exercise_list_variable(var_name, var_config, context)
            return [ex.get("nombre", "") for ex in exercises]
        
        return var_config.get("default", [])
    
    def _resolve_conditional_variable(
        self,
        var_name: str,
        var_config: Dict[str, Any],
        context: VariableContext
    ) -> Any:
        """Resolve conditional variable"""
        condition = var_config.get("condition", "")
        true_value = var_config.get("true_value", True)
        false_value = var_config.get("false_value", False)
        
        try:
            result = self.evaluate_expression(condition, context)
            return true_value if result else false_value
        except Exception as e:
            logger.warning(f"Error in condition for {var_name}: {e}")
            return false_value
    
    def _resolve_date_variable(
        self,
        var_name: str,
        var_config: Dict[str, Any],
        context: VariableContext
    ) -> Any:
        """Resolve date variable"""
        date_source = var_config.get("source", "current")
        format_str = var_config.get("format", "%d/%m/%Y")
        
        if date_source == "current":
            date_obj = datetime.now()
        elif date_source == "routine_creation":
            if context.routine_data and "fecha_creacion" in context.routine_data:
                date_obj = context.routine_data["fecha_creacion"]
            else:
                date_obj = datetime.now()
        else:
            date_obj = datetime.now()
        
        return date_obj.strftime(format_str)
    
    def _resolve_array_variable(
        self,
        var_name: str,
        var_config: Dict[str, Any],
        context: VariableContext
    ) -> Any:
        """Resolve array variable"""
        items = var_config.get("items", [])
        separator = var_config.get("separator", ", ")
        
        # Process each item
        processed_items = []
        for item in items:
            if isinstance(item, str):
                # Resolve template variables in item
                processed_item = self.resolve_template_string(item, context)
                processed_items.append(processed_item)
            else:
                processed_items.append(item)
        
        # Join if separator is specified
        if separator and isinstance(processed_items, list):
            return separator.join(str(item) for item in processed_items)
        
        return processed_items
    
    def _resolve_simple_variable(
        self,
        var_name: str,
        var_config: Dict[str, Any],
        context: VariableContext
    ) -> Any:
        """Resolve simple variable (string, number, boolean)"""
        var_type = var_config.get("type", "string")
        default_value = var_config.get("default", "")
        
        # Try to get value from context
        if var_name in context.template_data:
            value = context.template_data[var_name]
        else:
            value = default_value
        
        # Type conversion
        if var_type == "number":
            try:
                return float(value) if value else 0
            except:
                return 0
        elif var_type == "boolean":
            if isinstance(value, bool):
                return value
            elif isinstance(value, str):
                return value.lower() in ("true", "1", "yes", "on")
            else:
                return bool(value)
        else:
            return str(value) if value is not None else ""
    
    # === Expression Evaluation ===
    
    def _compile_expression(self, expression: str) -> Callable:
        """Compile expression for evaluation"""
        # This is a simplified expression compiler
        # In production, you might want to use a more sophisticated parser
        
        def compiled_func(context: VariableContext) -> Any:
            # Replace variables in expression
            processed_expr = expression
            
            # Find and replace variables
            var_pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)\b'
            
            def replace_var(match):
                var_path = match.group(1)
                value = self._resolve_nested_property(var_path, context)
                return str(value)
            
            processed_expr = re.sub(var_pattern, replace_var, processed_expr)
            
            # Evaluate expression (simplified - in production use proper expression parser)
            try:
                # Safe evaluation with limited context
                allowed_names = {
                    "len": len,
                    "sum": sum,
                    "max": max,
                    "min": min,
                    "abs": abs,
                    "round": round,
                    "True": True,
                    "False": False,
                    "None": None,
                }
                
                # Add built-in functions
                if context.functions:
                    allowed_names.update(context.functions)
                
                return eval(processed_expr, {"__builtins__": {}}, allowed_names)
            except:
                logger.warning(f"Error evaluating expression: {processed_expr}")
                return 0
        
        return compiled_func
    
    # === Utility Methods ===
    
    def _resolve_nested_property(self, property_path: str, context: VariableContext) -> Any:
        """Resolve nested property (e.g., 'usuario.nombre' or 'dias.0.ejercicios')"""
        parts = property_path.split(".")
        
        # Start with template data
        current = context.template_data
        
        for part in parts:
            if isinstance(current, dict):
                if part in current:
                    current = current[part]
                else:
                    # Try other context sources
                    if part == "usuario" and context.user_data:
                        current = context.user_data
                    elif part == "gimnasio" and context.gym_data:
                        current = context.gym_data
                    elif part == "rutina" and context.routine_data:
                        current = context.routine_data
                    elif part == "ejercicios" and context.exercise_data:
                        current = context.exercise_data
                    else:
                        return ""
            elif isinstance(current, list):
                try:
                    index = int(part)
                    if 0 <= index < len(current):
                        current = current[index]
                    else:
                        return ""
                except:
                    return ""
            else:
                return ""
        
        return current if current is not None else ""
    
    def _get_nested_value(self, data: Dict[str, Any], path: str, default: Any = "") -> Any:
        """Get nested value from dictionary"""
        parts = path.split(".")
        current = data
        
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return default
        
        return current if current is not None else default
    
    def _resolve_simple_value(self, var_name: str, context: VariableContext) -> Any:
        """Resolve simple variable value"""
        # Check template data first
        if var_name in context.template_data:
            return context.template_data[var_name]
        
        # Check user data
        if context.user_data and var_name in context.user_data:
            return context.user_data[var_name]
        
        # Check gym data
        if context.gym_data and var_name in context.gym_data:
            return context.gym_data[var_name]
        
        # Check routine data
        if context.routine_data and var_name in context.routine_data:
            return context.routine_data[var_name]
        
        # Return empty string if not found
        return ""
    
    def _initialize_built_in_functions(self) -> Dict[str, Callable]:
        """Initialize built-in functions for expressions"""
        return {
            # Math functions
            "add": lambda x, y: x + y,
            "subtract": lambda x, y: x - y,
            "multiply": lambda x, y: x * y,
            "divide": lambda x, y: x / y if y != 0 else 0,
            "modulo": lambda x, y: x % y if y != 0 else 0,
            "power": lambda x, y: x ** y,
            "sqrt": lambda x: x ** 0.5 if x >= 0 else 0,
            
            # String functions
            "upper": lambda x: str(x).upper(),
            "lower": lambda x: str(x).lower(),
            "title": lambda x: str(x).title(),
            "capitalize": lambda x: str(x).capitalize(),
            "length": lambda x: len(x) if hasattr(x, '__len__') else 0,
            "concat": lambda *args: "".join(str(arg) for arg in args),
            
            # Date functions
            "now": lambda: datetime.now(),
            "today": lambda: date.today(),
            "format_date": lambda d, f: d.strftime(f) if isinstance(d, (datetime, date)) else str(d),
            "days_between": lambda d1, d2: abs((d2 - d1).days) if isinstance(d1, (datetime, date)) and isinstance(d2, (datetime, date)) else 0,
            
            # Array functions
            "first": lambda arr: arr[0] if arr and len(arr) > 0 else None,
            "last": lambda arr: arr[-1] if arr and len(arr) > 0 else None,
            "join": lambda arr, sep: sep.join(str(item) for item in arr) if arr else "",
            
            # Conditional functions
            "if": lambda condition, true_val, false_val: true_val if condition else false_val,
            "and": lambda *args: all(args),
            "or": lambda *args: any(args),
            "not": lambda x: not x,
            
            # Exercise-specific functions
            "total_exercises": lambda context: sum(len(d.get("ejercicios", [])) for d in context.exercise_data) if context.exercise_data else 0,
            "exercises_for_day": lambda day, context: next((d.get("ejercicios", []) for d in context.exercise_data if d.get("numero") == day), []) if context.exercise_data else [],
            "exercise_count_for_day": lambda day, context: len(self._exercises_for_day(day, context)),
        }
    
    def _exercises_for_day(self, day: int, context: VariableContext) -> List[Dict[str, Any]]:
        """Get exercises for specific day"""
        if not context.exercise_data:
            return []
        
        for day_data in context.exercise_data:
            if day_data.get("numero") == day:
                return day_data.get("ejercicios", [])
        
        return []


# Export main classes
__all__ = [
    "VariableResolver",
    "VariableContext",
    "VariableType"
]
