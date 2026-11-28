"""RF_07 / RN_04 / PT_07 · Importación CSV reservada a ACT_01."""
from typing import Annotated

from fastapi import APIRouter, File, Response, UploadFile

from app.deps import Administrador, DB
from app.services.importer import MAX_BYTES, ImportKind, ImportResult, importar, template

router = APIRouter(prefix='/api/import', tags=['Importaciones'])
ArchivoCSV = Annotated[UploadFile, File()]


@router.post('/students', response_model=ImportResult)
def importar_alumnos(file: ArchivoCSV, db: DB, usuario: Administrador, dry_run: bool = False) -> ImportResult:
    return importar(db, usuario, 'students', file.file.read(MAX_BYTES + 1), dry_run)


@router.post('/enrollments', response_model=ImportResult)
def importar_inscripciones(file: ArchivoCSV, db: DB, usuario: Administrador,
                           dry_run: bool = False) -> ImportResult:
    return importar(db, usuario, 'enrollments', file.file.read(MAX_BYTES + 1), dry_run)


@router.get('/templates/{kind}', response_class=Response)
def descargar_plantilla(kind: ImportKind, usuario: Administrador) -> Response:
    return Response(
        template(kind), media_type='text/csv',
        headers={'Content-Disposition': f'attachment; filename="plantilla-{kind}.csv"'},
    )
