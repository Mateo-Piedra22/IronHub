"""
Seed script para crear plantillas base personalizables
para el nuevo sistema de templates dinámicos
"""

import logging
from sqlalchemy.orm import Session

from ..models.orm_models import PlantillaRutina, PlantillaRutinaVersion

logger = logging.getLogger(__name__)

# Plantillas base personalizables
BASE_TEMPLATES = [
    {
        "nombre": "Full Body Beginner",
        "descripcion": "Rutina full body ideal para principiantes, enfocada en movimientos compuestos básicos",
        "categoria": "fuerza",
        "dias_semana": 3,
        "tags": ["principiante", "full body", "compuestos", "básico"],
        "configuracion": {
            "layout": {
                "type": "full_body",
                "days_per_week": 3,
                "session_duration": 45,
                "rest_days": [2, 4, 6, 7]
            },
            "exercises": {
                "day_1": {
                    "name": "Día 1 - Empuje",
                    "warmup": {"duration": 5, "type": "cardio_ligero"},
                    "main_exercises": [
                        {
                            "name": "Sentadilla con peso corporal",
                            "sets": 3,
                            "reps": "8-12",
                            "rest": 90,
                            "notes": "Mantener espalda recta",
                            "customizable": True
                        },
                        {
                            "name": "Flexiones en pared o rodillas",
                            "sets": 3,
                            "reps": "8-15",
                            "rest": 60,
                            "notes": "Adaptar dificultad según nivel",
                            "customizable": True
                        },
                        {
                            "name": "Remo con mancuernas",
                            "sets": 3,
                            "reps": "10-12",
                            "rest": 60,
                            "notes": "Mantener core activo",
                            "customizable": True
                        },
                        {
                            "name": "Press militar sentado",
                            "sets": 3,
                            "reps": "8-12",
                            "rest": 60,
                            "notes": "Controlar movimiento",
                            "customizable": True
                        },
                        {
                            "name": "Curl de bíceps",
                            "sets": 2,
                            "reps": "10-15",
                            "rest": 45,
                            "notes": "Movimiento controlado",
                            "customizable": True
                        }
                    ],
                    "cooldown": {"duration": 5, "type": "estiramientos"}
                },
                "day_2": {
                    "name": "Día 2 - Pierna y Core",
                    "warmup": {"duration": 5, "type": "movilidad_articular"},
                    "main_exercises": [
                        {
                            "name": "Zancadas",
                            "sets": 3,
                            "reps": "10-12 por pierna",
                            "rest": 90,
                            "notes": "Mantener equilibrio",
                            "customizable": True
                        },
                        {
                            "name": "Peso muerto rumano con mancuernas",
                            "sets": 3,
                            "reps": "10-12",
                            "rest": 90,
                            "notes": "Piernas semiflexionadas",
                            "customizable": True
                        },
                        {
                            "name": "Elevación talones",
                            "sets": 3,
                            "reps": "15-20",
                            "rest": 45,
                            "notes": "Movimiento completo",
                            "customizable": True
                        },
                        {
                            "name": "Plancha",
                            "sets": 3,
                            "reps": "30-60 segundos",
                            "rest": 60,
                            "notes": "Mantener posición",
                            "customizable": True
                        },
                        {
                            "name": "Elevaciones de pierna",
                            "sets": 3,
                            "reps": "15-20",
                            "rest": 45,
                            "notes": "Controlar movimiento",
                            "customizable": True
                        }
                    ],
                    "cooldown": {"duration": 5, "type": "estiramientos"}
                },
                "day_3": {
                    "name": "Día 3 - Tirón y Brazos",
                    "warmup": {"duration": 5, "type": "cardio_ligero"},
                    "main_exercises": [
                        {
                            "name": "Dominadas asistidas o jalón al pecho",
                            "sets": 3,
                            "reps": "8-12",
                            "rest": 90,
                            "notes": "Foco en espalda",
                            "customizable": True
                        },
                        {
                            "name": "Press de banca plano",
                            "sets": 3,
                            "reps": "8-12",
                            "rest": 90,
                            "notes": "Controlar descenso",
                            "customizable": True
                        },
                        {
                            "name": "Elevaciones laterales",
                            "sets": 3,
                            "reps": "12-15",
                            "rest": 60,
                            "notes": "Movimiento controlado",
                            "customizable": True
                        },
                        {
                            "name": "Tríceps en polea",
                            "sets": 3,
                            "reps": "10-12",
                            "rest": 60,
                            "notes": "Codos pegados al cuerpo",
                            "customizable": True
                        },
                        {
                            "name": "Curl martillo",
                            "sets": 3,
                            "reps": "10-12",
                            "rest": 45,
                            "notes": "Sin balanceo",
                            "customizable": True
                        }
                    ],
                    "cooldown": {"duration": 5, "type": "estiramientos"}
                }
            },
            "progression": {
                "type": "linear",
                "duration_weeks": 8,
                "progression_method": "double_progression",
                "deload_frequency": 4
            },
            "customization_options": {
                "exercise_substitution": True,
                "rep_range_adjustment": True,
                "rest_time_modification": True,
                "exercise_order_change": False,
                "add_accessory_work": True
            }
        }
    },
    {
        "nombre": "Hipertrofia Split 4 Días",
        "descripcion": "Rutina de hipertrofia clásica 4 días con división por grupos musculares",
        "categoria": "hipertrofia",
        "dias_semana": 4,
        "tags": ["intermedio", "hipertrofia", "split", "volumen"],
        "configuracion": {
            "layout": {
                "type": "upper_lower_split",
                "days_per_week": 4,
                "session_duration": 60,
                "rest_days": [3, 7],
                "split_pattern": ["Upper A", "Lower A", "Upper B", "Lower B"]
            },
            "exercises": {
                "day_1": {
                    "name": "Upper A - Empuje Pesado",
                    "warmup": {"duration": 10, "type": "activacion + cardio"},
                    "main_exercises": [
                        {
                            "name": "Press de banca plano con barra",
                            "sets": 4,
                            "reps": "6-8",
                            "rest": 120,
                            "notes": "Foco en fuerza progresiva",
                            "customizable": True
                        },
                        {
                            "name": "Press inclinado con mancuernas",
                            "sets": 3,
                            "reps": "8-12",
                            "rest": 90,
                            "notes": "Controlar movimiento",
                            "customizable": True
                        },
                        {
                            "name": "Fondos en paralelas",
                            "sets": 3,
                            "reps": "8-12",
                            "rest": 90,
                            "notes": "Variar inclinación",
                            "customizable": True
                        },
                        {
                            "name": "Press militar con barra",
                            "sets": 4,
                            "reps": "6-10",
                            "rest": 90,
                            "notes": "Piernas semiflexionadas",
                            "customizable": True
                        },
                        {
                            "name": "Elevaciones laterales con mancuernas",
                            "sets": 3,
                            "reps": "12-15",
                            "rest": 60,
                            "notes": "Controlar excéntrico",
                            "customizable": True
                        },
                        {
                            "name": "Tríceps en banco",
                            "sets": 3,
                            "reps": "8-12",
                            "rest": 60,
                            "notes": "Codos apuntando hacia arriba",
                            "customizable": True
                        }
                    ],
                    "accessory_work": [
                        {
                            "name": "Curl de bíceps con barra",
                            "sets": 3,
                            "reps": "10-12",
                            "rest": 60,
                            "optional": True
                        }
                    ],
                    "cooldown": {"duration": 5, "type": "estiramientos"}
                },
                "day_2": {
                    "name": "Lower A - Pierna Pesada",
                    "warmup": {"duration": 10, "type": "movilidad + activacion"},
                    "main_exercises": [
                        {
                            "name": "Sentadilla con barra",
                            "sets": 4,
                            "reps": "6-8",
                            "rest": 120,
                            "notes": "Profundidad completa",
                            "customizable": True
                        },
                        {
                            "name": "Peso muerto convencional",
                            "sets": 3,
                            "reps": "5-6",
                            "rest": 180,
                            "notes": "Técnica perfecta",
                            "customizable": True
                        },
                        {
                            "name": "Prensa de piernas",
                            "sets": 3,
                            "reps": "10-12",
                            "rest": 90,
                            "notes": "Rango completo",
                            "customizable": True
                        },
                        {
                            "name": "Extensiones de cuádriceps",
                            "sets": 3,
                            "reps": "12-15",
                            "rest": 60,
                            "notes": "Pico de contracción",
                            "customizable": True
                        },
                        {
                            "name": "Curl femoral acostado",
                            "sets": 3,
                            "reps": "10-12",
                            "rest": 60,
                            "notes": "Controlar movimiento",
                            "customizable": True
                        },
                        {
                            "name": "Elevación talones sentado",
                            "sets": 4,
                            "reps": "15-20",
                            "rest": 45,
                            "notes": "Sin descanso entre series",
                            "customizable": True
                        }
                    ],
                    "cooldown": {"duration": 5, "type": "estiramientos"}
                },
                "day_3": {
                    "name": "Upper B - Tirón Pesado",
                    "warmup": {"duration": 10, "type": "activacion + cardio"},
                    "main_exercises": [
                        {
                            "name": "Dominadas",
                            "sets": 4,
                            "reps": "6-10",
                            "rest": 120,
                            "notes": "Rango completo",
                            "customizable": True
                        },
                        {
                            "name": "Remo con barra",
                            "sets": 4,
                            "reps": "6-8",
                            "rest": 90,
                            "notes": "Mantener espalda recta",
                            "customizable": True
                        },
                        {
                            "name": "Remo sentado en polea",
                            "sets": 3,
                            "reps": "8-12",
                            "rest": 90,
                            "notes": "Foco en dorsal ancho",
                            "customizable": True
                        },
                        {
                            "name": "Face pulls",
                            "sets": 3,
                            "reps": "15-20",
                            "rest": 60,
                            "notes": "Rotación externa",
                            "customizable": True
                        },
                        {
                            "name": "Curl de bíceps con mancuernas",
                            "sets": 3,
                            "reps": "10-12",
                            "rest": 60,
                            "notes": "Sin balanceo",
                            "customizable": True
                        },
                        {
                            "name": "Curl concentrado",
                            "sets": 3,
                            "reps": "10-12",
                            "rest": 60,
                            "notes": "Contracción máxima",
                            "customizable": True
                        }
                    ],
                    "cooldown": {"duration": 5, "type": "estiramientos"}
                },
                "day_4": {
                    "name": "Lower B - Pierna Volumen",
                    "warmup": {"duration": 10, "type": "movilidad + activacion"},
                    "main_exercises": [
                        {
                            "name": "Zancadas con mancuernas",
                            "sets": 3,
                            "reps": "10-12 por pierna",
                            "rest": 90,
                            "notes": "Zancada larga",
                            "customizable": True
                        },
                        {
                            "name": "Sentadilla búlgara",
                            "sets": 3,
                            "reps": "8-10 por pierna",
                            "rest": 90,
                            "notes": "Torso erguido",
                            "customizable": True
                        },
                        {
                            "name": "Peso muerto rumano",
                            "sets": 3,
                            "reps": "10-12",
                            "rest": 90,
                            "notes": "Estirar femorales",
                            "customizable": True
                        },
                        {
                            "name": "Sentadilla sumo",
                            "sets": 3,
                            "reps": "12-15",
                            "rest": 60,
                            "notes": "Punta de pies hacia afuera",
                            "customizable": True
                        },
                        {
                            "name": "Abducción de cadera",
                            "sets": 3,
                            "reps": "15-20",
                            "rest": 60,
                            "notes": "Glúteo medio",
                            "customizable": True
                        },
                        {
                            "name": "Elevación talones de pie",
                            "sets": 4,
                            "reps": "20-25",
                            "rest": 45,
                            "notes": "Sin descanso",
                            "customizable": True
                        }
                    ],
                    "core_finisher": [
                        {
                            "name": "Plancha lateral",
                            "sets": 3,
                            "reps": "30 segundos por lado",
                            "rest": 30
                        },
                        {
                            "name": "Dead bug",
                            "sets": 3,
                            "reps": "10 por lado",
                            "rest": 45
                        }
                    ],
                    "cooldown": {"duration": 5, "type": "estiramientos"}
                }
            },
            "progression": {
                "type": "double_progression",
                "duration_weeks": 12,
                "volume_increase": "add_set_or_reps",
                "intensity_increase": "add_weight",
                "deload_frequency": 6
            },
            "customization_options": {
                "exercise_substitution": True,
                "rep_range_adjustment": True,
                "rest_time_modification": True,
                "exercise_order_change": True,
                "add_accessory_work": True,
                "intensity_techniques": ["drop_sets", "rest_pause", "partials"]
            }
        }
    },
    {
        "nombre": "Functional Fitness 3 Días",
        "descripcion": "Rutina de entrenamiento funcional con movimientos variados y trabajo de condición física",
        "categoria": "funcional",
        "dias_semana": 3,
        "tags": ["funcional", "cardio", "movilidad", "balance"],
        "configuracion": {
            "layout": {
                "type": "full_body_functional",
                "days_per_week": 3,
                "session_duration": 50,
                "rest_days": [2, 4, 5, 6, 7],
                "focus_rotation": ["strength", "conditioning", "mobility"]
            },
            "exercises": {
                "day_1": {
                    "name": "Día 1 - Fuerza Funcional",
                    "warmup": {"duration": 10, "type": "dinámico + activacion"},
                    "main_circuit": {
                        "rounds": 4,
                        "rest_between_rounds": 120,
                        "exercises": [
                            {
                                "name": "Kettlebell swings",
                                "sets": 1,
                                "reps": "15-20",
                                "rest": 30,
                                "notes": "Cadera explosiva",
                                "customizable": True
                            },
                            {
                                "name": "Thrusters con mancuernas",
                                "sets": 1,
                                "reps": "10-12",
                                "rest": 30,
                                "notes": "Movimiento fluido",
                                "customizable": True
                            },
                            {
                                "name": "Burpees",
                                "sets": 1,
                                "reps": "8-10",
                                "rest": 30,
                                "notes": "Saltar al final",
                                "customizable": True
                            },
                            {
                                "name": "Rowing con kettlebell",
                                "sets": 1,
                                "reps": "12-15",
                                "rest": 30,
                                "notes": "Espalda recta",
                                "customizable": True
                            },
                            {
                                "name": "Mountain climbers",
                                "sets": 1,
                                "reps": "20-30",
                                "rest": 30,
                                "notes": "Ritmo constante",
                                "customizable": True
                            }
                        ]
                    },
                    "strength_finisher": [
                        {
                            "name": "Turkish get-up (por lado)",
                            "sets": 2,
                            "reps": "1 por lado",
                            "rest": 60,
                            "notes": "Técnica perfecta",
                            "customizable": True
                        }
                    ],
                    "cooldown": {"duration": 10, "type": "movilidad + estiramientos"}
                },
                "day_2": {
                    "name": "Día 2 - Acondicionamiento",
                    "warmup": {"duration": 10, "type": "cardio progresivo"},
                    "conditioning_blocks": [
                        {
                            "name": "Bloque 1 - Potencia",
                            "duration": 8,
                            "exercises": [
                                {
                                    "name": "Box jumps",
                                    "work": 30,
                                    "rest": 30,
                                    "rounds": 4,
                                    "customizable": True
                                },
                                {
                                    "name": "Slam balls",
                                    "work": 30,
                                    "rest": 30,
                                    "rounds": 4,
                                    "customizable": True
                                }
                            ]
                        },
                        {
                            "name": "Bloque 2 - Resistencia",
                            "duration": 10,
                            "exercises": [
                                {
                                    "name": "Battle ropes",
                                    "work": 45,
                                    "rest": 15,
                                    "rounds": 3,
                                    "customizable": True
                                },
                                {
                                    "name": "Sled push/pull",
                                    "work": 60,
                                    "rest": 60,
                                    "rounds": 3,
                                    "customizable": True
                                }
                            ]
                        }
                    ],
                    "core_circuit": {
                        "rounds": 3,
                        "exercises": [
                            {
                                "name": "Plancha con arrastre",
                                "work": 30,
                                "rest": 15
                            },
                            {
                                "name": "Russian twists",
                                "work": 30,
                                "rest": 15
                            },
                            {
                                "name": "Leg raises",
                                "work": 30,
                                "rest": 15
                            }
                        ]
                    },
                    "cooldown": {"duration": 10, "type": "recuperación"}
                },
                "day_3": {
                    "name": "Día 3 - Movilidad y Estabilidad",
                    "warmup": {"duration": 10, "type": "movilidad articular"},
                    "movement_flows": [
                        {
                            "name": "Flow 1 - Ground work",
                            "duration": 10,
                            "exercises": [
                                {
                                    "name": "Animal crawls variations",
                                    "duration": 3,
                                    "notes": "Oso, cangrejo, lagartija",
                                    "customizable": True
                                },
                                {
                                    "name": "Transiciones suelo-pie",
                                    "duration": 3,
                                    "notes": "Get-ups variados",
                                    "customizable": True
                                },
                                {
                                    "name": "Rolling y balance",
                                    "duration": 4,
                                    "notes": "Forward/backward rolls",
                                    "customizable": True
                                }
                            ]
                        },
                        {
                            "name": "Flow 2 - Stability work",
                            "duration": 10,
                            "exercises": [
                                {
                                    "name": "Single leg work",
                                    "sets": 3,
                                    "reps": "8-12 por pierna",
                                    "rest": 45,
                                    "customizable": True
                                },
                                {
                                    "name": "Core stability",
                                    "sets": 3,
                                    "reps": "30-60 segundos",
                                    "rest": 30,
                                    "customizable": True
                                },
                                {
                                    "name": "Balance exercises",
                                    "sets": 3,
                                    "reps": "30 segundos",
                                    "rest": 30,
                                    "customizable": True
                                }
                            ]
                        }
                    ],
                    "flexibility_work": {
                        "duration": 15,
                        "focus_areas": ["caderas", "columna", "hombros"],
                        "stretch_types": ["estáticos", "dinámicos", "PNF"]
                    },
                    "cooldown": {"duration": 5, "type": "relajación"}
                }
            },
            "progression": {
                "type": "non_linear",
                "duration_weeks": 8,
                "progression_markers": ["volume", "intensity", "complexity"],
                "adaptation_focus": "work_capacity"
            },
            "customization_options": {
                "exercise_substitution": True,
                "rep_range_adjustment": True,
                "rest_time_modification": True,
                "exercise_order_change": True,
                "add_accessory_work": True,
                "intensity_techniques": ["complexes", "chains", "partials"],
                "equipment_adaptation": True
            }
        }
    },
    {
        "nombre": "Cardio y Fuerza Híbrido",
        "descripcion": "Combinación perfecta de entrenamiento cardiovascular y de fuerza para overall fitness",
        "categoria": "híbrido",
        "dias_semana": 4,
        "tags": ["cardio", "fuerza", "híbrido", "condición física"],
        "configuracion": {
            "layout": {
                "type": "hybrid_split",
                "days_per_week": 4,
                "session_duration": 55,
                "rest_days": [3, 7],
                "split_pattern": ["Upper + Cardio", "Lower + Cardio", "Full Body", "HIIT"]
            },
            "exercises": {
                "day_1": {
                    "name": "Upper Body + Cardio",
                    "warmup": {"duration": 8, "type": "cardio ligero + movilidad"},
                    "strength_part": {
                        "supersets": [
                            {
                                "exercises": [
                                    {
                                        "name": "Press banca plano",
                                        "sets": 3,
                                        "reps": "8-12",
                                        "customizable": True
                                    },
                                    {
                                        "name": "Remo con mancuernas",
                                        "sets": 3,
                                        "reps": "8-12",
                                        "customizable": True
                                    }
                                ],
                                "rest_between_exercises": 60,
                                "rest_between_sets": 90
                            },
                            {
                                "exercises": [
                                    {
                                        "name": "Press militar",
                                        "sets": 3,
                                        "reps": "10-12",
                                        "customizable": True
                                    },
                                    {
                                        "name": "Dominadas asistidas",
                                        "sets": 3,
                                        "reps": "máximo",
                                        "customizable": True
                                    }
                                ],
                                "rest_between_exercises": 60,
                                "rest_between_sets": 90
                            }
                        ]
                    },
                    "cardio_finisher": {
                        "type": "interval_training",
                        "duration": 15,
                        "intervals": [
                            {"work": 30, "rest": 30, "intensity": "moderado"},
                            {"work": 45, "rest": 15, "intensity": "alto"}
                        ],
                        "rounds": 4
                    },
                    "cooldown": {"duration": 5, "type": "estiramientos"}
                },
                "day_2": {
                    "name": "Lower Body + Cardio",
                    "warmup": {"duration": 8, "type": "movilidad + activación"},
                    "strength_part": {
                        "main_lifts": [
                            {
                                "name": "Sentadilla con barra",
                                "sets": 4,
                                "reps": "6-8",
                                "rest": 120,
                                "customizable": True
                            },
                            {
                                "name": "Peso muerto rumano",
                                "sets": 3,
                                "reps": "8-10",
                                "rest": 90,
                                "customizable": True
                            }
                        ],
                        "accessory_circuit": {
                            "rounds": 3,
                            "exercises": [
                                {
                                    "name": "Zancadas laterales",
                                    "reps": "10 por lado",
                                    "customizable": True
                                },
                                {
                                    "name": "Elevación talones",
                                    "reps": "20",
                                    "customizable": True
                                },
                                {
                                    "name": "Plancha",
                                    "reps": "45 segundos",
                                    "customizable": True
                                }
                            ],
                            "rest": 60
                        }
                    },
                    "cardio_finisher": {
                        "type": "steady_state",
                        "duration": 20,
                        "intensity": "moderado",
                        "equipment": "cinta elíptica o bicicleta"
                    },
                    "cooldown": {"duration": 5, "type": "estiramientos"}
                },
                "day_3": {
                    "name": "Full Body Power",
                    "warmup": {"duration": 10, "type": "activación completa"},
                    "power_complexes": [
                        {
                            "name": "Complex 1 - Push/Pull",
                            "rounds": 4,
                            "exercises": [
                                {
                                    "name": "Power clean",
                                    "reps": 3,
                                    "customizable": True
                                },
                                {
                                    "name": "Front squat",
                                    "reps": 5,
                                    "customizable": True
                                },
                                {
                                    "name": "Push press",
                                    "reps": 5,
                                    "customizable": True
                                },
                                {
                                    "name": "Back squat",
                                    "reps": 5,
                                    "customizable": True
                                }
                            ],
                            "rest": 120
                        }
                    ],
                    "conditioning_circuit": {
                        "duration": 15,
                        "exercises": [
                            {
                                "name": "Burpee box jumps",
                                "work": 45,
                                "rest": 15,
                                "customizable": True
                            },
                            {
                                "name": "Kettlebell swings",
                                "work": 45,
                                "rest": 15,
                                "customizable": True
                            },
                            {
                                "name": "Rowing ergómetro",
                                "work": 45,
                                "rest": 15,
                                "customizable": True
                            }
                        ],
                        "rounds": 3
                    },
                    "cooldown": {"duration": 10, "type": "recuperación profunda"}
                },
                "day_4": {
                    "name": "HIIT + Core",
                    "warmup": {"duration": 10, "type": "cardio progresivo"},
                    "hiit_blocks": [
                        {
                            "name": "Bloque 1 - Alta Intensidad",
                            "duration": 12,
                            "intervals": [
                                {"work": 40, "rest": 20, "intensity": "máximo"},
                                {"work": 30, "rest": 30, "intensity": "máximo"},
                                {"work": 20, "rest": 40, "intensity": "máximo"}
                            ],
                            "exercises": [
                                "Sprints en bicicleta",
                                "Battle ropes",
                                "Box jumps"
                            ],
                            "rounds": 2
                        },
                        {
                            "name": "Bloque 2 - Resistencia",
                            "duration": 10,
                            "intervals": [
                                {"work": 60, "rest": 30, "intensity": "alto"}
                            ],
                            "exercises": [
                                "Slam balls",
                                "Sled push",
                                "Kettlebell snatches"
                            ],
                            "rounds": 2
                        }
                    ],
                    "core_strength": {
                        "rounds": 3,
                        "exercises": [
                            {
                                "name": "Ab wheel rollouts",
                                "reps": "8-12",
                                "customizable": True
                            },
                            {
                                "name": "Hanging leg raises",
                                "reps": "10-15",
                                "customizable": True
                            },
                            {
                                "name": "Russian twists con peso",
                                "reps": "20-30",
                                "customizable": True
                            }
                        ],
                        "rest": 60
                    },
                    "cooldown": {"duration": 10, "type": "estiramientos + respiración"}
                }
            },
            "progression": {
                "type": "concurrent",
                "duration_weeks": 10,
                "strength_progression": "linear",
                "cardio_progression": "interval_expansion",
                "deload_strategy": "volume_reduction"
            },
            "customization_options": {
                "exercise_substitution": True,
                "rep_range_adjustment": True,
                "rest_time_modification": True,
                "exercise_order_change": True,
                "add_accessory_work": True,
                "cardio_modification": True,
                "intensity_techniques": ["clusters", "myo-reps", "density"]
            }
        }
    },
    {
        "nombre": "Rehab y Movilidad",
        "descripcion": "Programa de rehabilitación y movilidad para recuperación y prevención de lesiones",
        "categoria": "rehab",
        "dias_semana": 3,
        "tags": ["rehabilitación", "movilidad", "recuperación", "prevención"],
        "configuracion": {
            "layout": {
                "type": "rehab_split",
                "days_per_week": 3,
                "session_duration": 45,
                "rest_days": [2, 4, 5, 6, 7],
                "focus_rotation": ["movilidad", "estabilidad", "fuerza_controlada"]
            },
            "exercises": {
                "day_1": {
                    "name": "Día 1 - Movilidad Articular",
                    "warmup": {"duration": 5, "type": "respiración consciente"},
                    "mobility_flows": [
                        {
                            "name": "Flow columna vertebral",
                            "duration": 15,
                            "exercises": [
                                {
                                    "name": "Cat-cow variations",
                                    "reps": "10-12",
                                    "notes": "Foco en cada vértebra",
                                    "customizable": True
                                },
                                {
                                    "name": "Thoracic rotations",
                                    "reps": "8-10 por lado",
                                    "notes": "Cadera estable",
                                    "customizable": True
                                },
                                {
                                    "name": "Spinal waves",
                                    "reps": "6-8",
                                    "notes": "Movimiento fluido",
                                    "customizable": True
                                }
                            ]
                        },
                        {
                            "name": "Flow cadera y cadera",
                            "duration": 15,
                            "exercises": [
                                {
                                    "name": "Hip circles",
                                    "reps": "10 por dirección",
                                    "notes": "Rango completo",
                                    "customizable": True
                                },
                                {
                                    "name": "90/90 stretches",
                                    "duration": "60 segundos por lado",
                                    "notes": "Relajar cadera",
                                    "customizable": True
                                },
                                {
                                    "name": "Frog stretch progressions",
                                    "duration": "90 segundos",
                                    "notes": "Respiración profunda",
                                    "customizable": True
                                }
                            ]
                        }
                    ],
                    "shoulder_health": {
                        "duration": 10,
                        "exercises": [
                            {
                                "name": "Shoulder CARs",
                                "reps": "3 por dirección",
                                "notes": "Control completo",
                                "customizable": True
                            },
                            {
                                "name": "Band pull-aparts",
                                "reps": "15-20",
                                "notes": "Retracción escapular",
                                "customizable": True
                            }
                        ]
                    },
                    "cooldown": {"duration": 5, "type": "relajación"}
                },
                "day_2": {
                    "name": "Día 2 - Estabilidad y Control",
                    "warmup": {"duration": 8, "type": "activación neuromuscular"},
                    "stability_work": [
                        {
                            "name": "Core stability progression",
                            "duration": 20,
                            "exercises": [
                                {
                                    "name": "Dead bug variations",
                                    "sets": 3,
                                    "reps": "10 por lado",
                                    "notes": "Respiración coordinada",
                                    "customizable": True
                                },
                                {
                                    "name": "Bird dog progressions",
                                    "sets": 3,
                                    "reps": "8 por lado",
                                    "notes": "Control pélvico",
                                    "customizable": True
                                },
                                {
                                    "name": "Side plank variations",
                                    "sets": 2,
                                    "reps": "30-45 segundos",
                                    "notes": "Alineación neutral",
                                    "customizable": True
                                }
                            ]
                        },
                        {
                            "name": "Balance y propiocepción",
                            "duration": 15,
                            "exercises": [
                                {
                                    "name": "Single leg stance progressions",
                                    "sets": 3,
                                    "reps": "30 segundos por pierna",
                                    "notes": "Mirada fija",
                                    "customizable": True
                                },
                                {
                                    "name": "Single leg RDL",
                                    "sets": 3,
                                    "reps": "8-10 por pierna",
                                    "notes": "Peso ligero",
                                    "customizable": True
                                }
                            ]
                        }
                    ],
                    "scapular_stability": {
                        "duration": 10,
                        "exercises": [
                            {
                                "name": "Wall slides",
                                "sets": 3,
                                "reps": "10-12",
                                "notes": "Espalda en pared",
                                "customizable": True
                            },
                            {
                                "name": "Scapular push-ups",
                                "sets": 2,
                                "reps": "8-10",
                                "notes": "Solo escápulas",
                                "customizable": True
                            }
                        ]
                    },
                    "cooldown": {"duration": 2, "type": "respiración"}
                },
                "day_3": {
                    "name": "Día 3 - Fuerza Controlada",
                    "warmup": {"duration": 10, "type": "movilidad específica"},
                    "controlled_strength": [
                        {
                            "name": "Patrones de movimiento básicos",
                            "duration": 25,
                            "exercises": [
                                {
                                    "name": "Goblet squats",
                                    "sets": 3,
                                    "reps": "12-15",
                                    "notes": "Torso erguido",
                                    "customizable": True
                                },
                                {
                                    "name": "Kettlebell deadlifts",
                                    "sets": 3,
                                    "reps": "10-12",
                                    "notes": "Cadera bisagra",
                                    "customizable": True
                                },
                                {
                                    "name": "Farmer's walks",
                                    "sets": 3,
                                    "reps": "30-40 metros",
                                    "notes": "Postura perfecta",
                                    "customizable": True
                                },
                                {
                                    "name": "Turkish get-ups (sin peso)",
                                    "sets": 2,
                                    "reps": "3 por lado",
                                    "notes": "Foco en técnica",
                                    "customizable": True
                                }
                            ]
                        }
                    ],
                    "integration_work": {
                        "duration": 10,
                        "exercises": [
                            {
                                "name": "Carries variados",
                                "sets": 3,
                                "reps": "20 metros",
                                "notes": "Farmer's, rack, overhead",
                                "customizable": True
                            },
                            {
                                "name": "Loaded carries",
                                "sets": 2,
                                "reps": "15 metros",
                                "notes": "Integración total",
                                "customizable": True
                            }
                        ]
                    },
                    "flexibility_integration": {
                        "duration": 5,
                        "focus": ["isquiotibiales", "caderas", "columna"],
                        "method": "estiramientos dinámicos"
                    }
                }
            },
            "progression": {
                "type": "ability_based",
                "duration_weeks": 6,
                "progression_criteria": ["range_of_motion", "control_quality", "endurance"],
                "assessment_frequency": 2
            },
            "customization_options": {
                "exercise_substitution": True,
                "intensity_adjustment": True,
                "duration_modification": True,
                "focus_area_emphasis": True,
                "equipment_adaptation": True,
                "difficulty_progression": True
            }
        }
    }
]

def create_base_templates(db: Session) -> int:
    """
    Crear plantillas base en la base de datos
    
    Returns:
        int: Número de plantillas creadas
    """
    created_count = 0
    
    for template_data in BASE_TEMPLATES:
        try:
            # Verificar si ya existe
            existing = db.query(PlantillaRutina).filter(
                PlantillaRutina.nombre == template_data["nombre"]
            ).first()
            
            if existing:
                logger.info(f"Template '{template_data['nombre']}' ya existe, omitiendo...")
                continue
            
            # Crear template
            template = PlantillaRutina(
                nombre=template_data["nombre"],
                descripcion=template_data["descripcion"],
                categoria=template_data["categoria"],
                dias_semana=template_data["dias_semana"],
                configuracion=template_data["configuracion"],
                tags=template_data["tags"],
                activa=True,
                publica=True,  # Templates base son públicos
                creada_por=None,  # System created
                uso_count=0,
                rating_promedio=0.0,
                rating_count=0
            )
            
            db.add(template)
            db.flush()  # Obtener ID
            
            # Crear versión inicial
            version = PlantillaRutinaVersion(
                plantilla_id=template.id,
                version="1.0.0",
                configuracion=template_data["configuracion"],
                cambios_descripcion="Versión inicial - Template base del sistema",
                creada_por=None,
                es_actual=True
            )
            
            db.add(version)
            db.commit()
            
            created_count += 1
            logger.info(f"Template '{template_data['nombre']}' creado exitosamente")
            
        except Exception as e:
            logger.error(f"Error creando template '{template_data['nombre']}': {e}")
            db.rollback()
    
    return created_count

def run_seed():
    """Ejecutar seed de plantillas base"""
    from ..database import SessionLocal
    
    db = SessionLocal()
    try:
        count = create_base_templates(db)
        logger.info(f"Seed completado: {count} plantillas base creadas")
        return count
    finally:
        db.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_seed()
