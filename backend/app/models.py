"""INT_02 · Entidades BD_01–BD_12 y restricciones de integridad RNF_03."""
from datetime import date, datetime, timezone

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.engine import Dialect
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator

from app.database import Base


def now() -> datetime:
    return datetime.now(timezone.utc)


class FechaUTC(TypeDecorator[datetime]):
    """RN_03 · SQLite devuelve fechas sin zona incluso con timezone=True."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value


class User(Base):
    """BD_01 · Cuentas ACT_01, ACT_02 y ACT_03."""

    __tablename__ = 'users'
    __table_args__ = (CheckConstraint("role IN ('admin', 'tutor', 'operador')"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(300))
    full_name: Mapped[str] = mapped_column(String(160), default='')
    role: Mapped[str] = mapped_column(String(24))
    active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(FechaUTC(), default=now)


class Career(Base):
    """BD_09 · Catálogo de carreras."""
    __tablename__ = 'careers'

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    active: Mapped[bool] = mapped_column(default=True)


class Period(Base):
    """BD_06 · Periodo académico identificado por código."""
    __tablename__ = 'periods'

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    start_date: Mapped[date | None]
    end_date: Mapped[date | None]
    active: Mapped[bool] = mapped_column(default=True)


class Student(Base):
    """BD_02 / BD_10 · Expediente y situación laboral."""
    __tablename__ = 'students'
    __table_args__ = (
        CheckConstraint('semester BETWEEN 1 AND 20'),
        CheckConstraint('work_hours_weekly BETWEEN 0 AND 100'),
        CheckConstraint("status IN ('activo', 'baja_temporal', 'baja_definitiva', 'egresado')"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    enrollment_number: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(160))
    program: Mapped[str] = mapped_column(String(100))
    career_id: Mapped[int | None] = mapped_column(ForeignKey('careers.id'))
    tutor_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'), index=True)
    semester: Mapped[int]
    employed: Mapped[bool] = mapped_column(default=False)
    work_hours_weekly: Mapped[int] = mapped_column(default=0)
    active: Mapped[bool] = mapped_column(default=True)
    status: Mapped[str] = mapped_column(String(24), default='activo')
    created_at: Mapped[datetime] = mapped_column(FechaUTC(), default=now)
    updated_at: Mapped[datetime] = mapped_column(FechaUTC(), default=now, onupdate=now)
    career: Mapped[Career | None] = relationship(lazy='joined')
    enrollments: Mapped[list['Enrollment']] = relationship(back_populates='student', cascade='all, delete-orphan')

    @property
    def career_name(self) -> str | None:
        return self.career.name if self.career else None


class Subject(Base):
    """BD_03 · Catálogo de materias."""
    __tablename__ = 'subjects'

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(25), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    credits: Mapped[int] = mapped_column(default=0)
    active: Mapped[bool] = mapped_column(default=True)


class Enrollment(Base):
    """BD_04 / BD_05 · Inscripción y calificación en escala de 0 a 10."""
    __tablename__ = 'enrollments'
    __table_args__ = (
        UniqueConstraint('student_id', 'subject_id', 'term', name='uq_student_subject_term'),
        CheckConstraint('grade BETWEEN 0 AND 10'),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey('students.id'))
    subject_id: Mapped[int] = mapped_column(ForeignKey('subjects.id'))
    term: Mapped[str] = mapped_column(String(30))
    period_id: Mapped[int | None] = mapped_column(ForeignKey('periods.id'))
    grade: Mapped[float | None]
    updated_at: Mapped[datetime] = mapped_column(FechaUTC(), default=now, onupdate=now)
    student: Mapped[Student] = relationship(back_populates='enrollments')
    subject: Mapped[Subject] = relationship(lazy='joined')
    period: Mapped[Period | None] = relationship(lazy='joined')

    @property
    def subject_code(self) -> str:
        return self.subject.code

    @property
    def subject_name(self) -> str:
        return self.subject.name

    @property
    def period_code(self) -> str | None:
        return self.period.code if self.period else None


class PredictionLog(Base):
    """BD_07 · Resultado efectivamente emitido por BD_11, vinculado al solicitante."""
    __tablename__ = 'prediction_logs'
    __table_args__ = (CheckConstraint("risk_category IN ('baja', 'media', 'alta')"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int | None] = mapped_column(ForeignKey('students.id'), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    model_version: Mapped[str | None] = mapped_column(String(120))
    task: Mapped[str | None] = mapped_column(String(80))
    predicted_class: Mapped[str] = mapped_column(String(80))
    probability_dropout: Mapped[float]
    risk_category: Mapped[str] = mapped_column(String(12))
    features: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(FechaUTC(), default=now)


class FollowUp(Base):
    """BD_08 · Sesión de seguimiento registrada por tutor o administrador."""
    __tablename__ = 'followups'

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey('students.id'), index=True)
    tutor_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    date: Mapped[date]
    note: Mapped[str] = mapped_column(Text)
    agreement: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(FechaUTC(), default=now)


class AuditLog(Base):
    """BD_12 / RNF_05 · Eventos registrados en la misma transacción del cambio."""
    __tablename__ = 'audit_logs'
    __table_args__ = (
        CheckConstraint("action IN ('crear', 'editar', 'baja', 'reactivar', 'importar', 'predecir', 'login')"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'))
    action: Mapped[str] = mapped_column(String(20))
    entity: Mapped[str] = mapped_column(String(40))
    entity_id: Mapped[int]
    detail: Mapped[dict | str | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(FechaUTC(), default=now)
