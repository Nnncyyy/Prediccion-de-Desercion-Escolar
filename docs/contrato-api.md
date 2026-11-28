# INT_02 · Contrato HTTP de SIPDE

Referencia para el cliente web. Los ejemplos usan una misma base temporal y el modelo local. Los identificadores, las fechas y las probabilidades son valores de ejemplo. En login, sustituye el marcador del JWT por el token recibido.

## Convenciones

- Envía JSON con `Content-Type: application/json`. Para una operación autenticada, envía `Authorization: Bearer <access_token>`. Las fechas de calendario usan `YYYY-MM-DD` y los instantes se expresan en UTC.
- **401** indica sesión ausente, inválida, vencida o cuenta inactiva. Login y cambio de contraseña también comprueban las credenciales. **403** devuelve `{"detail":"No tiene permiso para esta acción"}`. **404** identifica un recurso ausente o un estudiante fuera del alcance del tutor.
- **409** indica un conflicto al guardar. **422** indica entrada inválida. Para errores de esquema se devuelve, por ejemplo, `{"detail":[{"loc":["body","semester"],"msg":"Valor inválido","type":"greater_than_equal"}]}`. Las validaciones de negocio devuelven `{"detail":"mensaje"}`. El validador ML detalla los fallos por variable. **503** indica que el modelo o su esquema no están disponibles.
- En cada PATCH, envía únicamente los campos que cambian. Los cuerpos rechazan claves desconocidas. Un campo anulable se borra enviando `null`. En las rutas paginadas, `skip` es un entero ≥ 0 (por defecto 0) y `limit` un entero ≥ 1 (por defecto 100).
- Los nombres de campos se mantienen como aparecen en JSON. Las rutas de importación RF_07 y reportes RF_13 quedan reservadas para Tarea G.

## Servicio y autenticación · RF_01 / CU_01

### GET /api/health

- **Acceso** · Público.
- **Errores** · Ninguno de dominio.

**Cuerpo** · Sin cuerpo.

**Respuesta 200**

```json
{
  "status": "ok",
  "service": "SIPDE"
}
```

### POST /api/auth/login

- **Acceso** · Público.
- **Errores** · 401 credenciales incorrectas o cuenta inactiva, 422 cuerpo inválido.

El JWT tiene una vigencia de ocho horas.

**Cuerpo de ejemplo**

```json
{
  "email": "admin@example.test",
  "password": "EjemploLocal123"
}
```

**Respuesta 200**

```json
{
  "access_token": "<JWT>",
  "token_type": "bearer",
  "role": "admin",
  "user": {
    "id": 1,
    "email": "admin@example.test",
    "full_name": "Administrador",
    "role": "admin"
  }
}
```

### GET /api/auth/me

- **Acceso** · admin, operador y tutor.
- **Errores** · 401.

**Cuerpo** · Sin cuerpo.

**Respuesta 200**

```json
{
  "id": 1,
  "email": "admin@example.test",
  "full_name": "Administrador",
  "role": "admin",
  "active": true,
  "created_at": "2026-11-25T04:03:11.776686Z"
}
```

### POST /api/auth/change-password

- **Acceso** · admin, operador y tutor.
- **Errores** · 401 sesión inválida o contraseña actual incorrecta, 422.

La contraseña nueva requiere al menos ocho caracteres.

**Cuerpo de ejemplo**

```json
{
  "current_password": "EjemploLocal123",
  "new_password": "EjemploNuevo123"
}
```

**Respuesta 200**

```json
{
  "message": "Contraseña actualizada"
}
```

## Usuarios · RF_02 / ACT_01

### POST /api/users

- **Acceso** · admin.
- **Errores** · 401, 403, 409 correo duplicado, 422.

Envía los cuatro campos. Roles válidos: `admin`, `operador` y `tutor`. El nombre admite de 2 a 160 caracteres y la contraseña requiere al menos 8.

**Cuerpo de ejemplo**

```json
{
  "email": "tutor@example.test",
  "full_name": "Laura Flores",
  "role": "tutor",
  "password": "TutoriaLocal123"
}
```

**Respuesta 201**

```json
{
  "id": 2,
  "email": "tutor@example.test",
  "full_name": "Laura Flores",
  "role": "tutor",
  "active": true,
  "created_at": "2026-11-25T04:03:12.578117Z"
}
```

### GET /api/users

- **Acceso** · admin.
- **Errores** · 401, 403.

Incluye cuentas activas e inactivas, ordenadas por ID ascendente.

**Cuerpo** · Sin cuerpo.

**Respuesta 200**

```json
[
  {
    "id": 1,
    "email": "admin@example.test",
    "full_name": "Administrador",
    "role": "admin",
    "active": true,
    "created_at": "2026-11-25T04:03:11.776686Z"
  },
  {
    "id": 2,
    "email": "tutor@example.test",
    "full_name": "Laura Flores",
    "role": "tutor",
    "active": true,
    "created_at": "2026-11-25T04:03:12.578117Z"
  }
]
```

### PATCH /api/users/{user_id}

- **Acceso** · admin.
- **Errores** · 401, 403, 404, 409 autoprotección del administrador, 422.

Admite `full_name`, `role`, `active` y `password`. Para desactivar envía `{"active":false}`. El administrador conserva su propio rol y su cuenta activa. El sistema conserva al menos un administrador activo.

**Cuerpo de ejemplo**

```json
{
  "full_name": "Laura Flores Ramos"
}
```

**Respuesta 200**

```json
{
  "id": 2,
  "email": "tutor@example.test",
  "full_name": "Laura Flores Ramos",
  "role": "tutor",
  "active": true,
  "created_at": "2026-11-25T04:03:12.578117Z"
}
```

## Catálogos · RF_04

### POST /api/careers

- **Acceso** · admin.
- **Errores** · 401, 403, 409 código o nombre duplicado, 422.

Código de 1–30 y nombre de 1–100 caracteres. Se requieren code y name. active es opcional y vale true por defecto.

**Cuerpo de ejemplo**

```json
{
  "code": "ISC",
  "name": "Sistemas"
}
```

**Respuesta 201**

```json
{
  "code": "ISC",
  "name": "Sistemas",
  "active": true,
  "id": 1
}
```

### GET /api/careers

- **Acceso** · admin, operador y tutor.
- **Errores** · 401, 422 filtro inválido.

Filtro opcional `active`. Sin filtro incluye activos e inactivos, ordenados por nombre e ID.

Ejemplo de consulta `/api/careers?active=true`.

**Cuerpo** · Sin cuerpo.

**Respuesta 200**

```json
[
  {
    "code": "ISC",
    "name": "Sistemas",
    "active": true,
    "id": 1
  }
]
```

### PATCH /api/careers/{career_id}

- **Acceso** · admin.
- **Errores** · 401, 403, 404, 409 código o nombre duplicado, 422.

Admite los mismos campos que el alta. Envía `{"active":false}` para desactivar o `{"active":true}` para reactivar.

**Cuerpo de ejemplo**

```json
{
  "name": "Ingeniería en Sistemas"
}
```

**Respuesta 200**

```json
{
  "code": "ISC",
  "name": "Ingeniería en Sistemas",
  "active": true,
  "id": 1
}
```

### POST /api/periods

- **Acceso** · admin.
- **Errores** · 401, 403, 409 código duplicado o conflicto al actualizar term, 422.

Código de 1–30 y nombre de 1–120 caracteres. Las fechas son opcionales y anulables. La fecha final debe ser igual o posterior a la inicial. Cambiar el código actualiza term en las inscripciones vinculadas. Se requieren code y name. active es opcional y vale true por defecto.

**Cuerpo de ejemplo**

```json
{
  "code": "2026-2",
  "name": "Segundo periodo de 2026",
  "start_date": "2026-08-01"
}
```

**Respuesta 201**

```json
{
  "code": "2026-2",
  "name": "Segundo periodo de 2026",
  "start_date": "2026-08-01",
  "end_date": null,
  "active": true,
  "id": 1
}
```

### GET /api/periods

- **Acceso** · admin, operador y tutor.
- **Errores** · 401, 422 filtro inválido.

Filtro opcional `active`. Sin filtro incluye activos e inactivos, ordenados por nombre e ID.

Ejemplo de consulta `/api/periods?active=true`.

**Cuerpo** · Sin cuerpo.

**Respuesta 200**

```json
[
  {
    "code": "2026-2",
    "name": "Segundo periodo de 2026",
    "start_date": "2026-08-01",
    "end_date": null,
    "active": true,
    "id": 1
  }
]
```

### PATCH /api/periods/{period_id}

- **Acceso** · admin.
- **Errores** · 401, 403, 404, 409 código duplicado o conflicto al actualizar term, 422.

Admite los mismos campos que el alta. Envía `{"active":false}` para desactivar o `{"active":true}` para reactivar.

**Cuerpo de ejemplo**

```json
{
  "end_date": "2026-12-15"
}
```

**Respuesta 200**

```json
{
  "code": "2026-2",
  "name": "Segundo periodo de 2026",
  "start_date": "2026-08-01",
  "end_date": "2026-12-15",
  "active": true,
  "id": 1
}
```

### POST /api/subjects

- **Acceso** · admin.
- **Errores** · 401, 403, 409 código duplicado, 422.

Código de 1–25 y nombre de 1–120 caracteres. Los créditos admiten 0–50 y por defecto valen 0. Se requieren code y name. active es opcional y vale true por defecto.

**Cuerpo de ejemplo**

```json
{
  "code": "MAT",
  "name": "Matemáticas",
  "credits": 5
}
```

**Respuesta 201**

```json
{
  "code": "MAT",
  "name": "Matemáticas",
  "credits": 5,
  "active": true,
  "id": 1
}
```

### GET /api/subjects

- **Acceso** · admin, operador y tutor.
- **Errores** · 401, 422 filtro inválido.

Filtro opcional `active`. Sin filtro incluye activos e inactivos, ordenados por nombre e ID.

Ejemplo de consulta `/api/subjects?active=true`.

**Cuerpo** · Sin cuerpo.

**Respuesta 200**

```json
[
  {
    "code": "MAT",
    "name": "Matemáticas",
    "credits": 5,
    "active": true,
    "id": 1
  }
]
```

### PATCH /api/subjects/{subject_id}

- **Acceso** · admin.
- **Errores** · 401, 403, 404, 409 código duplicado, 422.

Admite los mismos campos que el alta. Envía `{"active":false}` para desactivar o `{"active":true}` para reactivar.

**Cuerpo de ejemplo**

```json
{
  "credits": 6
}
```

**Respuesta 200**

```json
{
  "code": "MAT",
  "name": "Matemáticas",
  "credits": 6,
  "active": true,
  "id": 1
}
```

## Estudiantes y situación laboral · RF_03 / RF_06 / CU_02

### POST /api/students

- **Acceso** · admin y operador.
- **Errores** · 401, 403, 404 carrera ausente, 409 matrícula duplicada, 422.

Requiere matrícula (1–40 caracteres), nombre (2–160), semestre (1–20) y program o career_id. Con carrera y program omitido o vacío se copia su nombre. program admite hasta 100 caracteres. employed vale false y work_hours_weekly vale 0 por defecto (rango 0–100). El alumno inicia activo y sin tutor.

**Cuerpo de ejemplo**

```json
{
  "enrollment_number": "A001",
  "full_name": "Ana García",
  "semester": 2,
  "career_id": 1
}
```

**Respuesta 201**

```json
{
  "id": 1,
  "enrollment_number": "A001",
  "full_name": "Ana García",
  "program": "Ingeniería en Sistemas",
  "career_id": 1,
  "career_name": "Ingeniería en Sistemas",
  "tutor_id": null,
  "semester": 2,
  "employed": false,
  "work_hours_weekly": 0,
  "status": "activo",
  "active": true,
  "created_at": "2026-11-25T04:03:14.007503Z",
  "updated_at": "2026-11-25T04:03:14.007508Z"
}
```

### GET /api/students

- **Acceso** · admin y operador para todos los alumnos. Tutor para sus alumnos asignados.
- **Errores** · 401, 422 filtros o paginación inválidos.

Filtros combinables: `q` busca una subcadena literal en matrícula o nombre sin distinguir mayúsculas, `career_id`, `tutor_id`, `status` y `active` comparan por igualdad. Sin filtros incluye activos e inactivos. Devuelve una lista por ID descendente. La cabecera `X-Total-Count` contiene el total visible filtrado antes de aplicar skip/limit (1 en el ejemplo).

Ejemplo de consulta `/api/students?q=ana&career_id=1&active=true&status=activo&skip=0&limit=25`.

**Cuerpo** · Sin cuerpo.

**Respuesta 200**

```json
[
  {
    "id": 1,
    "enrollment_number": "A001",
    "full_name": "Ana García",
    "program": "Ingeniería en Sistemas",
    "career_id": 1,
    "career_name": "Ingeniería en Sistemas",
    "tutor_id": null,
    "semester": 2,
    "employed": false,
    "work_hours_weekly": 0,
    "status": "activo",
    "active": true,
    "created_at": "2026-11-25T04:03:14.007503Z",
    "updated_at": "2026-11-25T04:03:14.007508Z"
  }
]
```

### GET /api/students/{student_id}

- **Acceso** · admin y operador para todos los alumnos. Tutor para sus alumnos asignados.
- **Errores** · 401, 404, 422 ID inválido.

**Cuerpo** · Sin cuerpo.

**Respuesta 200**

```json
{
  "id": 1,
  "enrollment_number": "A001",
  "full_name": "Ana García",
  "program": "Ingeniería en Sistemas",
  "career_id": 1,
  "career_name": "Ingeniería en Sistemas",
  "tutor_id": null,
  "semester": 2,
  "employed": false,
  "work_hours_weekly": 0,
  "status": "activo",
  "active": true,
  "created_at": "2026-11-25T04:03:14.007503Z",
  "updated_at": "2026-11-25T04:03:14.007508Z"
}
```

### PATCH /api/students/{student_id}

- **Acceso** · admin y operador.
- **Errores** · 401, 403, 404 alumno o carrera ausentes, 409 matrícula duplicada, 422.

Admite los campos del alta. Para desvincular la carrera, envía `{"career_id":null}`. Para copiar el nombre de una carrera nueva, envía también `"program":""`. La asignación de tutor y los cambios de estado tienen rutas propias.

**Cuerpo de ejemplo**

```json
{
  "employed": true,
  "work_hours_weekly": 30
}
```

**Respuesta 200**

```json
{
  "id": 1,
  "enrollment_number": "A001",
  "full_name": "Ana García",
  "program": "Ingeniería en Sistemas",
  "career_id": 1,
  "career_name": "Ingeniería en Sistemas",
  "tutor_id": null,
  "semester": 2,
  "employed": true,
  "work_hours_weekly": 30,
  "status": "activo",
  "active": true,
  "created_at": "2026-11-25T04:03:14.007503Z",
  "updated_at": "2026-11-25T04:03:14.355476Z"
}
```

### POST /api/students/{student_id}/deactivate

- **Acceso** · admin.
- **Errores** · 401, 403, 404, 422.

El cuerpo es opcional. status acepta baja_temporal (por defecto), baja_definitiva y egresado. reason es opcional y se guarda en bitácora.

**Cuerpo de ejemplo**

```json
{
  "status": "baja_temporal",
  "reason": "Solicitud del alumno"
}
```

**Respuesta 200**

```json
{
  "id": 1,
  "enrollment_number": "A001",
  "full_name": "Ana García",
  "program": "Ingeniería en Sistemas",
  "career_id": 1,
  "career_name": "Ingeniería en Sistemas",
  "tutor_id": null,
  "semester": 2,
  "employed": true,
  "work_hours_weekly": 30,
  "status": "baja_temporal",
  "active": false,
  "created_at": "2026-11-25T04:03:14.007503Z",
  "updated_at": "2026-11-25T04:03:14.468030Z"
}
```

### POST /api/students/{student_id}/reactivate

- **Acceso** · admin.
- **Errores** · 401, 403, 404, 422 ID inválido.

Restaura active=true y status=activo.

**Cuerpo** · Sin cuerpo.

**Respuesta 200**

```json
{
  "id": 1,
  "enrollment_number": "A001",
  "full_name": "Ana García",
  "program": "Ingeniería en Sistemas",
  "career_id": 1,
  "career_name": "Ingeniería en Sistemas",
  "tutor_id": null,
  "semester": 2,
  "employed": true,
  "work_hours_weekly": 30,
  "status": "activo",
  "active": true,
  "created_at": "2026-11-25T04:03:14.007503Z",
  "updated_at": "2026-11-25T04:03:14.592378Z"
}
```

### PUT /api/students/{student_id}/tutor

- **Acceso** · admin.
- **Errores** · 401, 403, 404 alumno o usuario ausente, 422 tutor inactivo, rol incorrecto o cuerpo inválido.

Exige tutor_id. Envía null para retirar la asignación.

**Cuerpo de ejemplo**

```json
{
  "tutor_id": 2
}
```

**Respuesta 200**

```json
{
  "id": 1,
  "enrollment_number": "A001",
  "full_name": "Ana García",
  "program": "Ingeniería en Sistemas",
  "career_id": 1,
  "career_name": "Ingeniería en Sistemas",
  "tutor_id": 2,
  "semester": 2,
  "employed": true,
  "work_hours_weekly": 30,
  "status": "activo",
  "active": true,
  "created_at": "2026-11-25T04:03:14.007503Z",
  "updated_at": "2026-11-25T04:03:14.718361Z"
}
```

## Inscripciones, calificaciones y alertas · RF_05 / RF_10 / CU_03 / CU_05

### POST /api/enrollments

- **Acceso** · admin y operador.
- **Errores** · 401, 403, 404 alumno, materia o periodo por ID ausentes, 409 alumno inactivo o inscripción duplicada, 422.

Requiere student_id, subject_id y al menos uno de term y period_id. Un term nuevo crea un periodo activo con ese código y nombre. Si envías ambos, deben coincidir. grade admite null (pendiente, por defecto) o un número de 0 a 10. La combinación alumno, materia y periodo es única.

**Cuerpo de ejemplo**

```json
{
  "student_id": 1,
  "subject_id": 1,
  "term": "2027-1",
  "grade": 8.5
}
```

**Respuesta 201**

```json
{
  "id": 1,
  "student_id": 1,
  "subject_id": 1,
  "term": "2027-1",
  "period_id": 2,
  "period_code": "2027-1",
  "subject_code": "MAT",
  "subject_name": "Matemáticas",
  "grade": 8.5,
  "updated_at": "2026-11-25T04:03:14.846508Z"
}
```

### PATCH /api/enrollments/{enrollment_id}

- **Acceso** · admin y operador.
- **Errores** · 401, 403, 404 inscripción o periodo ausente, 409 duplicado, 422.

Admite grade, term y period_id, con la misma resolución del periodo. Para retirar la calificación, envía grade=null.

**Cuerpo de ejemplo**

```json
{
  "period_id": 1,
  "grade": 5.5
}
```

**Respuesta 200**

```json
{
  "id": 1,
  "student_id": 1,
  "subject_id": 1,
  "term": "2026-2",
  "period_id": 1,
  "period_code": "2026-2",
  "subject_code": "MAT",
  "subject_name": "Matemáticas",
  "grade": 5.5,
  "updated_at": "2026-11-25T04:03:14.970363Z"
}
```

### GET /api/students/{student_id}/enrollments

- **Acceso** · admin y operador para todos los alumnos. Tutor para sus alumnos asignados.
- **Errores** · 401, 404, 422 ID inválido.

Orden por ID descendente. period_code puede ser null en inscripciones históricas sin vínculo al catálogo.

**Cuerpo** · Sin cuerpo.

**Respuesta 200**

```json
[
  {
    "id": 1,
    "student_id": 1,
    "subject_id": 1,
    "term": "2026-2",
    "period_id": 1,
    "period_code": "2026-2",
    "subject_code": "MAT",
    "subject_name": "Matemáticas",
    "grade": 5.5,
    "updated_at": "2026-11-25T04:03:14.970363Z"
  }
]
```

### GET /api/students/{student_id}/alert

- **Acceso** · admin y operador para todos los alumnos. Tutor para sus alumnos asignados.
- **Errores** · 401, 404, 422 ID inválido.

RA_01 calcula baja, media, alta o sin_datos usando solo las calificaciones disponibles y la situación laboral. Las reglas se describen en el [contrato ML](contrato-ml.md).

**Cuerpo** · Sin cuerpo.

**Respuesta 200**

```json
{
  "student_id": 1,
  "level": "alta",
  "average": 5.5,
  "failed_subjects": 1,
  "evaluated_subjects": 1,
  "reasons": [
    "RA_01_R2: Promedio inferior a 6",
    "RA_01_R3: Jornada laboral de 30+ horas combinada con reprobación"
  ],
  "method": "Reglas orientativas; no es una predicción ML"
}
```

## Seguimiento · RF_14 / BD_08

### POST /api/students/{student_id}/followups

- **Acceso** · admin y tutor. El tutor solo puede indicar un alumno asignado.
- **Errores** · 401, 403, 404, 422.

Requiere date y note (texto no vacío). agreement es opcional y anulable. tutor_id identifica al usuario que registró el seguimiento, también cuando lo crea un administrador.

**Cuerpo de ejemplo**

```json
{
  "date": "2026-11-24",
  "note": "Se revisó el avance en Matemáticas.",
  "agreement": "Asistir a asesoría el viernes."
}
```

**Respuesta 201**

```json
{
  "date": "2026-11-24",
  "note": "Se revisó el avance en Matemáticas.",
  "agreement": "Asistir a asesoría el viernes.",
  "id": 1,
  "student_id": 1,
  "tutor_id": 1,
  "created_at": "2026-11-25T04:03:15.317864Z"
}
```

### GET /api/students/{student_id}/followups

- **Acceso** · admin y operador para todos los alumnos. Tutor para sus alumnos asignados.
- **Errores** · 401, 404, 422 ID inválido.

Orden por fecha de seguimiento descendente, luego por ID descendente.

**Cuerpo** · Sin cuerpo.

**Respuesta 200**

```json
[
  {
    "date": "2026-11-24",
    "note": "Se revisó el avance en Matemáticas.",
    "agreement": "Asistir a asesoría el viernes.",
    "id": 1,
    "student_id": 1,
    "tutor_id": 1,
    "created_at": "2026-11-25T04:03:15.317864Z"
  }
]
```

## Modelo, esquema e historial · RF_09 / RF_11 / CU_04

### GET /api/ml/model

- **Acceso** · admin, operador y tutor.
- **Errores** · 401, 503 modelo ausente.

Metadatos de solo lectura (BD_11). Un artefacto antiguo puede devolver null en metadatos ausentes.

**Cuerpo** · Sin cuerpo.

**Respuesta 200**

```json
{
  "model_name": "logreg",
  "version": "1.0.0",
  "task": "binaria",
  "feature_set": "temprano",
  "classes": [
    "Dropout",
    "No_Dropout"
  ],
  "metrics": {
    "accuracy": 0.8451977401129943,
    "balanced_accuracy": 0.8265918305172131,
    "f1_macro": 0.8238642224065571,
    "recall_dropout": 0.7746478873239436,
    "precision_dropout": 0.7508532423208191,
    "f1_dropout": 0.7625649913344887,
    "roc_auc": 0.9092592158608891,
    "brier_dropout": 0.10955127387938715,
    "confusion_matrix": [
      [
        220,
        64
      ],
      [
        73,
        528
      ]
    ],
    "classes": [
      "Dropout",
      "No_Dropout"
    ],
    "n_test": 885,
    "classification_report": {
      "Dropout": {
        "precision": 0.7508532423208191,
        "recall": 0.7746478873239436,
        "f1-score": 0.7625649913344887,
        "support": 284.0
      },
      "No_Dropout": {
        "precision": 0.8918918918918919,
        "recall": 0.8785357737104825,
        "f1-score": 0.8851634534786254,
        "support": 601.0
      },
      "accuracy": 0.8451977401129943,
      "macro avg": {
        "precision": 0.8213725671063554,
        "recall": 0.8265918305172131,
        "f1-score": 0.8238642224065571,
        "support": 885.0
      },
      "weighted avg": {
        "precision": 0.8466320314645644,
        "recall": 0.8451977401129943,
        "f1-score": 0.8458211221238968,
        "support": 885.0
      }
    }
  },
  "trained_at": "2026-11-03T03:06:23.769019+00:00",
  "dataset_sha256": "6bcfb6b3c826c4b8b9c7a99c063762748f6f462e24aabd26719ec2e55fed6135",
  "sklearn_version": "1.9.1"
}
```

### GET /api/ml/schema

- **Acceso** · admin, operador y tutor.
- **Errores** · 401, 503 esquema ausente.

Genera el formulario a partir de columns y conserva los nombres de variable como claves JSON.

**Cuerpo** · Sin cuerpo.

**Respuesta 200**

<details>
<summary>JSON completo del esquema de ejemplo</summary>

```json
{
  "id": "ML_02",
  "version": "1.0.0",
  "model_name": "logreg",
  "task": "binaria",
  "feature_set": "temprano",
  "classes": [
    "Dropout",
    "No_Dropout"
  ],
  "dataset_sha256": "6bcfb6b3c826c4b8b9c7a99c063762748f6f462e24aabd26719ec2e55fed6135",
  "nota": "Rangos y códigos observados en el CSV local; no son un mapeo de códigos UCI ni límites universales. numeric_columns del artefacto conserva tipos de transporte del backend; el pipeline trata los códigos nominales con codificación de categorías.",
  "columns": [
    {
      "nombre": "Marital status",
      "id": "VAR_01",
      "descripcion_es": "Estado civil",
      "tipo": "nominal",
      "momento": "inscripción",
      "min": 1.0,
      "max": 6.0,
      "ejemplo": 1.0,
      "valores_permitidos": [
        1,
        2,
        3,
        4,
        5,
        6
      ]
    },
    {
      "nombre": "Application mode",
      "id": "VAR_02",
      "descripcion_es": "Modalidad de acceso",
      "tipo": "nominal",
      "momento": "inscripción",
      "min": 1.0,
      "max": 18.0,
      "ejemplo": 8.0,
      "valores_permitidos": [
        1,
        2,
        3,
        4,
        5,
        6,
        7,
        8,
        9,
        10,
        11,
        12,
        13,
        14,
        15,
        16,
        17,
        18
      ]
    },
    {
      "nombre": "Application order",
      "id": "VAR_03",
      "descripcion_es": "Orden de preferencia de la solicitud",
      "tipo": "numérica",
      "momento": "inscripción",
      "min": 0.0,
      "max": 9.0,
      "ejemplo": 5.0
    },
    {
      "nombre": "Course",
      "id": "VAR_04",
      "descripcion_es": "Carrera cursada",
      "tipo": "nominal",
      "momento": "inscripción",
      "min": 1.0,
      "max": 17.0,
      "ejemplo": 2.0,
      "valores_permitidos": [
        1,
        2,
        3,
        4,
        5,
        6,
        7,
        8,
        9,
        10,
        11,
        12,
        13,
        14,
        15,
        16,
        17
      ]
    },
    {
      "nombre": "Daytime/evening attendance",
      "id": "VAR_05",
      "descripcion_es": "Asistencia diurna o nocturna",
      "tipo": "binaria",
      "momento": "inscripción",
      "min": 0.0,
      "max": 1.0,
      "ejemplo": 1.0
    },
    {
      "nombre": "Previous qualification",
      "id": "VAR_06",
      "descripcion_es": "Titulación previa",
      "tipo": "nominal",
      "momento": "inscripción",
      "min": 1.0,
      "max": 17.0,
      "ejemplo": 1.0,
      "valores_permitidos": [
        1,
        2,
        3,
        4,
        5,
        6,
        7,
        8,
        9,
        10,
        11,
        12,
        13,
        14,
        15,
        16,
        17
      ]
    },
    {
      "nombre": "Nacionality",
      "id": "VAR_07",
      "descripcion_es": "Nacionalidad",
      "tipo": "nominal",
      "momento": "inscripción",
      "min": 1.0,
      "max": 21.0,
      "ejemplo": 1.0,
      "valores_permitidos": [
        1,
        2,
        3,
        4,
        5,
        6,
        7,
        8,
        9,
        10,
        11,
        12,
        13,
        14,
        15,
        16,
        17,
        18,
        19,
        20,
        21
      ]
    },
    {
      "nombre": "Mother's qualification",
      "id": "VAR_08",
      "descripcion_es": "Escolaridad materna",
      "tipo": "nominal",
      "momento": "inscripción",
      "min": 1.0,
      "max": 29.0,
      "ejemplo": 13.0,
      "valores_permitidos": [
        1,
        2,
        3,
        4,
        5,
        6,
        7,
        8,
        9,
        10,
        11,
        12,
        13,
        14,
        15,
        16,
        17,
        18,
        19,
        20,
        21,
        22,
        23,
        24,
        25,
        26,
        27,
        28,
        29
      ]
    },
    {
      "nombre": "Father's qualification",
      "id": "VAR_09",
      "descripcion_es": "Escolaridad paterna",
      "tipo": "nominal",
      "momento": "inscripción",
      "min": 1.0,
      "max": 34.0,
      "ejemplo": 10.0,
      "valores_permitidos": [
        1,
        2,
        3,
        4,
        5,
        6,
        7,
        8,
        9,
        10,
        11,
        12,
        13,
        14,
        15,
        16,
        17,
        18,
        19,
        20,
        21,
        22,
        23,
        24,
        25,
        26,
        27,
        28,
        29,
        30,
        31,
        32,
        33,
        34
      ]
    },
    {
      "nombre": "Mother's occupation",
      "id": "VAR_10",
      "descripcion_es": "Ocupación materna",
      "tipo": "nominal",
      "momento": "inscripción",
      "min": 1.0,
      "max": 32.0,
      "ejemplo": 6.0,
      "valores_permitidos": [
        1,
        2,
        3,
        4,
        5,
        6,
        7,
        8,
        9,
        10,
        11,
        12,
        13,
        14,
        15,
        16,
        17,
        18,
        19,
        20,
        21,
        22,
        23,
        24,
        25,
        26,
        27,
        28,
        29,
        30,
        31,
        32
      ]
    },
    {
      "nombre": "Father's occupation",
      "id": "VAR_11",
      "descripcion_es": "Ocupación paterna",
      "tipo": "nominal",
      "momento": "inscripción",
      "min": 1.0,
      "max": 46.0,
      "ejemplo": 10.0,
      "valores_permitidos": [
        1,
        2,
        3,
        4,
        5,
        6,
        7,
        8,
        9,
        10,
        11,
        12,
        13,
        14,
        15,
        16,
        17,
        18,
        19,
        20,
        21,
        22,
        23,
        24,
        25,
        26,
        27,
        28,
        29,
        30,
        31,
        32,
        33,
        34,
        35,
        36,
        37,
        38,
        39,
        40,
        41,
        42,
        43,
        44,
        45,
        46
      ]
    },
    {
      "nombre": "Displaced",
      "id": "VAR_12",
      "descripcion_es": "Desplazamiento del domicilio habitual",
      "tipo": "binaria",
      "momento": "inscripción",
      "min": 0.0,
      "max": 1.0,
      "ejemplo": 1.0
    },
    {
      "nombre": "Educational special needs",
      "id": "VAR_13",
      "descripcion_es": "Necesidades educativas especiales",
      "tipo": "binaria",
      "momento": "inscripción",
      "min": 0.0,
      "max": 1.0,
      "ejemplo": 0.0
    },
    {
      "nombre": "Debtor",
      "id": "VAR_14",
      "descripcion_es": "Existencia de adeudos",
      "tipo": "binaria",
      "momento": "inscripción",
      "min": 0.0,
      "max": 1.0,
      "ejemplo": 0.0
    },
    {
      "nombre": "Tuition fees up to date",
      "id": "VAR_15",
      "descripcion_es": "Colegiatura al corriente",
      "tipo": "binaria",
      "momento": "inscripción",
      "min": 0.0,
      "max": 1.0,
      "ejemplo": 1.0
    },
    {
      "nombre": "Gender",
      "id": "VAR_16",
      "descripcion_es": "Género registrado",
      "tipo": "binaria",
      "momento": "inscripción",
      "min": 0.0,
      "max": 1.0,
      "ejemplo": 1.0
    },
    {
      "nombre": "Scholarship holder",
      "id": "VAR_17",
      "descripcion_es": "Beneficiario de beca",
      "tipo": "binaria",
      "momento": "inscripción",
      "min": 0.0,
      "max": 1.0,
      "ejemplo": 0.0
    },
    {
      "nombre": "Age at enrollment",
      "id": "VAR_18",
      "descripcion_es": "Edad al inscribirse",
      "tipo": "numérica",
      "momento": "inscripción",
      "min": 17.0,
      "max": 70.0,
      "ejemplo": 20.0
    },
    {
      "nombre": "International",
      "id": "VAR_19",
      "descripcion_es": "Condición de estudiante internacional",
      "tipo": "binaria",
      "momento": "inscripción",
      "min": 0.0,
      "max": 1.0,
      "ejemplo": 0.0
    },
    {
      "nombre": "Curricular units 1st sem (credited)",
      "id": "VAR_20",
      "descripcion_es": "Unidades reconocidas, primer semestre",
      "tipo": "numérica",
      "momento": "1er semestre",
      "min": 0.0,
      "max": 20.0,
      "ejemplo": 0.0
    },
    {
      "nombre": "Curricular units 1st sem (enrolled)",
      "id": "VAR_21",
      "descripcion_es": "Unidades inscritas, primer semestre",
      "tipo": "numérica",
      "momento": "1er semestre",
      "min": 0.0,
      "max": 26.0,
      "ejemplo": 0.0
    },
    {
      "nombre": "Curricular units 1st sem (evaluations)",
      "id": "VAR_22",
      "descripcion_es": "Evaluaciones realizadas, primer semestre",
      "tipo": "numérica",
      "momento": "1er semestre",
      "min": 0.0,
      "max": 45.0,
      "ejemplo": 0.0
    },
    {
      "nombre": "Curricular units 1st sem (approved)",
      "id": "VAR_23",
      "descripcion_es": "Unidades aprobadas, primer semestre",
      "tipo": "numérica",
      "momento": "1er semestre",
      "min": 0.0,
      "max": 26.0,
      "ejemplo": 0.0
    },
    {
      "nombre": "Curricular units 1st sem (grade)",
      "id": "VAR_24",
      "descripcion_es": "Promedio de unidades aprobadas, primer semestre",
      "tipo": "numérica",
      "momento": "1er semestre",
      "min": 0.0,
      "max": 18.875,
      "ejemplo": 0.0
    },
    {
      "nombre": "Curricular units 1st sem (without evaluations)",
      "id": "VAR_25",
      "descripcion_es": "Unidades sin evaluación, primer semestre",
      "tipo": "numérica",
      "momento": "1er semestre",
      "min": 0.0,
      "max": 12.0,
      "ejemplo": 0.0
    },
    {
      "nombre": "Unemployment rate",
      "id": "VAR_32",
      "descripcion_es": "Tasa de desempleo",
      "tipo": "numérica",
      "momento": "macroeconómica",
      "min": 7.6,
      "max": 16.2,
      "ejemplo": 10.8
    },
    {
      "nombre": "Inflation rate",
      "id": "VAR_33",
      "descripcion_es": "Tasa de inflación",
      "tipo": "numérica",
      "momento": "macroeconómica",
      "min": -0.8,
      "max": 3.7,
      "ejemplo": 1.4
    },
    {
      "nombre": "GDP",
      "id": "VAR_34",
      "descripcion_es": "Variación del producto interno bruto",
      "tipo": "numérica",
      "momento": "macroeconómica",
      "min": -4.06,
      "max": 3.51,
      "ejemplo": 1.74
    }
  ]
}
```

</details>

### POST /api/ml/predict

- **Acceso** · admin y tutor. El tutor solo puede indicar un alumno asignado.
- **Errores** · 401, 403, 404 alumno ausente o fuera de alcance, 422 campos inválidos, 503 modelo o esquema no disponible o incompatible.

features requiere todas las variables del esquema y números JSON válidos. student_id es opcional y anulable. Cada éxito guarda la versión, la fecha UTC, la clase, la probabilidad de Dropout, la categoría, las variables y el usuario. Cuando falla la inferencia no se crea registro. El detalle de la validación PT_08 se documenta en el [contrato ML](contrato-ml.md).

**Cuerpo de ejemplo**

```json
{
  "student_id": 1,
  "features": {
    "Marital status": 1.0,
    "Application mode": 1.0,
    "Application order": 1.0,
    "Course": 5.0,
    "Daytime/evening attendance": 1.0,
    "Previous qualification": 1.0,
    "Nacionality": 1.0,
    "Mother's qualification": 1.0,
    "Father's qualification": 27.0,
    "Mother's occupation": 6.0,
    "Father's occupation": 10.0,
    "Displaced": 1.0,
    "Educational special needs": 0.0,
    "Debtor": 1.0,
    "Tuition fees up to date": 1.0,
    "Gender": 0.0,
    "Scholarship holder": 0.0,
    "Age at enrollment": 21.0,
    "International": 0.0,
    "Curricular units 1st sem (credited)": 0.0,
    "Curricular units 1st sem (enrolled)": 6.0,
    "Curricular units 1st sem (evaluations)": 9.0,
    "Curricular units 1st sem (approved)": 5.0,
    "Curricular units 1st sem (grade)": 11.4,
    "Curricular units 1st sem (without evaluations)": 0.0,
    "Unemployment rate": 12.7,
    "Inflation rate": 3.7,
    "GDP": -1.7
  }
}
```

**Respuesta 200**

```json
{
  "clase_predicha": "No_Dropout",
  "probabilidades": {
    "Dropout": 0.4051158285182902,
    "No_Dropout": 0.5948841714817098
  },
  "probabilidad_desercion": 0.4051158285182902,
  "categoria_orientativa": "media",
  "modelo": {
    "model_name": "logreg",
    "version": "1.0.0",
    "task": "binaria"
  },
  "fecha_prediccion": "2026-11-25T04:03:15.825504+00:00",
  "nota": "RN_01: Es una estimación estadística, no un diagnóstico. RN_05: Es independiente de las alertas por reglas RA_01; requiere revisión humana.",
  "predicted_class": "No_Dropout",
  "probabilities": {
    "Dropout": 0.4051158285182902,
    "No_Dropout": 0.5948841714817098
  },
  "model_name": "logreg",
  "note": "RN_01: Es una estimación estadística, no un diagnóstico. RN_05: Es independiente de las alertas por reglas RA_01; requiere revisión humana.",
  "prediction_id": 1,
  "created_at": "2026-11-25T04:03:15.825504+00:00"
}
```

### GET /api/ml/predictions

- **Acceso** · admin y tutor. El tutor solo puede indicar un alumno asignado.
- **Errores** · 401, 403, 404 alumno ausente o fuera de alcance, 422.

student_id es opcional. El administrador ve también predicciones sin alumno. El tutor solo ve las asociadas a sus alumnos actuales. Orden descendente por fecha e ID.

Ejemplo de consulta `/api/ml/predictions?student_id=1&skip=0&limit=10`.

**Cuerpo** · Sin cuerpo.

**Respuesta 200**

```json
[
  {
    "id": 1,
    "student_id": 1,
    "user_id": 1,
    "model_version": "1.0.0",
    "task": "binaria",
    "predicted_class": "No_Dropout",
    "probability_dropout": 0.4051158285182902,
    "risk_category": "media",
    "created_at": "2026-11-25T04:03:15.825504Z",
    "features": {
      "Marital status": 1.0,
      "Application mode": 1.0,
      "Application order": 1.0,
      "Course": 5.0,
      "Daytime/evening attendance": 1.0,
      "Previous qualification": 1.0,
      "Nacionality": 1.0,
      "Mother's qualification": 1.0,
      "Father's qualification": 27.0,
      "Mother's occupation": 6.0,
      "Father's occupation": 10.0,
      "Displaced": 1.0,
      "Educational special needs": 0.0,
      "Debtor": 1.0,
      "Tuition fees up to date": 1.0,
      "Gender": 0.0,
      "Scholarship holder": 0.0,
      "Age at enrollment": 21.0,
      "International": 0.0,
      "Curricular units 1st sem (credited)": 0.0,
      "Curricular units 1st sem (enrolled)": 6.0,
      "Curricular units 1st sem (evaluations)": 9.0,
      "Curricular units 1st sem (approved)": 5.0,
      "Curricular units 1st sem (grade)": 11.4,
      "Curricular units 1st sem (without evaluations)": 0.0,
      "Unemployment rate": 12.7,
      "Inflation rate": 3.7,
      "GDP": -1.7
    }
  }
]
```

### GET /api/students/{student_id}/predictions

- **Acceso** · admin y tutor. El tutor solo puede indicar un alumno asignado.
- **Errores** · 401, 403, 404, 422.

Mismo formato y orden que el historial general; acepta skip y limit.

**Cuerpo** · Sin cuerpo.

**Respuesta 200**

```json
[
  {
    "id": 1,
    "student_id": 1,
    "user_id": 1,
    "model_version": "1.0.0",
    "task": "binaria",
    "predicted_class": "No_Dropout",
    "probability_dropout": 0.4051158285182902,
    "risk_category": "media",
    "created_at": "2026-11-25T04:03:15.825504Z",
    "features": {
      "Marital status": 1.0,
      "Application mode": 1.0,
      "Application order": 1.0,
      "Course": 5.0,
      "Daytime/evening attendance": 1.0,
      "Previous qualification": 1.0,
      "Nacionality": 1.0,
      "Mother's qualification": 1.0,
      "Father's qualification": 27.0,
      "Mother's occupation": 6.0,
      "Father's occupation": 10.0,
      "Displaced": 1.0,
      "Educational special needs": 0.0,
      "Debtor": 1.0,
      "Tuition fees up to date": 1.0,
      "Gender": 0.0,
      "Scholarship holder": 0.0,
      "Age at enrollment": 21.0,
      "International": 0.0,
      "Curricular units 1st sem (credited)": 0.0,
      "Curricular units 1st sem (enrolled)": 6.0,
      "Curricular units 1st sem (evaluations)": 9.0,
      "Curricular units 1st sem (approved)": 5.0,
      "Curricular units 1st sem (grade)": 11.4,
      "Curricular units 1st sem (without evaluations)": 0.0,
      "Unemployment rate": 12.7,
      "Inflation rate": 3.7,
      "GDP": -1.7
    }
  }
]
```

## Indicadores · RF_12 / CU_06

### GET /api/dashboard

- **Acceso** · admin y operador para todos los alumnos. Tutor para sus alumnos asignados.
- **Errores** · 401.

students incluye todos los estados. subjects cuenta el catálogo completo para admin y operador, y materias distintas inscritas por alumnos asignados para tutor. Los indicadores de notas incluyen a los inactivos, omiten notas nulas y usan 6 como mínimo aprobatorio. average_grade vale null sin notas y se redondea a dos decimales. students_by_career usa el nombre del catálogo o, si falta, program. alerts_by_level evalúa exclusivamente alumnos activos. predictions incluye las filas sin alumno únicamente en el alcance global. last_predictions devuelve hasta cinco resúmenes ordenados por fecha e ID descendentes, sin features.

**Cuerpo** · Sin cuerpo.

**Respuesta 200**

```json
{
  "students": 1,
  "subjects": 1,
  "enrollments": 1,
  "active_students": 1,
  "inactive_students": 0,
  "students_by_status": {
    "activo": 1,
    "baja_temporal": 0,
    "baja_definitiva": 0,
    "egresado": 0
  },
  "students_by_career": [
    {
      "career": "Ingeniería en Sistemas",
      "count": 1
    }
  ],
  "average_grade": 5.5,
  "failed_enrollments": 1,
  "alerts_by_level": {
    "baja": 0,
    "media": 0,
    "alta": 1,
    "sin_datos": 0
  },
  "predictions": 1,
  "predictions_by_category": {
    "baja": 0,
    "media": 1,
    "alta": 0
  },
  "last_predictions": [
    {
      "id": 1,
      "student_id": 1,
      "user_id": 1,
      "model_version": "1.0.0",
      "task": "binaria",
      "predicted_class": "No_Dropout",
      "probability_dropout": 0.4051158285182902,
      "risk_category": "media",
      "created_at": "2026-11-25T04:03:15.825504Z"
    }
  ]
}
```

## Eliminación de inscripción · RF_05

### DELETE /api/enrollments/{enrollment_id}

- **Acceso** · admin y operador.
- **Errores** · 401, 403, 404, 422 ID inválido.

Elimina la inscripción y su nota. La bitácora registra baja.

**Cuerpo** · Sin cuerpo.

**Respuesta 204** · Sin cuerpo.

## Bitácora · RNF_05 / BD_12

### GET /api/audit

- **Acceso** · admin.
- **Errores** · 401, 403, 422.

entity y user_id son filtros opcionales por igualdad. Orden por ID descendente. entity usa el nombre de la tabla. action puede ser crear, editar, baja, reactivar, importar, predecir o login. detail puede ser un texto, un objeto o null.

Ejemplo de consulta `/api/audit?entity=enrollments&user_id=1&skip=0&limit=1`.

**Cuerpo** · Sin cuerpo.

**Respuesta 200**

```json
[
  {
    "id": 21,
    "user_id": 1,
    "action": "baja",
    "entity": "enrollments",
    "entity_id": 1,
    "detail": {
      "student_id": 1
    },
    "created_at": "2026-11-25T04:03:16.315760Z"
  }
]
```

## Importación CSV · RF_07 / RN_04 / RNF_03 / RNF_05

Las tres rutas de esta sección están disponibles para administradores. Una sesión inválida devuelve 401 y un rol sin acceso devuelve 403.

### POST /api/import/students

Recibe `multipart/form-data` con el archivo en el campo `file`. La consulta opcional `dry_run` vale `false` por defecto. Importa expedientes por matrícula y permite actualizar los existentes.

### POST /api/import/enrollments

Usa el mismo cuerpo y parámetro `dry_run`. Identifica cada inscripción por alumno, materia y código de periodo. Crea los periodos faltantes y actualiza las calificaciones de las inscripciones existentes.

**Respuesta 200 para ambas importaciones**

```json
{
  "dry_run": false,
  "applied": false,
  "total_rows": 2,
  "created": 1,
  "updated": 0,
  "errors": [{"row": 3, "field": "semester", "message": "Valor inválido"}]
}
```

`created` y `updated` cuentan las operaciones de las filas válidas, incluso en simulaciones o lotes rechazados. `applied` confirma que se guardó el lote completo. Si el archivo está vacío de registros, tiene errores por fila o se procesa con `dry_run=true`, `applied` vale `false`. Los lotes confirmados generan una entrada `importar` con el resumen y el ID de entidad `0`, que representa el lote.

Las rutas devuelven 413 si el archivo supera 2 MiB (2,097,152 bytes) o 5,000 registros de datos, 422 si faltan columnas obligatorias o la codificación, el encabezado o los parámetros son inválidos, y 409 si surge un conflicto de integridad al guardar. Para columnas faltantes se devuelve `{"detail":{"message":"Faltan columnas obligatorias","missing_columns":["full_name","semester"]}}`. Las columnas y ejemplos están documentados en [Formato de importación CSV](formato-importacion.md).

### GET /api/import/templates/{kind}

`kind` admite `students` o `enrollments`. Devuelve 200 con un archivo `text/csv`, `Content-Disposition: attachment`, encabezados y dos filas de ejemplo. Un tipo inválido devuelve 422.

## Reportes · RF_13 / RN_04

Los administradores tienen acceso global. Los tutores tienen acceso a los alumnos que tienen asignados al momento de consultar. Las rutas devuelven 401 por sesión inválida y 403 para operadores. Las descargas CSV usan coma, UTF-8 con BOM y `Content-Disposition: attachment`.

### GET /api/reports/summary

Acepta `career_id` y `period` como filtros opcionales. El código `period` aplica a las inscripciones usadas para calcular calificaciones, reprobación y alertas. El filtro de carrera aplica a los alumnos y a sus inscripciones, alertas y predicciones vinculadas.

`failure_rate` es `100 × failed_enrollments / failure_rate_denominator`. El denominador es `evaluated_enrollments`, que cuenta las inscripciones con una nota registrada. Reprueban las notas menores que 6. Las alertas se calculan con RA_01 solo para alumnos activos. `by_career` agrupa por nombre de carrera del catálogo o por `program` cuando el alumno carece de carrera registrada. Promedios de notas y tasas se redondean a dos decimales.

El promedio de probabilidad de Dropout está en escala de 0 a 1 y usa todas las predicciones del alcance, incluidas las predicciones sin alumno cuando el administrador consulta sin filtro de carrera. Los indicadores numéricos devuelven cero en ausencia de registros y `by_career` devuelve una lista vacía si faltan alumnos.

**Respuesta 200**

```json
{
  "students": 2,
  "active_students": 2,
  "students_by_status": {"activo": 2, "baja_temporal": 0, "baja_definitiva": 0, "egresado": 0},
  "evaluated_enrollments": 3,
  "failed_enrollments": 2,
  "average_grade": 6.33,
  "failure_rate": 66.67,
  "failure_rate_denominator": 3,
  "alerts_by_level": {"baja": 1, "media": 0, "alta": 1, "sin_datos": 0},
  "predictions": 1,
  "predictions_by_category": {"baja": 0, "media": 0, "alta": 1},
  "average_probability_dropout": 0.82,
  "by_career": [
    {"career": "Sistemas", "students": 2, "average_grade": 6.33, "failure_rate": 66.67, "alerts_alta": 1}
  ]
}
```

### GET /api/reports/students y GET /api/reports/students.csv

Aceptan `career_id`, `status` y `alert_level` como filtros opcionales y combinables. `status` admite `activo`, `baja_temporal`, `baja_definitiva`, `egresado`. `alert_level` admite `baja`, `media`, `alta`, `sin_datos`. Un filtro inválido devuelve 422.

Las dos variantes ordenan por matrícula. Las claves de la lista JSON y los encabezados del CSV son:

```text
enrollment_number,full_name,career,semester,status,employed,work_hours_weekly,average_grade,failed_subjects,alert_level,probability_dropout,risk_category,prediction_at
```

Los valores académicos y la alerta RA_01 usan todas las inscripciones evaluadas del alumno. Sin notas, el promedio y las reprobadas valen cero y el nivel vale `sin_datos`. La última predicción se determina por fecha descendente y, en caso de empate, por ID descendente. Los tres campos de predicción valen `null` en JSON y quedan vacíos en CSV si el alumno carece de predicciones. Una consulta sin coincidencias devuelve una lista vacía en JSON o solo los encabezados en CSV.

### GET /api/reports/predictions.csv

Acepta `student_id`, `from` y `to` como filtros opcionales. Los límites son inclusivos y admiten fechas `YYYY-MM-DD` o instantes ISO 8601. Una fecha cubre el día completo en UTC cuando se usa en ambos límites. Los instantes sin zona se interpretan en UTC. Un rango invertido o inválido devuelve 422.

Ordena por fecha e ID descendentes. Para un alumno sin predicciones visibles devuelve solo los encabezados. Sin filtro de alumno, un administrador también recibe el historial de predicciones sin alumno asociado. Los campos exportados son:

```text
id,student_id,user_id,model_version,task,predicted_class,probability_dropout,risk_category,created_at
```
