"""
Exercise Table Builder

This module provides advanced exercise table building for dynamic routine templates,
including weekly progression, exercise variations, supersets, and custom formatting.
"""

from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from enum import Enum
import logging

from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Table, TableStyle, Paragraph, Spacer

logger = logging.getLogger(__name__)


class TableFormat(Enum):
    """Exercise table formats"""
    BASIC = "basic"
    DETAILED = "detailed"
    COMPACT = "compact"
    WEEKLY = "weekly"
    PROGRESSION = "progression"


class ExerciseColumn(Enum):
    """Available exercise table columns"""
    EXERCISE_NAME = "exercise_name"
    SETS = "sets"
    REPS = "reps"
    WEIGHT = "weight"
    REST = "rest"
    DURATION = "duration"
    INTENSITY = "intensity"
    TEMPO = "tempo"
    RPE = "rpe"
    NOTES = "notes"
    MUSCLE_GROUP = "muscle_group"
    EQUIPMENT = "equipment"


@dataclass
class TableConfig:
    """Configuration for exercise table"""
    format: TableFormat = TableFormat.BASIC
    columns: List[ExerciseColumn] = None
    show_weekly: bool = False
    current_week: int = 1
    total_weeks: int = 4
    group_by_day: bool = True
    show_day_headers: bool = True
    show_totals: bool = False
    alternate_row_colors: bool = True
    include_exercise_images: bool = False
    custom_styles: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.columns is None:
            self.columns = [
                ExerciseColumn.EXERCISE_NAME,
                ExerciseColumn.SETS,
                ExerciseColumn.REPS,
                ExerciseColumn.REST,
                ExerciseColumn.NOTES
            ]


@dataclass
class ExerciseData:
    """Exercise data structure"""
    id: int
    name: str
    sets: int
    reps: Union[str, int, List[str]]
    weight: Optional[Union[str, float, List[float]]] = None
    rest: Optional[Union[str, int]] = None
    duration: Optional[Union[str, int]] = None
    intensity: Optional[Union[str, float]] = None
    tempo: Optional[str] = None
    rpe: Optional[Union[str, int]] = None
    notes: Optional[str] = None
    muscle_group: Optional[str] = None
    equipment: Optional[str] = None
    variation_id: Optional[str] = None
    supergroup_id: Optional[str] = None
    order: int = 0
    day_number: int = 1


class ExerciseTableBuilder:
    """Advanced exercise table builder"""
    
    def __init__(self):
        self.default_styles = self._create_default_styles()
        self.column_configs = self._create_column_configs()
    
    def build_exercise_table(
        self,
        exercises: List[Dict[str, Any]],
        config: TableConfig,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Any]:
        """Build exercise table with specified configuration"""
        try:
            # Convert exercise data
            exercise_data = self._convert_exercise_data(exercises)
            
            # Group exercises by day if needed
            if config.group_by_day:
                return self._build_grouped_table(exercise_data, config, context)
            else:
                return self._build_simple_table(exercise_data, config, context)
                
        except Exception as e:
            logger.error(f"Error building exercise table: {e}")
            return []
    
    def build_weekly_progression_table(
        self,
        exercises: List[Dict[str, Any]],
        config: TableConfig,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Any]:
        """Build weekly progression table"""
        try:
            exercise_data = self._convert_exercise_data(exercises)
            return self._build_weekly_table(exercise_data, config, context)
            
        except Exception as e:
            logger.error(f"Error building weekly progression table: {e}")
            return []
    
    def build_superset_table(
        self,
        exercises: List[Dict[str, Any]],
        config: TableConfig,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Any]:
        """Build superset table"""
        try:
            exercise_data = self._convert_exercise_data(exercises)
            return self._build_superset_table(exercise_data, config, context)
            
        except Exception as e:
            logger.error(f"Error building superset table: {e}")
            return []
    
    # === Table Building Methods ===
    
    def _build_simple_table(
        self,
        exercises: List[ExerciseData],
        config: TableConfig,
        context: Optional[Dict[str, Any]]
    ) -> List[Any]:
        """Build simple exercise table"""
        elements = []
        
        if not exercises:
            return elements
        
        # Create table data
        headers = self._get_table_headers(config)
        rows = []
        
        for exercise in exercises:
            row = self._build_exercise_row(exercise, config, context)
            rows.append(row)
        
        # Create table
        table_data = [headers] + rows
        table = Table(table_data, colWidths=self._get_column_widths(config))
        
        # Apply styles
        self._apply_table_styles(table, config)
        
        elements.append(table)
        elements.append(Spacer(1, 12))
        
        return elements
    
    def _build_grouped_table(
        self,
        exercises: List[ExerciseData],
        config: TableConfig,
        context: Optional[Dict[str, Any]]
    ) -> List[Any]:
        """Build grouped exercise table (by day)"""
        elements = []
        
        if not exercises:
            return elements
        
        # Group exercises by day
        days = {}
        for exercise in exercises:
            day_num = exercise.day_number
            if day_num not in days:
                days[day_num] = []
            days[day_num].append(exercise)
        
        # Build table for each day
        for day_num in sorted(days.keys()):
            day_exercises = days[day_num]
            
            # Add day header
            if config.show_day_headers:
                day_header = Paragraph(f"Día {day_num}", self.default_styles["day_header"])
                elements.append(day_header)
                elements.append(Spacer(1, 6))
            
            # Build day table
            headers = self._get_table_headers(config)
            rows = []
            
            for exercise in day_exercises:
                row = self._build_exercise_row(exercise, config, context)
                rows.append(row)
            
            # Create table
            table_data = [headers] + rows
            table = Table(table_data, colWidths=self._get_column_widths(config))
            
            # Apply styles
            self._apply_table_styles(table, config)
            
            elements.append(table)
            elements.append(Spacer(1, 20))
        
        return elements
    
    def _build_weekly_table(
        self,
        exercises: List[ExerciseData],
        config: TableConfig,
        context: Optional[Dict[str, Any]]
    ) -> List[Any]:
        """Build weekly progression table"""
        elements = []
        
        if not exercises:
            return elements
        
        # Group exercises by day
        days = {}
        for exercise in exercises:
            day_num = exercise.day_number
            if day_num not in days:
                days[day_num] = []
            days[day_num].append(exercise)
        
        # Build weekly table for each day
        for day_num in sorted(days.keys()):
            day_exercises = days[day_num]
            
            # Add day header
            if config.show_day_headers:
                day_header = Paragraph(f"Día {day_num} - Progresión Semanal", self.default_styles["day_header"])
                elements.append(day_header)
                elements.append(Spacer(1, 6))
            
            # Create weekly headers
            headers = ["Ejercicio"] + [f"Semana {i+1}" for i in range(config.total_weeks)]
            
            # Build weekly rows
            rows = []
            for exercise in day_exercises:
                row = [exercise.name]
                
                # Add weekly values
                for week in range(1, config.total_weeks + 1):
                    weekly_value = self._get_weekly_value(exercise, week, config)
                    row.append(weekly_value)
                
                rows.append(row)
            
            # Create table
            table_data = [headers] + rows
            col_widths = [3*inch] + [1.2*inch] * config.total_weeks
            table = Table(table_data, colWidths=col_widths)
            
            # Apply weekly styles
            self._apply_weekly_table_styles(table, config)
            
            elements.append(table)
            elements.append(Spacer(1, 20))
        
        return elements
    
    def _build_superset_table(
        self,
        exercises: List[ExerciseData],
        config: TableConfig,
        context: Optional[Dict[str, Any]]
    ) -> List[Any]:
        """Build superset table"""
        elements = []
        
        if not exercises:
            return elements
        
        # Group exercises by superset
        supersets = {}
        regular_exercises = []
        
        for exercise in exercises:
            if exercise.supergroup_id:
                if exercise.supergroup_id not in supersets:
                    supersets[exercise.supergroup_id] = []
                supersets[exercise.supergroup_id].append(exercise)
            else:
                regular_exercises.append(exercise)
        
        # Build regular exercises table
        if regular_exercises:
            regular_elements = self._build_simple_table(regular_exercises, config, context)
            elements.extend(regular_elements)
        
        # Build superset tables
        for superset_id in sorted(supersets.keys()):
            superset_exercises = supersets[superset_id]
            
            # Add superset header
            superset_header = Paragraph(f"Superset {superset_id}", self.default_styles["superset_header"])
            elements.append(superset_header)
            elements.append(Spacer(1, 6))
            
            # Build superset table
            headers = self._get_table_headers(config)
            rows = []
            
            for exercise in superset_exercises:
                row = self._build_exercise_row(exercise, config, context)
                rows.append(row)
            
            # Create table
            table_data = [headers] + rows
            table = Table(table_data, colWidths=self._get_column_widths(config))
            
            # Apply superset styles
            self._apply_superset_table_styles(table, config)
            
            elements.append(table)
            elements.append(Spacer(1, 20))
        
        return elements
    
    # === Row Building Methods ===
    
    def _build_exercise_row(
        self,
        exercise: ExerciseData,
        config: TableConfig,
        context: Optional[Dict[str, Any]]
    ) -> List[str]:
        """Build exercise row data"""
        row = []
        
        for column in config.columns:
            cell_value = self._get_column_value(exercise, column, config, context)
            row.append(str(cell_value))
        
        return row
    
    def _get_column_value(
        self,
        exercise: ExerciseData,
        column: ExerciseColumn,
        config: TableConfig,
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Get value for specific column"""
        if column == ExerciseColumn.EXERCISE_NAME:
            return exercise.name
        elif column == ExerciseColumn.SETS:
            return str(exercise.sets)
        elif column == ExerciseColumn.REPS:
            if config.show_weekly:
                return self._get_weekly_value(exercise, config.current_week, config)
            else:
                return str(exercise.reps)
        elif column == ExerciseColumn.WEIGHT:
            return self._format_weight(exercise.weight, config)
        elif column == ExerciseColumn.REST:
            return self._format_rest(exercise.rest)
        elif column == ExerciseColumn.DURATION:
            return self._format_duration(exercise.duration)
        elif column == ExerciseColumn.INTENSITY:
            return self._format_intensity(exercise.intensity)
        elif column == ExerciseColumn.TEMPO:
            return exercise.tempo or ""
        elif column == ExerciseColumn.RPE:
            return self._format_rpe(exercise.rpe)
        elif column == ExerciseColumn.NOTES:
            return exercise.notes or ""
        elif column == ExerciseColumn.MUSCLE_GROUP:
            return exercise.muscle_group or ""
        elif column == ExerciseColumn.EQUIPMENT:
            return exercise.equipment or ""
        else:
            return ""
    
    def _get_weekly_value(
        self,
        exercise: ExerciseData,
        week: int,
        config: TableConfig
    ) -> str:
        """Get weekly value for exercise"""
        if isinstance(exercise.reps, list):
            if week <= len(exercise.reps):
                return str(exercise.reps[week - 1])
            else:
                return str(exercise.reps[-1]) if exercise.reps else ""
        elif isinstance(exercise.reps, str):
            # Parse comma-separated values
            values = [v.strip() for v in exercise.reps.split(",")]
            if week <= len(values):
                return values[week - 1]
            else:
                return values[-1] if values else exercise.reps
        else:
            return str(exercise.reps)
    
    # === Formatting Methods ===
    
    def _format_weight(self, weight: Optional[Union[str, float, List[float]]], config: TableConfig) -> str:
        """Format weight value"""
        if not weight:
            return ""
        
        if isinstance(weight, list):
            if config.show_weekly and config.current_week <= len(weight):
                weight = weight[config.current_week - 1]
            else:
                weight = weight[-1] if weight else ""
        
        if isinstance(weight, (int, float)):
            return f"{weight}kg" if weight > 0 else ""
        
        return str(weight)
    
    def _format_rest(self, rest: Optional[Union[str, int]]) -> str:
        """Format rest value"""
        if not rest:
            return ""
        
        if isinstance(rest, int):
            return f"{rest}s" if rest > 0 else ""
        
        return str(rest)
    
    def _format_duration(self, duration: Optional[Union[str, int]]) -> str:
        """Format duration value"""
        if not duration:
            return ""
        
        if isinstance(duration, int):
            if duration < 60:
                return f"{duration}s"
            else:
                minutes = duration // 60
                seconds = duration % 60
                return f"{minutes}m{seconds}s" if seconds > 0 else f"{minutes}m"
        
        return str(duration)
    
    def _format_intensity(self, intensity: Optional[Union[str, float]]) -> str:
        """Format intensity value"""
        if not intensity:
            return ""
        
        if isinstance(intensity, (int, float)):
            return f"{intensity}%" if intensity > 0 else ""
        
        return str(intensity)
    
    def _format_rpe(self, rpe: Optional[Union[str, int]]) -> str:
        """Format RPE value"""
        if not rpe:
            return ""
        
        return str(rpe)
    
    # === Style Methods ===
    
    def _apply_table_styles(self, table: Table, config: TableConfig):
        """Apply table styles"""
        styles = [
            # Header styles
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            
            # Body styles
            ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]
        
        # Add alternating row colors
        if config.alternate_row_colors:
            for i in range(1, len(table._arg[1])):  # Skip header
                if i % 2 == 0:
                    styles.append(('BACKGROUND', (0, i), (-1, i), colors.whitesmoke))
        
        # Apply custom styles
        if config.custom_styles:
            styles.extend(config.custom_styles)
        
        table.setStyle(TableStyle(styles))
    
    def _apply_weekly_table_styles(self, table: Table, config: TableConfig):
        """Apply weekly table styles"""
        styles = [
            # Header styles
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),  # Exercise name left-aligned
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),  # Weeks center-aligned
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            
            # Body styles
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]
        
        # Highlight current week
        if 1 <= config.current_week <= config.total_weeks:
            current_week_col = config.current_week
            styles.extend([
                ('BACKGROUND', (current_week_col, 1), (current_week_col, -1), colors.lightblue),
                ('FONTNAME', (current_week_col, 1), (current_week_col, -1), 'Helvetica-Bold'),
            ])
        
        table.setStyle(TableStyle(styles))
    
    def _apply_superset_table_styles(self, table: Table, config: TableConfig):
        """Apply superset table styles"""
        styles = [
            # Header styles
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightcoral),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            
            # Body styles
            ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BACKGROUND', (0, 1), (-1, -1), colors.mistyrose),
        ]
        
        table.setStyle(TableStyle(styles))
    
    # === Utility Methods ===
    
    def _convert_exercise_data(self, exercises: List[Dict[str, Any]]) -> List[ExerciseData]:
        """Convert exercise dictionaries to ExerciseData objects"""
        exercise_data = []
        
        for i, ex in enumerate(exercises):
            exercise = ExerciseData(
                id=ex.get("id", i),
                name=ex.get("nombre", ""),
                sets=ex.get("series", 0),
                reps=ex.get("repeticiones", ""),
                weight=ex.get("peso_kg"),
                rest=ex.get("descanso"),
                duration=ex.get("duracion"),
                intensity=ex.get("intensidad"),
                tempo=ex.get("tempo"),
                rpe=ex.get("rir"),
                notes=ex.get("notas"),
                muscle_group=ex.get("grupo_muscular"),
                equipment=ex.get("equipamiento"),
                variation_id=ex.get("variacion_id"),
                supergroup_id=ex.get("superserie_grupo"),
                order=ex.get("orden", i),
                day_number=ex.get("dia_semana", 1)
            )
            exercise_data.append(exercise)
        
        # Sort by order
        exercise_data.sort(key=lambda x: x.order)
        return exercise_data
    
    def _get_table_headers(self, config: TableConfig) -> List[str]:
        """Get table headers based on configuration"""
        headers = []
        
        for column in config.columns:
            header = self.column_configs[column]["header"]
            headers.append(header)
        
        return headers
    
    def _get_column_widths(self, config: TableConfig) -> List[float]:
        """Get column widths based on configuration"""
        widths = []
        
        for column in config.columns:
            width = self.column_configs[column]["width"]
            widths.append(width)
        
        return widths
    
    def _create_default_styles(self) -> Dict[str, ParagraphStyle]:
        """Create default paragraph styles"""
        return {
            "day_header": ParagraphStyle(
                "DayHeader",
                fontSize=14,
                spaceAfter=6,
                textColor=colors.black,
                fontName="Helvetica-Bold"
            ),
            "superset_header": ParagraphStyle(
                "SupersetHeader",
                fontSize=12,
                spaceAfter=6,
                textColor=colors.darkred,
                fontName="Helvetica-Bold"
            )
        }
    
    def _create_column_configs(self) -> Dict[ExerciseColumn, Dict[str, Any]]:
        """Create column configurations"""
        return {
            ExerciseColumn.EXERCISE_NAME: {"header": "Ejercicio", "width": 3*inch},
            ExerciseColumn.SETS: {"header": "Series", "width": 1*inch},
            ExerciseColumn.REPS: {"header": "Repeticiones", "width": 1.5*inch},
            ExerciseColumn.WEIGHT: {"header": "Peso", "width": 1*inch},
            ExerciseColumn.REST: {"header": "Descanso", "width": 1*inch},
            ExerciseColumn.DURATION: {"header": "Duración", "width": 1*inch},
            ExerciseColumn.INTENSITY: {"header": "Intensidad", "width": 1*inch},
            ExerciseColumn.TEMPO: {"header": "Tempo", "width": 1*inch},
            ExerciseColumn.RPE: {"header": "RPE", "width": 0.8*inch},
            ExerciseColumn.NOTES: {"header": "Notas", "width": 2*inch},
            ExerciseColumn.MUSCLE_GROUP: {"header": "Grupo Muscular", "width": 1.5*inch},
            ExerciseColumn.EQUIPMENT: {"header": "Equipamiento", "width": 1.5*inch}
        }


# Export main classes
__all__ = [
    "ExerciseTableBuilder",
    "TableConfig",
    "ExerciseData",
    "TableFormat",
    "ExerciseColumn"
]
