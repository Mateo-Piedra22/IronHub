"""
Template Customization Component
Componente para personalizar plantillas asignadas a gimnasios
"""

import json
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class ExerciseCustomization(BaseModel):
    """Modelo para personalización de ejercicios"""
    name: Optional[str] = Field(None, description="Nombre personalizado del ejercicio")
    sets: Optional[int] = Field(None, ge=1, le=10, description="Número de series")
    reps: Optional[str] = Field(None, description="Rango de repeticiones (ej: '8-12')")
    rest: Optional[int] = Field(None, ge=0, le=600, description="Tiempo de descanso en segundos")
    notes: Optional[str] = Field(None, description="Notas personalizadas")
    enabled: bool = Field(True, description="Si el ejercicio está habilitado")
    alternative_exercise: Optional[str] = Field(None, description="Ejercicio alternativo")

class DayCustomization(BaseModel):
    """Modelo para personalización de día de entrenamiento"""
    name: Optional[str] = Field(None, description="Nombre personalizado del día")
    warmup_duration: Optional[int] = Field(None, ge=0, le=30, description="Duración del calentamiento en minutos")
    cooldown_duration: Optional[int] = Field(None, ge=0, le=30, description="Duración del enfriamiento en minutos")
    exercises: List[ExerciseCustomization] = Field(default_factory=list)
    enabled: bool = Field(True, description="Si el día está habilitado")
    notes: Optional[str] = Field(None, description="Notas del día")

class TemplateCustomizationConfig(BaseModel):
    """Configuración completa de personalización de plantilla"""
    
    # Información general
    template_name: Optional[str] = Field(None, description="Nombre personalizado de la plantilla")
    description: Optional[str] = Field(None, description="Descripción personalizada")
    tags: Optional[List[str]] = Field(None, description="Tags personalizados")
    
    # Configuración de entrenamiento
    session_duration: Optional[int] = Field(None, ge=15, le=180, description="Duración de la sesión en minutos")
    intensity_level: Optional[str] = Field(None, regex="^(bajo|medio|alto)$", description="Nivel de intensidad")
    rest_days: Optional[List[int]] = Field(None, description="Días de descanso (1-7)")
    
    # Personalización por días
    days: Dict[str, DayCustomization] = Field(default_factory=dict, description="Configuración por día")
    
    # Equipamiento disponible
    available_equipment: Optional[List[str]] = Field(None, description="Equipamiento disponible en el gimnasio")
    equipment_restrictions: Optional[List[str]] = Field(None, description="Equipamiento a evitar")
    
    # Preferencias del gimnasio
    focus_areas: Optional[List[str]] = Field(None, description="Áreas de enfoque preferidas")
    avoid_exercises: Optional[List[str]] = Field(None, description="Ejercicios a evitar")
    member_level: Optional[str] = Field(None, regex="^(principiante|intermedio|avanzado)$", description="Nivel promedio de miembros")
    
    # Configuración de progreso
    progression_style: Optional[str] = Field(None, regex="^(lineal|doble_progresion|ondulada)$", description="Estilo de progresión")
    deload_frequency: Optional[int] = Field(None, ge=2, le=12, description="Frecuencia de deload en semanas")
    
    # Configuración de visualización
    show_tips: bool = Field(True, description="Mostrar tips de ejecución")
    show_video_links: bool = Field(True, description="Mostrar enlaces a videos")
    show_calories_estimate: bool = Field(False, description="Mostrar estimación de calorías")
    
    # Configuración de idioma y formato
    language: str = Field("es", description="Idioma de la plantilla")
    weight_unit: str = Field("kg", regex="^(kg|lbs)$", description="Unidad de peso")
    distance_unit: str = Field("km", regex="^(km|miles)$", description="Unidad de distancia")

class TemplateCustomizer:
    """Clase para manejar la personalización de plantillas"""
    
    @staticmethod
    def create_default_config(base_template: Dict[str, Any]) -> TemplateCustomizationConfig:
        """
        Crear configuración de personalización por defecto basada en una plantilla
        
        Args:
            base_template: Plantilla base para extraer configuración inicial
            
        Returns:
            TemplateCustomizationConfig: Configuración por defecto
        """
        config_data = {}
        
        # Extraer información básica
        layout = base_template.get("layout", {})
        exercises = base_template.get("exercises", {})
        
        config_data["session_duration"] = layout.get("session_duration", 60)
        config_data["rest_days"] = layout.get("rest_days", [])
        config_data["focus_areas"] = [base_template.get("categoria", "general")]
        
        # Crear configuración por días
        days_config = {}
        for day_key, day_data in exercises.items():
            day_config = DayCustomization(
                name=day_data.get("name", f"Día {day_key.split('_')[1]}"),
                warmup_duration=day_data.get("warmup", {}).get("duration", 5),
                cooldown_duration=day_data.get("cooldown", {}).get("duration", 5)
            )
            
            # Configurar ejercicios
            exercises_list = day_data.get("main_exercises", [])
            if isinstance(exercises_list, list):
                day_config.exercises = [
                    ExerciseCustomization(
                        name=ex.get("name"),
                        sets=ex.get("sets"),
                        reps=ex.get("reps"),
                        rest=ex.get("rest"),
                        notes=ex.get("notes"),
                        enabled=True
                    )
                    for ex in exercises_list
                ]
            
            days_config[day_key] = day_config
        
        config_data["days"] = days_config
        
        return TemplateCustomizationConfig(**config_data)
    
    @staticmethod
    def apply_customization(
        base_template: Dict[str, Any], 
        customization: TemplateCustomizationConfig
    ) -> Dict[str, Any]:
        """
        Aplicar personalización a una plantilla base
        
        Args:
            base_template: Plantilla original
            customization: Configuración de personalización
            
        Returns:
            Dict[str, Any]: Plantilla personalizada
        """
        # Crear copia profunda de la plantilla
        customized_template = json.loads(json.dumps(base_template))
        
        # Aplicar personalización general
        if customization.template_name:
            customized_template["nombre"] = customization.template_name
        
        if customization.description:
            customized_template["descripcion"] = customization.description
        
        if customization.tags:
            customized_template["tags"] = customization.tags
        
        # Actualizar layout
        layout = customized_template.get("layout", {})
        if customization.session_duration:
            layout["session_duration"] = customization.session_duration
        
        if customization.rest_days:
            layout["rest_days"] = customization.rest_days
        
        customized_template["layout"] = layout
        
        # Aplicar personalización por días
        exercises = customized_template.get("exercises", {})
        for day_key, day_config in customization.days.items():
            if day_key in exercises:
                day_data = exercises[day_key]
                
                # Actualizar información del día
                if day_config.name:
                    day_data["name"] = day_config.name
                
                # Actualizar warmup y cooldown
                if day_config.warmup_duration:
                    warmup = day_data.get("warmup", {})
                    warmup["duration"] = day_config.warmup_duration
                    day_data["warmup"] = warmup
                
                if day_config.cooldown_duration:
                    cooldown = day_data.get("cooldown", {})
                    cooldown["duration"] = day_config.cooldown_duration
                    day_data["cooldown"] = cooldown
                
                # Actualizar ejercicios
                main_exercises = day_data.get("main_exercises", [])
                if isinstance(main_exercises, list) and day_config.exercises:
                    for i, exercise_config in enumerate(day_config.exercises):
                        if i < len(main_exercises):
                            exercise = main_exercises[i]
                            
                            if exercise_config.name:
                                exercise["name"] = exercise_config.name
                            
                            if exercise_config.sets:
                                exercise["sets"] = exercise_config.sets
                            
                            if exercise_config.reps:
                                exercise["reps"] = exercise_config.reps
                            
                            if exercise_config.rest:
                                exercise["rest"] = exercise_config.rest
                            
                            if exercise_config.notes:
                                exercise["notes"] = exercise_config.notes
                            
                            if not exercise_config.enabled:
                                # Deshabilitar ejercicio (marcar como opcional)
                                exercise["optional"] = True
                            
                            if exercise_config.alternative_exercise:
                                exercise["alternative"] = exercise_config.alternative_exercise
                
                # Agregar notas del día
                if day_config.notes:
                    day_data["notes"] = day_config.notes
                
                # Deshabilitar día completo si es necesario
                if not day_config.enabled:
                    day_data["disabled"] = True
        
        customized_template["exercises"] = exercises
        
        # Agregar metadatos de personalización
        customized_template["customization_metadata"] = {
            "customized": True,
            "focus_areas": customization.focus_areas,
            "intensity_level": customization.intensity_level,
            "member_level": customization.member_level,
            "available_equipment": customization.available_equipment,
            "equipment_restrictions": customization.equipment_restrictions,
            "avoid_exercises": customization.avoid_exercises,
            "progression_style": customization.progression_style,
            "deload_frequency": customization.deload_frequency,
            "show_tips": customization.show_tips,
            "show_video_links": customization.show_video_links,
            "show_calories_estimate": customization.show_calories_estimate,
            "language": customization.language,
            "weight_unit": customization.weight_unit,
            "distance_unit": customization.distance_unit
        }
        
        return customized_template
    
    @staticmethod
    def validate_customization(
        customization: TemplateCustomizationConfig,
        base_template: Dict[str, Any]
    ) -> List[str]:
        """
        Validar configuración de personalización
        
        Args:
            customization: Configuración a validar
            base_template: Plantilla base para referencia
            
        Returns:
            List[str]: Lista de errores (vacía si es válida)
        """
        errors = []
        
        # Validar duración de sesión
        if customization.session_duration:
            if customization.session_duration < 15 or customization.session_duration > 180:
                errors.append("La duración de la sesión debe estar entre 15 y 180 minutos")
        
        # Validar días de descanso
        if customization.rest_days:
            if any(day < 1 or day > 7 for day in customization.rest_days):
                errors.append("Los días de descanso deben estar entre 1 y 7")
        
        # Validar configuración por días
        base_days = base_template.get("exercises", {})
        for day_key, day_config in customization.days.items():
            if day_key not in base_days:
                errors.append(f"El día {day_key} no existe en la plantilla base")
                continue
            
            # Validar ejercicios
            base_exercises = base_days[day_key].get("main_exercises", [])
            if isinstance(base_exercises, list):
                if len(day_config.exercises) != len(base_exercises):
                    errors.append(f"El número de ejercicios en {day_key} no coincide con la plantilla base")
                
                # Validar rangos de repeticiones
                for exercise_config in day_config.exercises:
                    if exercise_config.reps:
                        # Validar formato de reps (ej: "8-12", "10", "6-8-10")
                        reps_pattern = r'^\d+(-\d+)*$'
                        import re
                        if not re.match(reps_pattern, exercise_config.reps):
                            errors.append(f"Formato de repeticiones inválido: {exercise_config.reps}")
        
        # Validar equipamiento
        if customization.available_equipment and customization.equipment_restrictions:
            overlap = set(customization.available_equipment) & set(customization.equipment_restrictions)
            if overlap:
                errors.append(f"Equipamiento en conflicto: {', '.join(overlap)}")
        
        return errors
    
    @staticmethod
    def get_customization_preview(
        base_template: Dict[str, Any],
        customization: TemplateCustomizationConfig
    ) -> Dict[str, Any]:
        """
        Generar vista previa de cambios de personalización
        
        Args:
            base_template: Plantilla base
            customization: Configuración de personalización
            
        Returns:
            Dict[str, Any]: Resumen de cambios
        """
        changes = {
            "general": [],
            "layout": [],
            "days": {},
            "new_features": []
        }
        
        # Cambios generales
        if customization.template_name:
            changes["general"].append(f"Nombre: '{base_template.get('nombre', '')}' → '{customization.template_name}'")
        
        if customization.description:
            changes["general"].append("Descripción personalizada")
        
        if customization.tags:
            changes["general"].append(f"Tags: {', '.join(customization.tags)}")
        
        # Cambios de layout
        if customization.session_duration:
            original_duration = base_template.get("layout", {}).get("session_duration", 60)
            changes["layout"].append(f"Duración: {original_duration}min → {customization.session_duration}min")
        
        if customization.rest_days:
            changes["layout"].append(f"Días de descanso: {customization.rest_days}")
        
        # Cambios por días
        exercises = base_template.get("exercises", {})
        for day_key, day_config in customization.days.items():
            day_changes = []
            
            if day_key in exercises:
                if day_config.name and day_config.name != exercises[day_key].get("name"):
                    day_changes.append(f"Nombre: '{exercises[day_key].get('name')}' → '{day_config.name}'")
                
                # Cambios en ejercicios
                base_exercises = exercises[day_key].get("main_exercises", [])
                if isinstance(base_exercises, list):
                    for i, exercise_config in enumerate(day_config.exercises):
                        if i < len(base_exercises):
                            base_exercise = base_exercises[i]
                            exercise_changes = []
                            
                            if exercise_config.name and exercise_config.name != base_exercise.get("name"):
                                exercise_changes.append(f"Nombre: {exercise_config.name}")
                            
                            if exercise_config.sets and exercise_config.sets != base_exercise.get("sets"):
                                exercise_changes.append(f"Series: {base_exercise.get('sets')} → {exercise_config.sets}")
                            
                            if exercise_config.reps and exercise_config.reps != base_exercise.get("reps"):
                                exercise_changes.append(f"Reps: {base_exercise.get('reps')} → {exercise_config.reps}")
                            
                            if exercise_config.rest and exercise_config.rest != base_exercise.get("rest"):
                                exercise_changes.append(f"Descanso: {base_exercise.get('rest')}s → {exercise_config.rest}s")
                            
                            if exercise_changes:
                                day_changes.append(f"Ejercicio {i+1}: {', '.join(exercise_changes)}")
                
                if not day_config.enabled:
                    day_changes.append("Día deshabilitado")
            
            if day_changes:
                changes["days"][day_key] = day_changes
        
        # Nuevas características
        if customization.show_tips:
            changes["new_features"].append("Tips de ejecución")
        
        if customization.show_video_links:
            changes["new_features"].append("Enlaces a videos")
        
        if customization.show_calories_estimate:
            changes["new_features"].append("Estimación de calorías")
        
        if customization.focus_areas:
            changes["new_features"].append(f"Enfoque en: {', '.join(customization.focus_areas)}")
        
        return changes

# Utilidades para personalización común
COMMON_CUSTOMIZATIONS = {
    "principiante": {
        "intensity_level": "bajo",
        "member_level": "principiante",
        "session_duration": 45,
        "show_tips": True,
        "show_video_links": True
    },
    "intermedio": {
        "intensity_level": "medio",
        "member_level": "intermedio",
        "session_duration": 60,
        "show_tips": True,
        "progression_style": "doble_progresion"
    },
    "avanzado": {
        "intensity_level": "alto",
        "member_level": "avanzado",
        "session_duration": 75,
        "progression_style": "ondulada",
        "deload_frequency": 4
    },
    "equipamiento_basico": {
        "available_equipment": ["barra", "mancuernas", "pesas", "banco"],
        "equipment_restrictions": ["maquina", "cable", "kettlebell"]
    },
    "equipamiento_completo": {
        "available_equipment": ["barra", "mancuernas", "pesas", "banco", "maquina", "cable", "kettlebell", "bandas"]
    },
    "enfocado_fuerza": {
        "focus_areas": ["fuerza", "potencia"],
        "intensity_level": "alto",
        "rest_days": [2, 4, 7]
    },
    "enfocado_hipertrofia": {
        "focus_areas": ["hipertrofia", "volumen"],
        "intensity_level": "medio",
        "session_duration": 70,
        "progression_style": "doble_progresion"
    }
}

def apply_preset_customization(
    base_template: Dict[str, Any],
    preset_name: str
) -> Dict[str, Any]:
    """
    Aplicar personalización predefinida a una plantilla
    
    Args:
        base_template: Plantilla base
        preset_name: Nombre del preset (de COMMON_CUSTOMIZATIONS)
        
    Returns:
        Dict[str, Any]: Plantilla personalizada
    """
    if preset_name not in COMMON_CUSTOMIZATIONS:
        raise ValueError(f"Preset '{preset_name}' no encontrado")
    
    preset_config = COMMON_CUSTOMIZATIONS[preset_name]
    
    # Crear configuración de personalización
    customization_config = TemplateCustomizationConfig(**preset_config)
    
    # Aplicar personalización
    return TemplateCustomizer.apply_customization(base_template, customization_config)
