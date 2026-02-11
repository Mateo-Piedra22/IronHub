"""
Migration: Add Dynamic Template System Tables

This migration adds the database schema for the Dynamic Routine Engine,
including template management, versioning, gym assignments, and analytics.

Tables Added:
- plantillas_rutina: Main template definitions
- plantillas_rutina_versiones: Template versioning
- gimnasio_plantillas: Gym-specific template assignments
- plantilla_analitica: Template usage analytics
- plantilla_mercado: Template marketplace data
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "0016_add_dynamic_template_system"
down_revision = "0015_asistencias_tipo"
branch_labels = None
depends_on = None


def upgrade():
    """Add template system tables to the database"""
    
    # 1. Main template definitions table
    op.create_table(
        'plantillas_rutina',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nombre', sa.String(255), nullable=False),
        sa.Column('descripcion', sa.Text(), nullable=True),
        sa.Column('configuracion', postgresql.JSONB(), nullable=False),
        sa.Column('categoria', sa.String(100), nullable=True, server_default='general'),
        sa.Column('dias_semana', sa.Integer(), nullable=True),
        sa.Column('activa', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('publica', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('creada_por', sa.Integer(), nullable=True),
        sa.Column('fecha_creacion', sa.DateTime(), nullable=True, server_default=sa.text('current_timestamp')),
        sa.Column('fecha_actualizacion', sa.DateTime(), nullable=True, server_default=sa.text('current_timestamp')),
        sa.Column('version_actual', sa.String(50), nullable=True, server_default='1.0.0'),
        sa.Column('tags', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('preview_url', sa.String(500), nullable=True),
        sa.Column('uso_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('rating_promedio', sa.Numeric(3, 2), nullable=True),
        sa.Column('rating_count', sa.Integer(), nullable=True, server_default='0'),
        sa.ForeignKeyConstraint(['creada_por'], ['usuarios.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Indexes for plantillas_rutina
    op.create_index('idx_plantillas_rutina_activa', 'plantillas_rutina', ['activa'])
    op.create_index('idx_plantillas_rutina_categoria', 'plantillas_rutina', ['categoria'])
    op.create_index('idx_plantillas_rutina_publica', 'plantillas_rutina', ['publica'])
    op.create_index('idx_plantillas_rutina_creada_por', 'plantillas_rutina', ['creada_por'])
    op.create_index('idx_plantillas_rutina_fecha_creacion', 'plantillas_rutina', ['fecha_creacion'])
    
    # 2. Template versioning table
    op.create_table(
        'plantillas_rutina_versiones',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('plantilla_id', sa.Integer(), nullable=False),
        sa.Column('version', sa.String(50), nullable=False),
        sa.Column('configuracion', postgresql.JSONB(), nullable=False),
        sa.Column('cambios_descripcion', sa.Text(), nullable=True),
        sa.Column('creada_por', sa.Integer(), nullable=True),
        sa.Column('fecha_creacion', sa.DateTime(), nullable=True, server_default=sa.text('current_timestamp')),
        sa.Column('es_actual', sa.Boolean(), nullable=True, server_default='false'),
        sa.ForeignKeyConstraint(['plantilla_id'], ['plantillas_rutina.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['creada_por'], ['usuarios.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('plantilla_id', 'version', name='uq_plantilla_version')
    )
    
    # Indexes for plantillas_rutina_versiones
    op.create_index('idx_plantillas_versiones_plantilla_id', 'plantillas_rutina_versiones', ['plantilla_id'])
    op.create_index('idx_plantillas_versiones_es_actual', 'plantillas_rutina_versiones', ['es_actual'])
    op.create_index('idx_plantillas_versiones_fecha_creacion', 'plantillas_rutina_versiones', ['fecha_creacion'])
    
    # 3. Gym-specific template assignments
    op.create_table(
        'gimnasio_plantillas',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('gimnasio_id', sa.Integer(), nullable=False),
        sa.Column('plantilla_id', sa.Integer(), nullable=False),
        sa.Column('activa', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('prioridad', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('configuracion_personalizada', postgresql.JSONB(), nullable=True),
        sa.Column('asignada_por', sa.Integer(), nullable=True),
        sa.Column('fecha_asignacion', sa.DateTime(), nullable=True, server_default=sa.text('current_timestamp')),
        sa.Column('fecha_ultima_uso', sa.DateTime(), nullable=True),
        sa.Column('uso_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('notas', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['gimnasio_id'], ['gym_config.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['plantilla_id'], ['plantillas_rutina.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['asignada_por'], ['usuarios.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('gimnasio_id', 'plantilla_id', name='uq_gimnasio_plantilla')
    )
    
    # Indexes for gimnasio_plantillas
    op.create_index('idx_gimnasio_plantillas_gimnasio_id', 'gimnasio_plantillas', ['gimnasio_id'])
    op.create_index('idx_gimnasio_plantillas_plantilla_id', 'gimnasio_plantillas', ['plantilla_id'])
    op.create_index('idx_gimnasio_plantillas_activa', 'gimnasio_plantillas', ['activa'])
    op.create_index('idx_gimnasio_plantillas_prioridad', 'gimnasio_plantillas', ['prioridad'])
    
    # 4. Template usage analytics
    op.create_table(
        'plantilla_analitica',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('plantilla_id', sa.Integer(), nullable=False),
        sa.Column('gimnasio_id', sa.Integer(), nullable=True),
        sa.Column('usuario_id', sa.Integer(), nullable=True),
        sa.Column('evento_tipo', sa.String(50), nullable=False),  # 'view', 'export', 'create', 'edit'
        sa.Column('fecha_evento', sa.DateTime(), nullable=True, server_default=sa.text('current_timestamp')),
        sa.Column('datos_evento', postgresql.JSONB(), nullable=True),
        sa.Column('tiempo_render_ms', sa.Integer(), nullable=True),
        sa.Column('exitoso', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['plantilla_id'], ['plantillas_rutina.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['gimnasio_id'], ['gym_config.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Indexes for plantilla_analitica
    op.create_index('idx_plantilla_analitica_plantilla_id', 'plantilla_analitica', ['plantilla_id'])
    op.create_index('idx_plantilla_analitica_gimnasio_id', 'plantilla_analitica', ['gimnasio_id'])
    op.create_index('idx_plantilla_analitica_usuario_id', 'plantilla_analitica', ['usuario_id'])
    op.create_index('idx_plantilla_analitica_evento_tipo', 'plantilla_analitica', ['evento_tipo'])
    op.create_index('idx_plantilla_analitica_fecha_evento', 'plantilla_analitica', ['fecha_evento'])
    
    # 5. Template marketplace data
    op.create_table(
        'plantilla_mercado',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('plantilla_id', sa.Integer(), nullable=False),
        sa.Column('precio', sa.Numeric(10, 2), nullable=True, server_default='0.00'),
        sa.Column('moneda', sa.String(3), nullable=True, server_default='USD'),
        sa.Column('descargas', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('rating_promedio', sa.Numeric(3, 2), nullable=True),
        sa.Column('rating_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('resenas_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('featured', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('trending', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('categoria_mercado', sa.String(100), nullable=True),
        sa.Column('tags_mercado', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('fecha_publicacion', sa.DateTime(), nullable=True, server_default=sa.text('current_timestamp')),
        sa.Column('fecha_ultima_descarga', sa.DateTime(), nullable=True),
        sa.Column('ingresos_totales', sa.Numeric(12, 2), nullable=True, server_default='0.00'),
        sa.ForeignKeyConstraint(['plantilla_id'], ['plantillas_rutina.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Indexes for plantilla_mercado
    op.create_index('idx_plantilla_mercado_plantilla_id', 'plantilla_mercado', ['plantilla_id'])
    op.create_index('idx_plantilla_mercado_featured', 'plantilla_mercado', ['featured'])
    op.create_index('idx_plantilla_mercado_trending', 'plantilla_mercado', ['trending'])
    op.create_index('idx_plantilla_mercado_categoria_mercado', 'plantilla_mercado', ['categoria_mercado'])
    op.create_index('idx_plantilla_mercado_fecha_publicacion', 'plantilla_mercado', ['fecha_publicacion'])
    
    # 6. Add template_id to existing rutinas table for backward compatibility
    op.add_column('rutinas', sa.Column('plantilla_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_rutinas_plantilla_id',
        'rutinas', 'plantillas_rutina',
        ['plantilla_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_index('idx_rutinas_plantilla_id', 'rutinas', ['plantilla_id'])


def downgrade():
    """Remove template system tables from the database"""
    
    # Remove foreign key and index from rutinas table
    op.drop_index('idx_rutinas_plantilla_id', table_name='rutinas')
    op.drop_constraint('fk_rutinas_plantilla_id', table_name='rutinas', type_='foreignkey')
    op.drop_column('rutinas', 'plantilla_id')
    
    # Drop marketplace table
    op.drop_table('plantilla_mercado')
    
    # Drop analytics table
    op.drop_table('plantilla_analitica')
    
    # Drop gym assignments table
    op.drop_table('gimnasio_plantillas')
    
    # Drop versioning table
    op.drop_table('plantillas_rutina_versiones')
    
    # Drop main templates table
    op.drop_table('plantillas_rutina')
