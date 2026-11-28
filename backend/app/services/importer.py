"""RF_07 / RN_04 / RNF_03 / RNF_05 · Validación y carga atómica de CSV."""
import csv
from io import StringIO
from typing import Literal

from fastapi import HTTPException
from pydantic import BaseModel, ValidationError, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Career, Enrollment, Student, Subject, User
from app.routers.enrollments import resolver_periodo
from app.routers.students import completar_programa
from app.schemas import Codigo, CodigoMateria, Estado, Matricula, Nota, StudentCreate
from app.services.audit import aplicar_cambios, log_action

ImportKind = Literal['students', 'enrollments']
MAX_BYTES = 2 * 1024 * 1024
MAX_ROWS = 5000
REQUIRED = {
    'students': ('enrollment_number', 'full_name', 'semester'),
    'enrollments': ('enrollment_number', 'subject_code', 'term'),
}
OPTIONAL = {
    'students': ('career_code', 'program', 'employed', 'work_hours_weekly', 'status', 'tutor_email'),
    'enrollments': ('grade',),
}
EXAMPLES = {
    'students': (
        ('A001', 'Ana García', 2, '', 'Ingeniería en Sistemas', 'no', 0, 'activo', ''),
        ('A002', 'Luis Pérez', 4, '', 'Ingeniería en Sistemas', 'si', 30, 'activo', ''),
    ),
    'enrollments': (
        ('A001', 'MAT', '2027-1', 8.5),
        ('A002', 'MAT', '2027-1', ''),
    ),
}
BOOLEANOS = {'si': True, 'sí': True, 'true': True, '1': True, 'no': False, 'false': False, '0': False}


class RowError(BaseModel):
    row: int
    field: str
    message: str


class ImportResult(BaseModel):
    dry_run: bool
    applied: bool = False
    total_rows: int = 0
    created: int = 0
    updated: int = 0
    errors: list[RowError] = []


class StudentRow(StudentCreate):
    career_code: Codigo | None = None
    status: Estado = 'activo'
    tutor_email: str | None = None

    @field_validator('employed', mode='before')
    @classmethod
    def validar_employed(cls, value: str) -> bool:
        if value.casefold() not in BOOLEANOS:
            raise ValueError('Use si, no, true, false, 1 o 0')
        return BOOLEANOS[value.casefold()]


class EnrollmentRow(BaseModel):
    enrollment_number: Matricula
    subject_code: CodigoMateria
    term: Codigo
    grade: Nota | None = None

    @field_validator('grade', mode='before')
    @classmethod
    def validar_grade(cls, value: str) -> str | None:
        return None if value == '' else value


class InvalidRow(ValueError):
    def __init__(self, field: str, message: str):
        super().__init__(message)
        self.field = field


def template(kind: ImportKind) -> str:
    stream = StringIO(newline='')
    writer = csv.writer(stream)
    writer.writerow(REQUIRED[kind] + OPTIONAL[kind])
    writer.writerows(EXAMPLES[kind])
    return stream.getvalue()


def read_rows(content: bytes, kind: ImportKind, result: ImportResult) -> list[tuple[int, dict[str, str]]]:
    if len(content) > MAX_BYTES:
        raise HTTPException(413, 'El archivo supera el límite de 2 MB')
    try:
        source = content.decode('utf-8-sig')
    except UnicodeDecodeError as error:
        raise HTTPException(422, 'El archivo debe estar codificado en UTF-8') from error

    columns = REQUIRED[kind] + OPTIONAL[kind]
    stream = StringIO(source, newline='')
    header = stream.readline()
    stream.seek(0)
    delimiter = max((',', ';'), key=lambda sep: sum(
        part.strip(' \t\r"').casefold() in columns for part in header.split(sep)
    ))
    reader = csv.reader(stream, delimiter=delimiter, strict=True)
    try:
        headers = [value.strip().casefold() for value in next(reader, [])]
    except csv.Error as error:
        raise HTTPException(422, 'Encabezado CSV inválido') from error
    missing = [column for column in REQUIRED[kind] if column not in headers]
    if missing:
        raise HTTPException(422, {'message': 'Faltan columnas obligatorias', 'missing_columns': missing})
    if len(headers) != len(set(headers)):
        raise HTTPException(422, 'El encabezado contiene columnas repetidas')

    rows = []
    while True:
        line = reader.line_num + 1
        try:
            values = next(reader)
        except StopIteration:
            break
        except csv.Error:
            values = None
        if values == []:
            continue
        result.total_rows += 1
        if result.total_rows > MAX_ROWS:
            raise HTTPException(413, 'El archivo supera el límite de 5,000 filas')
        if values is None or len(values) != len(headers):
            result.errors.append(RowError(row=line, field='csv', message='Fila CSV mal formada'))
            continue
        row = {key: value.strip() for key, value in zip(headers, values) if key in columns}
        if any('\x00' in value for value in row.values()):
            result.errors.append(RowError(row=line, field='csv', message='La fila contiene un carácter nulo'))
            continue
        rows.append((line, row))
    return rows


def preparar_alumno(db: Session, row: dict[str, str], alumnos: dict[str, Student]) -> bool:
    data = StudentRow.model_validate({
        key: value for key, value in row.items() if key in REQUIRED['students'] or value
    })
    campos = data.model_dump(exclude_unset=True, exclude={'career_code', 'tutor_email'})
    alumno = alumnos.get(data.enrollment_number)
    if alumno is None:
        alumno = db.scalar(select(Student).where(Student.enrollment_number == data.enrollment_number))
    if data.career_code:
        carrera = db.scalar(select(Career).where(Career.code == data.career_code))
        if carrera is None:
            raise InvalidRow('career_code', 'Carrera no encontrada')
        campos['career_id'] = carrera.id
    if data.tutor_email:
        tutor = db.scalar(select(User).where(
            User.email == data.tutor_email, User.role == 'tutor', User.active.is_(True),
        ))
        if tutor is None:
            raise InvalidRow('tutor_email', 'Se requiere un tutor activo')
        campos['tutor_id'] = tutor.id

    if 'status' in campos:
        campos['active'] = data.status == 'activo'
    candidato = Student(
        program=campos.get('program', alumno.program if alumno is not None else ''),
        career_id=campos.get('career_id', alumno.career_id if alumno is not None else None),
    )
    try:
        completar_programa(db, candidato)
    except HTTPException as error:
        raise InvalidRow('program', error.detail) from error
    if alumno is None or candidato.program != alumno.program:
        campos['program'] = candidato.program
    creado = alumno is None
    if creado:
        alumno = Student(**campos)
        db.add(alumno)
    else:
        aplicar_cambios(alumno, campos)
    alumnos[data.enrollment_number] = alumno
    return creado


def preparar_inscripcion(db: Session, row: dict[str, str],
                         inscripciones: dict[tuple[int, int, str], Enrollment]) -> bool:
    data = EnrollmentRow.model_validate(row)
    alumno = db.scalar(select(Student).where(Student.enrollment_number == data.enrollment_number))
    if alumno is None:
        raise InvalidRow('enrollment_number', 'Estudiante no encontrado')
    materia = db.scalar(select(Subject).where(Subject.code == data.subject_code))
    if materia is None:
        raise InvalidRow('subject_code', 'Materia no encontrada')
    clave = (alumno.id, materia.id, data.term)
    inscripcion = inscripciones.get(clave)
    if inscripcion is None:
        inscripcion = db.scalar(select(Enrollment).where(
            Enrollment.student_id == alumno.id, Enrollment.subject_id == materia.id, Enrollment.term == data.term,
        ))
    creada = inscripcion is None
    if creada:
        if not alumno.active:
            raise InvalidRow('enrollment_number', 'El estudiante está inactivo')
        inscripcion = Enrollment(student_id=alumno.id, subject_id=materia.id, term=data.term)
        db.add(inscripcion)
    if 'grade' in data.model_fields_set:
        inscripcion.grade = data.grade
    inscripciones[clave] = inscripcion
    return creada


def importar(db: Session, usuario: User, kind: ImportKind, content: bytes, dry_run: bool) -> ImportResult:
    """RNF_03 / RNF_05 · Confirma los cambios y su bitácora en una sola transacción."""
    result = ImportResult(dry_run=dry_run)
    rows = read_rows(content, kind, result)
    alumnos: dict[str, Student] = {}
    inscripciones: dict[tuple[int, int, str], Enrollment] = {}
    try:
        with db.no_autoflush:
            for line, row in rows:
                try:
                    if kind == 'students':
                        creado = preparar_alumno(db, row, alumnos)
                    else:
                        creado = preparar_inscripcion(db, row, inscripciones)
                except InvalidRow as error:
                    result.errors.append(RowError(row=line, field=error.field, message=str(error)))
                    continue
                except ValidationError as error:
                    for item in error.errors():
                        field = item['loc'][0]
                        obligatorio = item['type'] == 'missing' or row.get(field) == ''
                        message = 'Campo obligatorio' if obligatorio else 'Valor inválido'
                        result.errors.append(RowError(row=line, field=field, message=message))
                    continue
                if creado:
                    result.created += 1
                else:
                    result.updated += 1

            result.errors.sort(key=lambda error: error.row)
            if dry_run or result.errors or not rows:
                db.rollback()
                return result
            # BD_06 · Orden estable de bloqueos cuando coinciden varios periodos entre lotes.
            periodos = {
                term: resolver_periodo(db, usuario, term, None).id
                for term in sorted({inscripcion.term for inscripcion in inscripciones.values()})
            }
            for inscripcion in inscripciones.values():
                inscripcion.period_id = periodos[inscripcion.term]
            result.applied = True
            log_action(db, usuario, 'importar', kind, 0, result.model_dump())
            db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(409, 'Conflicto de integridad al importar el archivo') from error
    return result
