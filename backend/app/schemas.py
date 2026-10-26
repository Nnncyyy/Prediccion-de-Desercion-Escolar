from pydantic import BaseModel, Field, ConfigDict

class StudentCreate(BaseModel):
    enrollment_number: str = Field(min_length=1, max_length=40)
    full_name: str = Field(min_length=2, max_length=160)
    program: str = Field(min_length=1, max_length=100)
    semester: int = Field(ge=1, le=20)
    employed: bool = False
    work_hours_weekly: int = Field(default=0, ge=0, le=100)

class StudentOut(StudentCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)

class SubjectCreate(BaseModel):
    code: str = Field(min_length=1, max_length=25)
    name: str = Field(min_length=1, max_length=120)
    credits: int = Field(default=0, ge=0, le=50)

class SubjectOut(SubjectCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)

class EnrollmentCreate(BaseModel):
    student_id: int
    subject_id: int
    term: str = Field(min_length=1, max_length=30)
    grade: float | None = Field(default=None, ge=0, le=10)  # Escala inicial configurable en futuro

class EnrollmentOut(EnrollmentCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)

class MLPredictInput(BaseModel):
    features: dict[str, str | int | float | bool | None]

class LoginInput(BaseModel):
    email: str
    password: str
