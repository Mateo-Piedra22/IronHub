"""
Pytest Configuration
Configuration file for pytest test runner
"""

import pytest
import sys
from pathlib import Path

project_path = Path(__file__).parent
src_path = project_path / "src"
sys.path.insert(0, str(project_path))
sys.path.insert(0, str(src_path))

# Test configuration
pytest_plugins = []

# Test markers
def pytest_configure(config):
    config.addinivalue_line(
        "markers", "unit: Unit tests"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests"
    )
    config.addinivalue_line(
        "markers", "api: API tests"
    )
    config.addinivalue_line(
        "markers", "slow: Slow running tests"
    )

# Test collection
collect_ignore_glob = [
    "*/migrations/*",
    "*/venv/*",
    "*/env/*",
    "*/__pycache__/*"
]

# Test output
def pytest_html_report_title(report):
    """Custom HTML report title"""
    report.title = "IronHub Template System Test Report"

# Fixtures
@pytest.fixture(scope="session")
def test_config():
    """Test configuration fixture"""
    return {
        "database_url": "sqlite:///:memory:",
        "test_timeout": 30,
        "mock_externals": True
    }

@pytest.fixture
def mock_database():
    """Mock database fixture"""
    from unittest.mock import Mock
    from sqlalchemy.orm import Session
    
    mock_session = Mock(spec=Session)
    mock_session.add = Mock()
    mock_session.commit = Mock()
    mock_session.rollback = Mock()
    mock_session.flush = Mock()
    mock_session.refresh = Mock()
    mock_session.query = Mock()
    
    return mock_session

@pytest.fixture
def sample_template_config():
    """Sample template configuration for testing"""
    return {
        "version": "1.0.0",
        "metadata": {
            "name": "Test Template",
            "description": "A test template for unit testing",
            "author": "Test Suite",
            "tags": ["test", "unit"]
        },
        "layout": {
            "page_size": "A4",
            "orientation": "portrait",
            "margins": {"top": 20, "right": 20, "bottom": 20, "left": 20}
        },
        "sections": [
            {
                "id": "header",
                "type": "header",
                "content": {
                    "title": "{{gym_name}}",
                    "subtitle": "Test Routine"
                }
            },
            {
                "id": "exercises",
                "type": "exercise_table",
                "content": {
                    "title": "Exercises",
                    "exercises": [
                        {
                            "name": "Push-ups",
                            "sets": 3,
                            "reps": "10",
                            "rest": "60s"
                        }
                    ]
                }
            }
        ],
        "variables": {
            "gym_name": {"type": "string", "default": "Test Gym"},
            "client_name": {"type": "string", "default": "Test Client"}
        },
        "styling": {
            "primary_color": "#000000",
            "font_family": "Arial",
            "font_size": 12
        }
    }

@pytest.fixture
def sample_excel_data():
    """Sample Excel data for testing"""
    return [
        ["Ejercicio", "Series", "Repeticiones", "Descanso", "Notas"],
        ["Push-ups", "3", "10", "60s", "Keep back straight"],
        ["Squats", "4", "12", "90s", "Full depth"],
        ["Pull-ups", "3", "8", "60s", "Full range"]
    ]

# Test utilities
def create_mock_template():
    """Create a mock template object"""
    from unittest.mock import Mock
    from datetime import datetime
    
    template = Mock()
    template.id = 1
    template.nombre = "Test Template"
    template.descripcion = "Test Description"
    template.configuracion = {}
    template.categoria = "test"
    template.dias_semana = 3
    template.activa = True
    template.publica = False
    template.creada_por = 1
    template.fecha_creacion = datetime.now()
    template.fecha_actualizacion = datetime.now()
    template.version_actual = "1.0.0"
    template.tags = ["test"]
    template.uso_count = 0
    template.rating_promedio = 0.0
    template.rating_count = 0
    
    return template

def create_mock_rutina():
    """Create a mock routine object"""
    from unittest.mock import Mock
    
    class MockEjercicio:
        def __init__(self):
            self.ejercicio = Mock()
            self.ejercicio.nombre = "Test Exercise"
            self.series = 3
            self.repeticiones = "10"
            self.descanso = "60s"
            self.notas = "Test notes"
    
    class MockDia:
        def __init__(self):
            self.ejercicios = [MockEjercicio()]
    
    class MockRutina:
        def __init__(self):
            self.nombre = "Test Routine"
            self.usuario_nombre = "Test User"
            self.dias = [MockDia()]
    
    return MockRutina()

# Environment setup
@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Setup test environment"""
    # Set environment variables for testing
    import os
    
    os.environ["TESTING"] = "true"
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    os.environ["LOG_LEVEL"] = "DEBUG"
    
    yield
    
    # Cleanup
    os.environ.pop("TESTING", None)
    os.environ.pop("DATABASE_URL", None)
    os.environ.pop("LOG_LEVEL", None)
