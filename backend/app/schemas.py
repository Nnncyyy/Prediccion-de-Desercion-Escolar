"""INT_02 · Contratos de entrada y salida RF_01–RF_14."""
from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

Rol = Literal['admin', 'tutor', 'operador']
Baja = Literal['baja_temporal', 'baja_definitiva', 'egresado']
Estado = Literal['activo', 'baja_temporal', 'baja_definitiva', 'egresado']
Categoria = Literal['baja', 'media', 'alta']
Nombre = Annotated[str, Field(min_length=1, max_length=120)]
NombrePersona = Annotated[str, Field(min_length=2, max_length=160)]
Codigo = Annotated[str, Field(min_length=1, max_length=30)]
CodigoMateria = Annotated[str, Field(min_length=1, max_length=25)]
Carrera = Annotated[str, Field(min_length=1, max_length=100)]
Programa = Annotated[str, Field(max_length=100)]
Matricula = Annotated[str, Field(min_length=1, max_length=40)]
Contrasena = Annotated[str, Field(min_length=8)]
Semestre = Annotated[int, Field(ge=1, le=20)]
Horas = Annotated[int, Field(ge=0, le=100)]
Creditos = Annotated[int, Field(ge=0, le=50)]
Nota = Annotated[float, Field(ge=0, le=10)]


class Entrada(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Salida(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class LoginInput(Entrada):
    email: str
    password: str


class PasswordChange(Entrada):
    current_password: str
    new_password: Contrasena


class UserCreate(Entrada):
    email: Annotated[str, Field(max_length=160, pattern=r'^[^\s@]+@[^\s@]+\.[^\s@]+$')]
    full_name: NombrePersona
    role: Rol
    password: Contrasena


# RF_02 · En los PATCH se aplica solo model_fields_set. Un valor omitido
# conserva el dato, y null solo se admite en las anotaciones que incluyen None.
class UserPatch(Entrada):
    full_name: NombrePersona = Field(default=None)
    role: Rol = Field(default=None)
    active: bool = Field(default=None)
    password: Contrasena = Field(default=None)


class UserInfo(Salida):
    id: int
    email: str
    full_name: str
    role: Rol


class UserOut(UserInfo):
    active: bool
    created_at: datetime


class LoginOut(Salida):
    access_token: str
    token_type: str
    role: Rol
    user: UserInfo


class StudentCreate(Entrada):
    enrollment_number: Matricula
    full_name: NombrePersona
    program: Programa = ''
    career_id: int | None = None
    semester: Semestre
    employed: bool = False
    work_hours_weekly: Horas = 0


class StudentPatch(Entrada):
    enrollment_number: Matricula = Field(default=None)
    full_name: NombrePersona = Field(default=None)
    program: Programa = Field(default=None)
    career_id: int | None = None
    semester: Semestre = Field(default=None)
    employed: bool = Field(default=None)
    work_hours_weekly: Horas = Field(default=None)


class StudentOut(Salida):
    id: int
    enrollment_number: str
    full_name: str
    program: str
    career_id: int | None
    career_name: str | None
    tutor_id: int | None
    semester: int
    employed: bool
    work_hours_weekly: int
    status: Estado
    active: bool
    created_at: datetime
    updated_at: datetime


class StudentDeactivate(Entrada):
    status: Baja = 'baja_temporal'
    reason: str | None = None


class StudentTutor(Entrada):
    tutor_id: int | None


class CareerCreate(Entrada):
    code: Codigo
    name: Carrera
    active: bool = True


class CareerPatch(Entrada):
    code: Codigo = Field(default=None)
    name: Carrera = Field(default=None)
    active: bool = Field(default=None)


class CareerOut(CareerCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)


class PeriodCreate(Entrada):
    code: Codigo
    name: Nombre
    start_date: date | None = None
    end_date: date | None = None
    active: bool = True


class PeriodPatch(Entrada):
    code: Codigo = Field(default=None)
    name: Nombre = Field(default=None)
    start_date: date | None = None
    end_date: date | None = None
    active: bool = Field(default=None)


class PeriodOut(PeriodCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)


class SubjectCreate(Entrada):
    code: CodigoMateria
    name: Nombre
    credits: Creditos = 0
    active: bool = True


class SubjectPatch(Entrada):
    code: CodigoMateria = Field(default=None)
    name: Nombre = Field(default=None)
    credits: Creditos = Field(default=None)
    active: bool = Field(default=None)


class SubjectOut(SubjectCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)


class EnrollmentCreate(Entrada):
    student_id: int
    subject_id: int
    term: Codigo | None = None
    period_id: int | None = None
    grade: Nota | None = None


class EnrollmentPatch(Entrada):
    term: Codigo = Field(default=None)
    period_id: int = Field(default=None)
    grade: Nota | None = None


class EnrollmentOut(Salida):
    id: int
    student_id: int
    subject_id: int
    term: str
    period_id: int | None
    period_code: str | None
    subject_code: str
    subject_name: str
    grade: float | None
    updated_at: datetime


class FollowUpCreate(Entrada):
    date: date
    note: Annotated[str, Field(min_length=1)]
    agreement: str | None = None


class FollowUpOut(FollowUpCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    student_id: int
    tutor_id: int
    created_at: datetime


class MLPredictInput(Entrada):
    features: dict[str, str | int | float | bool | None]
    student_id: int | None = None


class PredictionSummary(Salida):
    id: int
    student_id: int | None
    user_id: int
    model_version: str | None
    task: str | None
    predicted_class: str
    probability_dropout: float
    risk_category: Categoria
    created_at: datetime


class PredictionOut(PredictionSummary):
    features: dict


class AuditOut(Salida):
    id: int
    user_id: int | None
    action: str
    entity: str
    entity_id: int
    detail: str | dict | None
    created_at: datetime
