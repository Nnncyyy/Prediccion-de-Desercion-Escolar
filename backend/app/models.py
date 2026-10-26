from datetime import datetime, timezone
from sqlalchemy import String, ForeignKey, Integer, Float, DateTime, Boolean, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

def now(): return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(300))
    role: Mapped[str] = mapped_column(String(24), default='admin')
    active: Mapped[bool] = mapped_column(Boolean, default=True)

class Student(Base):
    __tablename__ = 'students'
    id: Mapped[int] = mapped_column(primary_key=True)
    enrollment_number: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(160))
    program: Mapped[str] = mapped_column(String(100))
    semester: Mapped[int] = mapped_column(Integer)
    employed: Mapped[bool] = mapped_column(Boolean, default=False)
    work_hours_weekly: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    enrollments: Mapped[list['Enrollment']] = relationship(back_populates='student', cascade='all, delete-orphan')

class Subject(Base):
    __tablename__ = 'subjects'
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(25), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    credits: Mapped[int] = mapped_column(Integer, default=0)

class Enrollment(Base):
    __tablename__ = 'enrollments'
    __table_args__ = (UniqueConstraint('student_id','subject_id','term',name='uq_student_subject_term'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey('students.id'))
    subject_id: Mapped[int] = mapped_column(ForeignKey('subjects.id'))
    term: Mapped[str] = mapped_column(String(30))
    grade: Mapped[float | None] = mapped_column(Float, nullable=True)
    student: Mapped[Student] = relationship(back_populates='enrollments')
    subject: Mapped[Subject] = relationship()

class PredictionLog(Base):
    __tablename__ = 'prediction_logs'
    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int | None] = mapped_column(ForeignKey('students.id'), nullable=True)
    kind: Mapped[str] = mapped_column(String(24))
    result: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
