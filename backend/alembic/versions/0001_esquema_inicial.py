"""RNF_03 / RT_03 · Esquema inicial de SIPDE (BD_01 a BD_12)."""
from alembic import op
import sqlalchemy as sa

revision = '0001_esquema_inicial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Crea las tablas, restricciones e índices iniciales."""
    op.create_table('careers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=30), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code'),
        sa.UniqueConstraint('name'),
    )

    op.create_table('periods',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=30), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=True),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code'),
    )

    op.create_table('subjects',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=25), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('credits', sa.Integer(), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code'),
    )

    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=160), nullable=False),
        sa.Column('password_hash', sa.String(length=300), nullable=False),
        sa.Column('full_name', sa.String(length=160), nullable=False),
        sa.Column('role', sa.String(length=24), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("role IN ('admin', 'tutor', 'operador')"),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    op.create_table('audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(length=20), nullable=False),
        sa.Column('entity', sa.String(length=40), nullable=False),
        sa.Column('entity_id', sa.Integer(), nullable=False),
        sa.Column('detail', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("action IN ('crear', 'editar', 'baja', 'reactivar', 'importar', 'predecir', 'login')"),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table('students',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('enrollment_number', sa.String(length=40), nullable=False),
        sa.Column('full_name', sa.String(length=160), nullable=False),
        sa.Column('program', sa.String(length=100), nullable=False),
        sa.Column('career_id', sa.Integer(), nullable=True),
        sa.Column('tutor_id', sa.Integer(), nullable=True),
        sa.Column('semester', sa.Integer(), nullable=False),
        sa.Column('employed', sa.Boolean(), nullable=False),
        sa.Column('work_hours_weekly', sa.Integer(), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column('status', sa.String(length=24), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('activo', 'baja_temporal', 'baja_definitiva', 'egresado')"),
        sa.CheckConstraint('semester BETWEEN 1 AND 20'),
        sa.CheckConstraint('work_hours_weekly BETWEEN 0 AND 100'),
        sa.ForeignKeyConstraint(['career_id'], ['careers.id']),
        sa.ForeignKeyConstraint(['tutor_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_students_enrollment_number', 'students', ['enrollment_number'], unique=True)
    op.create_index('ix_students_tutor_id', 'students', ['tutor_id'], unique=False)

    op.create_table('enrollments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('subject_id', sa.Integer(), nullable=False),
        sa.Column('term', sa.String(length=30), nullable=False),
        sa.Column('period_id', sa.Integer(), nullable=True),
        sa.Column('grade', sa.Double(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint('grade BETWEEN 0 AND 10'),
        sa.ForeignKeyConstraint(['period_id'], ['periods.id']),
        sa.ForeignKeyConstraint(['student_id'], ['students.id']),
        sa.ForeignKeyConstraint(['subject_id'], ['subjects.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('student_id', 'subject_id', 'term', name='uq_student_subject_term'),
    )

    op.create_table('followups',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('tutor_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('note', sa.Text(), nullable=False),
        sa.Column('agreement', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['student_id'], ['students.id']),
        sa.ForeignKeyConstraint(['tutor_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_followups_student_id', 'followups', ['student_id'], unique=False)

    op.create_table('prediction_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('model_version', sa.String(length=120), nullable=True),
        sa.Column('task', sa.String(length=80), nullable=True),
        sa.Column('predicted_class', sa.String(length=80), nullable=False),
        sa.Column('probability_dropout', sa.Double(), nullable=False),
        sa.Column('risk_category', sa.String(length=12), nullable=False),
        sa.Column('features', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("risk_category IN ('baja', 'media', 'alta')"),
        sa.ForeignKeyConstraint(['student_id'], ['students.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_prediction_logs_student_id', 'prediction_logs', ['student_id'], unique=False)


def downgrade() -> None:
    """Retira las tablas en orden inverso al de sus dependencias."""
    op.drop_table('prediction_logs')
    op.drop_table('followups')
    op.drop_table('enrollments')
    op.drop_table('students')
    op.drop_table('audit_logs')
    op.drop_table('users')
    op.drop_table('subjects')
    op.drop_table('periods')
    op.drop_table('careers')
