# INT_03 · Contrato ML de SIPDE para INT_02 e INT_04

Responsable: INT_03. Requisitos: RF_08, RF_09, RF_10, RF_11, RF_15, RNF_06; reglas RN_01, RN_03, RN_04 y RN_05. Evidencia automatizada: PT_08, PT_09, PT_10, `test_ml_api.py` (PT_07 parcial) y `test_risk.py` (RA_01).

## RF_09 · Endpoints y autorización vigente

Todas las rutas usan `Authorization: Bearer <JWT>` emitido por `POST /api/auth/login`, con la misma dependencia `current_user` del predictor existente. Actualmente se exige usuario activo; **no existe filtrado por rol** en estas rutas. Se probó el rol `admin` creado por el lifespan. La restricción por rol de RN_04 queda pendiente de INT_02, incluida la matriz de roles autorizados; INT_04 no debe asumir que ocultar controles equivale a autorización de servidor.

| ID | Método | Ruta | Auth/rol actual | Entrada | Salida 200 | Errores |
|---|---|---|---|---|---|---|
| RF_09_INFO | GET | `/api/ml/model` | JWT, usuario activo; admin probado | Sin cuerpo | Metadatos, versión, clases y métricas; ejemplo real RF_09_E1 | 401/403 de auth; 503 sin modelo |
| RF_09_SCHEMA | GET | `/api/ml/schema` | Igual que predict | Sin cuerpo | Esquema junto al modelo; extracto real RF_09_E2 | 401/403 de auth; 503 sin esquema |
| RF_09_PREDICT | POST | `/api/ml/predict` | Igual que arriba; RN_04 pendiente | `{"features": {...}}`, según RF_09_E3 | Clase, probabilidades, categoría, versión, UTC y nota; RF_09_E4 | 401/403 de auth; 422 entrada inválida; 503 sin modelo/esquema |

El horizonte de producción se fija en ML_00 antes de comparar: `logreg / temprano / binaria` (EXP_02), disponible al cierre del primer semestre. El conjunto completo es una referencia de techo (EXP_04) con proximidad al objetivo por variables del segundo semestre; sus resultados y diferencias frente a EXP_02 se generan en ML_02. El modelo binario devuelve `Dropout` y `No_Dropout`; este último agrupa `Enrolled` y `Graduate`, sin garantizar graduación.

## RF_09 · Ejemplos HTTP reales

Captura: `2026-11-03T03:12:05.822347+00:00`. Modelo `1.0.0`. Se ejecutaron los endpoints con FastAPI TestClient, login real y BD SQLite temporal. La entrada es `ACE_03_Dropout`, una fila real de test exportada por ACE_03; no hay valores ni métricas fabricados. Los timestamps de futuras ejecuciones cambian.

### RF_09_E1 · GET /api/ml/model, respuesta completa

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

Las llaves de metadatos ausentes en artefactos antiguos se devuelven como `null`, sin inferir versiones ni fechas. Se cargan exclusivamente joblib locales y confiables. La caché se identifica por ruta resuelta, mtime en nanosegundos y tamaño; un reentrenamiento invalida la carga anterior al cambiar el archivo. `MODEL_PATH` relativo se resuelve desde la raíz del repositorio.

### RF_09_E2 · GET /api/ml/schema, extracto real

Se muestra la cabecera y la primera columna de la respuesta capturada. La respuesta completa contiene todas las columnas del modelo y está versionada en [feature_schema.json](../ml/artifacts/feature_schema.json).

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
    }
  ]
}
```

### RF_09_E3 · POST /api/ml/predict, entrada completa real

```json
{
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

### RF_09_E4 · Respuesta completa real de predict

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
  "fecha_prediccion": "2026-11-03T03:12:06.146277+00:00",
  "nota": "RN_01: Es una estimación estadística, no un diagnóstico. RN_05: Es independiente de las alertas por reglas RA_01; requiere revisión humana.",
  "predicted_class": "No_Dropout",
  "probabilities": {
    "Dropout": 0.4051158285182902,
    "No_Dropout": 0.5948841714817098
  },
  "model_name": "logreg",
  "note": "RN_01: Es una estimación estadística, no un diagnóstico. RN_05: Es independiente de las alertas por reglas RA_01; requiere revisión humana."
}
```

`probabilidades` se alinea con `model.classes_`, nunca con posiciones supuestas (auditoría EXPOESCOM). Se conserva la precisión del estimador; las probabilidades suman 1 salvo error numérico. `probabilidad_desercion` es exactamente la entrada `Dropout` de ese mapa. `predicted_class`, `probabilities`, `model_name` y `note` mantienen compatibilidad. `fecha_prediccion` es ISO 8601 con UTC explícito.

## PT_08 · Integridad de entrada y errores

Los nombres de columna aceptan BOM U+FEFF y espacios exteriores. Se rechazan duplicados después de normalizar, faltantes y sobrantes. Los valores deben ser números JSON finitos: no se aceptan booleanos, nulos ni cadenas numéricas. Para nominales se valida `valores_permitidos`; para numéricas e indicadores binarios se valida el intervalo inclusivo `[min, max]`. Estos límites y códigos describen el CSV local; no son límites universales. No se agregan valores por defecto ni se infieren variables ausentes. El rechazo 422 enumera cada campo con `campo`, `problema`, `esperado` y `recibido`.

| ID | Estado | Condición y tratamiento para INT_04 |
|---|---|---|
| RF_09_ERR_AUTH | 401/403 | Sin JWT, JWT inválido o usuario inactivo: volver a autenticar. La versión instalada devolvió 401 sin token; versiones de HTTPBearer pueden devolver 403. Mensajes de la dependencia de auth pueden estar en inglés. |
| RN_04_ERR_ROL | 403 | Reservado para el control de rol de INT_02; actualmente no hay rechazo por rol. La forma de `detail` de RN_04 se debe acordar al implementarlo. |
| PT_08_ERR_INPUT | 422 | Corregir los campos indicados, sin enviar nuevamente el formulario sin cambios. |
| RF_09_ERR_MODEL | 503 | Falta modelo o esquema; entrenar desde la raíz. Un modelo y esquema con columnas incompatibles también devuelve 503. |

RF_09_ERR_AUTH, JWT inválido (401 real):

```json
{
  "detail": "Sesión inválida"
}
```

RF_09_ERR_AUTH, sin token (estado observado 401):

```json
{
  "detail": "Not authenticated"
}
```

RN_04_ERR_ROL, forma **propuesta** para INT_02 (403 pendiente, no es una respuesta observada del servicio actual):

```json
{"detail": "RN_04: Rol sin permiso para consultar predicciones ML."}
```

PT_08_ERR_INPUT, falta Course (422 real):

```json
{
  "detail": {
    "mensaje": "PT_08: Entrada inválida para el esquema ML.",
    "errores": [
      {
        "campo": "Course",
        "problema": "PT_08: Campo faltante",
        "esperado": "Valor numérico obligatorio",
        "recibido": null
      }
    ]
  }
}
```

RF_09_ERR_MODEL, artefacto ausente (503 real):

```json
{
  "detail": "INT_03: Modelo no entrenado. Desde la raíz ejecuta: python ml/training/train.py"
}
```

## RN_03 / RF_11 · Persistencia pendiente de INT_02

INT_03 no escribe en BD. El cuerpo vigente solo contiene `features`: no acepta ni vincula `student_id`, y no registra usuario. INT_02 debe definir la ampliación compatible del cuerpo o una ruta asociada al estudiante, validar su existencia y autorizar por rol en servidor (RN_04) antes de persistir. Se debe guardar la respuesta efectivamente emitida, sin volver a predecir para el historial.

| Campo requerido en prediction_logs | Situación exacta del modelo PredictionLog actual | Trabajo pendiente INT_02 |
|---|---|---|
| `student_id` | Ya existe, FK nullable a students | Exigir asociación válida según el flujo acordado |
| `model_version` | No existe | Añadir y guardar `modelo.version` |
| `probabilidad_desercion` | No existe | Añadir y guardar número emitido |
| `clase_predicha` | No existe | Añadir; `result` no tiene esta semántica explícita |
| `probabilidades` (JSON) | No existe | Añadir mapa completo de probabilidades |
| `fecha` | No existe con ese nombre | Acordar migración o mapeo de `created_at`; conservar fecha UTC de la predicción |
| `usuario` | No existe | Añadir referencia al usuario autenticado para auditoría RN_03 |

Las columnas actuales son exactamente `id`, `student_id`, `kind`, `result`, `created_at`. Faltan por nombre **`model_version`, `probabilidad_desercion`, `clase_predicha`, `probabilidades`, `fecha`, `usuario`**. `created_at` ya proporciona un campo temporal, pero necesita un mapeo explícito si se reutiliza como fecha; `kind` y `result` no almacenan por sí solos el contrato requerido. Este alcance no modifica `models.py`, esquemas de BD, auth ni roles.

## INT_04 · Formulario, demo y presentación (ACE_03 / RN_01 / RN_05)

1. Obtener `/api/ml/schema` con JWT y recorrer `columns` en su orden. Conservar `nombre` como clave exacta para enviar y `id` VAR_xx como identificador de control. Usar `descripcion_es` como etiqueta y `momento` como ayuda de disponibilidad.
2. Para `tipo=nominal`, construir un selector con **solo** `valores_permitidos` (códigos numéricos observados). No asignarles significados UCI sin mapeo verificado. Para `numérica`, usar control numérico con `min`/`max` inclusivos y permitir decimales. Para `binaria`, usar 0/1. Convertir valores a números JSON antes de enviar; no remitir `Target`, IDs de UI ni metadatos dentro de `features`.
3. Usar [ejemplos_prediccion.json](../ml/artifacts/ejemplos_prediccion.json) para la demo: tres filas reales de test, una por `clase_real` original. Copiar **solo** `features` al formulario. `indice_csv` permite verificar la fila y `clase_objetivo` documenta la agrupación binaria. No usar la clase real como variable del modelo.
4. Mostrar `probabilidad_desercion` como porcentaje estimado y la `categoria_orientativa` en una tarjeta ML con versión y fecha. Los cortes son `ML_UMBRAL_MEDIO=0.33` y `ML_UMBRAL_ALTO=0.66`: baja si p < medio, media si medio ≤ p < alto, alta si p ≥ alto. Son orientativos, configurables vía settings/variables de entorno y no provienen de calibración ni selección con test. La clase predicha del estimador no tiene por qué coincidir con esos cortes.
5. Mostrar la respuesta de RA_01 en otra tarjeta, identificada como alerta por reglas. No promediar ni fusionar sus niveles con la probabilidad ML (RN_05). Mostrar `nota` completa: estimación estadística, no diagnóstico (RN_01), independiente de reglas y con revisión humana. No traducir `No_Dropout` como garantía de graduación.
6. Tratar 422 por campo, 401/403 como autenticación o autorización y 503 como modelo no disponible. No sustituir errores por una probabilidad cero ni por un ejemplo de demo.

## RA_01 · RF_10: reglas académicas compatibles

Se conservan las llaves `level`, `average`, `failed_subjects`, `evaluated_subjects`, `reasons`, `method`. Las razones siguen siendo cadenas, ahora prefijadas con su ID. `method` conserva exactamente `Reglas orientativas; no es una predicción ML`.

| ID | Condición | Efecto |
|---|---|---|
| RA_01_MIN_APROBATORIA | Nota < 6 | Cuenta como reprobada; exactamente 6.0 aprueba |
| RA_01_R1 | Reprobadas ≥ `RA_01_MAX_REPROBADAS=2` | Razón: dos o más materias reprobadas |
| RA_01_R2 | Promedio redondeado a dos decimales < `RA_01_MIN_APROBATORIA=6` | Razón: promedio inferior a 6 |
| RA_01_R3 | Trabaja y horas semanales ≥ `RA_01_HORAS_TRABAJO=30` y al menos una reprobada | Razón: jornada laboral con reprobación; exactamente 30 h activa la regla |
| RA_01_N0 | Sin calificaciones no nulas | Nivel `sin_datos`, promedio null, sin razones |
| RA_01_N1 | Dos o más razones | Nivel `alta` |
| RA_01_N2 | Una razón o exactamente una reprobada | Nivel `media` |
| RA_01_N3 | Resto de casos con calificaciones | Nivel `baja` |

El promedio conserva el redondeo del backend existente. Los nulos se excluyen del conteo y del promedio. Horas de trabajo y calificaciones por materia pertenecen a RA_01; no se inventan como predictores del CSV histórico.

## RF_08 / RF_15 / RNF_06 · Reentrenamiento y versionado

Desde la raíz, sin añadir dependencias:

```bash
source backend/.venv/bin/activate
python ml/eda/audit_dataset.py
python ml/training/experiments.py
python ml/training/train.py --modelo logreg --conjunto temprano --tarea binaria --version 1.0.1
python ml/training/evaluate.py
cd backend && pytest -q
```

RF_15: volver a ejecutar experiments cuando cambie su código, el protocolo, los datos o la comparación; para repetir solo el candidato bastan train y evaluate. Elegir versión nueva para cada entrega del modelo. `train.py` ajusta solo en train y regenera juntos `dropout_model.joblib`, `feature_schema.json`, `model_card.json` y `ejemplos_prediccion.json`. El joblib es local y no versionado; los JSON y reportes se revisan y versionan mediante el flujo del equipo. No incluir rutas absolutas locales ni cambiar el CSV de esta tarea. `dataset_path` se registra relativo al repo; evaluate resuelve esa ruta desde la raíz independientemente del directorio de invocación. `--csv` permite otra ubicación y exige el mismo SHA-256 al verificar.

PT_10: evaluate compara métricas, matriz y reportes con tolerancia absoluta 1e-9, SHA-256 y semilla; termina con error si difieren. Dos entrenamientos con la misma semilla deben dar métricas idénticas; la fecha puede variar. PT_09 fija mínimos F1-macro y recall Dropout en constantes del test, redondeadas hacia abajo a 0.05 tras una ejecución observada, y verifica la matriz. Las pruebas oficiales entrenan el candidato en un directorio temporal por sesión en menos de 60 s, no usan el joblib local ni importan matplotlib. Los chequeos rápidos propios de `ml/tests/` no duplican los IDs PT.

Si cambia el esquema: actualizar el conjunto/diccionario y protocolo aplicable en ML_00, entrenar una nueva versión, regenerar el esquema y ejemplos desde datos reales, ejecutar PT_08–PT_10 y test_ml_api, y coordinar el cambio con INT_02/INT_04. Publicar el joblib y sus JSON del mismo entrenamiento como una unidad durante una ventana sin inferencias; después verificar `/api/ml/model` y `/api/ml/schema`. El servicio recarga el artefacto por mtime; no necesita reiniciar para un reemplazo válido. INT_04 debe volver a obtener el esquema y reconstruir controles al cambiar la versión; no enviar formularios guardados con columnas antiguas.
