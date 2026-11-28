# Formato de importación CSV · RF_07

Envía el CSV como archivo adjunto en el campo `file` de una solicitud `multipart/form-data`, con una sesión de administrador. Descarga ejemplos en `/api/import/templates/students` y `/api/import/templates/enrollments`.

Usa UTF-8, con o sin BOM, y coma o punto y coma como separador. La primera fila contiene los encabezados. Se admiten mayúsculas y espacios alrededor de los encabezados y valores. Las columnas adicionales se ignoran. Los encabezados deben ser únicos. Usa comillas dobles para delimitar un valor que contenga el separador y duplica las comillas que formen parte del valor. Escribe las calificaciones decimales con punto. El máximo es 2 MiB (2,097,152 bytes) y 5,000 registros de datos. Las líneas vacías se omiten.

## Alumnos · POST `/api/import/students`

| Columna | Presencia | Tipo y validación |
|---|---|---|
| `enrollment_number` | Obligatoria | Matrícula de 1 a 40 caracteres. Conserva los ceros a la izquierda. |
| `full_name` | Obligatoria | Nombre de 2 a 160 caracteres. |
| `semester` | Obligatoria | Entero entre 1 y 20. |
| `career_code` | Opcional | Código de carrera existente, de hasta 30 caracteres. |
| `program` | Opcional | Programa de hasta 100 caracteres. Para un alta se requiere un programa o una carrera. Si solo se indica la carrera, se toma su nombre como programa. |
| `employed` | Opcional | `si`, `sí`, `no`, `true`, `false`, `1` o `0`, sin distinción de mayúsculas. En un alta vale falso por defecto. |
| `work_hours_weekly` | Opcional | Entero entre 0 y 100. En un alta vale 0 por defecto. |
| `status` | Opcional | `activo`, `baja_temporal`, `baja_definitiva` o `egresado`. En un alta vale `activo` por defecto. |
| `tutor_email` | Opcional | Correo registrado de un tutor activo. En un alta la asignación queda vacía por defecto. |

Una matrícula existente actualiza el expediente. Las columnas opcionales de alumnos omitidas o vacías conservan sus valores existentes. Si se indica `status`, el campo `active` se sincroniza con ese estado. Los códigos y correos deben escribirse como están registrados.

```csv
enrollment_number,full_name,semester,program,employed,work_hours_weekly
A001,Ana García,2,Ingeniería en Sistemas,no,0
A002,Luis Pérez,4,Ingeniería en Sistemas,si,30
```

## Inscripciones · POST `/api/import/enrollments`

| Columna | Presencia | Tipo y validación |
|---|---|---|
| `enrollment_number` | Obligatoria | Matrícula existente de 1 a 40 caracteres. Las inscripciones nuevas requieren un alumno activo. |
| `subject_code` | Obligatoria | Código exacto de una materia existente, de 1 a 25 caracteres. |
| `term` | Obligatoria | Código de periodo de 1 a 30 caracteres. Si falta en el catálogo, se crea un periodo activo con ese código y nombre. |
| `grade` | Opcional | Número de 0 a 10. Una celda vacía deja la nota pendiente. Si falta la columna, un registro nuevo queda pendiente y uno existente conserva su nota. |

La combinación matrícula, materia y periodo identifica la inscripción a actualizar. En este ejemplo, registra la materia `MAT` y los alumnos antes de importar.

```csv
enrollment_number;subject_code;term;grade
A001;MAT;2027-1;8.5
A002;MAT;2027-1;
```

## Simulación, errores y auditoría

Usa `?dry_run=true` para simular la importación. La respuesta incluye el total de registros y las altas o actualizaciones previstas para las filas válidas. Si se repite una clave en el mismo archivo, las filas se procesan en orden y la segunda cuenta como actualización.

- **200** · El informe incluye `errors` con línea física de inicio de la fila, campo y mensaje en español. El encabezado empieza en la línea 1. Los errores incluyen filas mal formadas, campos vacíos obligatorios, valores fuera de rango, estatus inválidos, carreras o materias ausentes y tutores inexistentes o inactivos. Cualquier error revierte el lote completo. `applied` solo vale `true` si se confirmaron los cambios y su bitácora.
- **401 o 403** · Sesión inválida o rol distinto de administrador.
- **409** · Conflicto de integridad durante la confirmación. Se revierte el lote.
- **413** · Archivo o cantidad de registros por encima del límite.
- **422** · Archivo ausente, codificación o parámetros inválidos, encabezado inválido, repetido o con columnas obligatorias faltantes. Para estas últimas, consulta `detail.missing_columns`.

Solo los lotes confirmados registran `importar` en la bitácora, con entidad `students` o `enrollments` y el resumen del lote.
