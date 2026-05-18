# Clinical Whisper

Aplicacion local orientada a personal medico para registrar consultas clinicas a partir de conversaciones habladas, sin depender de servicios externos.

## Objetivo del proyecto

Construir una herramienta 100% local que permita:

- Capturar audio entre paciente y profesional.
- Transcribir el audio con Whisper.
- Procesar la transcripcion con modelos open source ejecutados en Ollama.
- Generar automaticamente un resumen estructurado de la consulta.
- Guardar cada sesion en un historial local por paciente.
- Revisar y editar sesiones ya guardadas desde la propia interfaz web.

## Estado actual

### Implementado

- Backend Flask local en `app.py`.
- Interfaz principal en `template/main.html` para:
  - introducir datos del paciente,
  - grabar audio desde navegador,
  - transcribir con Whisper,
  - corregir la transcripcion,
  - seleccionar modelo Ollama,
  - generar resumen, motivo de consulta y puntos clave.
- Modulo `src/speech/` para transcripcion local.
- Modulo `src/summarize/` para resumen clinico con Ollama:
  - normalizacion de datos,
  - construccion de prompts,
  - troceado de transcripciones largas,
  - resumen por bloques,
  - resumen final estructurado,
  - persistencia local en JSON.
- Persistencia local en `data/patients/`, agrupando sesiones por paciente.
- Vista de historiales en `template/history.html` para:
  - listar pacientes guardados,
  - listar sesiones de cada paciente,
  - abrir una sesion concreta,
  - lanzar una nueva consulta para un paciente ya existente con datos precargados,
  - borrar un paciente y todas sus sesiones,
  - editar transcripcion y datos clinicos,
  - volver a llamar al modelo para regenerar el resumen,
  - guardar cambios sobre la sesion existente.
- API interna para historiales:
  - `GET /api/patients`
  - `GET /api/patients/<patient_id>`
  - `GET /api/patients/<patient_id>/sessions/<session_id>`
  - `POST /api/sessions/resummarize`
  - `PUT /api/patients/<patient_id>/sessions/<session_id>`
  - `DELETE /api/patients/<patient_id>`
- Pruebas automatizadas con `unittest` para:
  - normalizacion,
  - chunking,
  - parseo JSON,
  - persistencia,
  - resumen,
  - endpoints de historiales y edicion.

### Limitaciones actuales

- El historial previo ya se reutiliza para precargar datos del paciente en nuevas consultas, pero todavia no se incorpora como contexto longitudinal dentro del prompt del modelo.
- No hay autenticacion, cifrado ni control de acceso.
- Los historiales se guardan en JSON local, sin base de datos ni versionado de esquema.
- La interfaz esta pensada para uso local y todavia no esta empaquetada como aplicacion de escritorio.

## Flujo actual de la aplicacion

1. El usuario abre la pagina principal.
2. Introduce los datos del paciente.
3. Graba audio y obtiene una transcripcion local con Whisper.
4. Revisa la transcripcion y la envia a Ollama.
5. Se genera un resumen estructurado y se guarda en `data/patients/`.
6. Desde la pagina de historiales puede reabrir esa sesion, editarla, regenerar el resumen, borrar pacientes o lanzar una nueva consulta con sus datos ya cargados.

## Estructura real del repositorio

```text
/
|-- app.py
|-- requirements.txt
|-- template/
|   |-- main.html
|   `-- history.html
|-- src/
|   |-- main.py
|   |-- speech/
|   |   |-- __init__.py
|   |   `-- transcriber.py
|   `-- summarize/
|       |-- __init__.py
|       |-- models.py
|       |-- prompts.py
|       |-- service.py
|       `-- storage.py
|-- data/
|   `-- patients/
|-- tests/
|   |-- test_app.py
|   |-- test_summarize_service.py
|   `-- test_summarize_storage.py
`-- doc/
    `-- PROJECT.md
```

## Componentes principales

### `app.py`

- Sirve la interfaz principal y la vista de historiales.
- Expone endpoints para transcripcion, resumen y gestion de historiales.

### `src/speech/transcriber.py`

- Encapsula la transcripcion local con Whisper.

### `src/summarize/service.py`

- Orquesta el pipeline de resumen con Ollama.
- Permite tanto guardar una consulta nueva como regenerar un resumen sin persistirlo todavia.

### `src/summarize/storage.py`

- Gestiona los JSON de pacientes y sesiones.
- Permite listar pacientes, leer sesiones y guardar modificaciones manuales.

### `template/main.html`

- Interfaz principal de nueva consulta.

### `template/history.html`

- Interfaz de navegacion y edicion de historiales.

## Persistencia de datos

Cada paciente se guarda en un JSON dentro de `data/patients/`.

La estructura incluye:

- metadatos del paciente,
- fechas de creacion y actualizacion,
- lista de sesiones,
- transcripcion original o corregida,
- resumen,
- motivo de consulta,
- puntos clave,
- snapshot del contexto clinico asociado a esa sesion.

## Tareas pendientes

### Producto

- Reutilizar historiales previos como contexto resumido real dentro de nuevas sesiones, no solo como precarga del formulario.
- Mejorar aun mas la experiencia de navegacion y revision clinica.
- Anadir exportacion a formatos utiles como PDF, DOCX o informe clinico estructurado.

### Datos y seguridad

- Definir politica de backup local.
- Valorar cifrado de historiales.
- Introducir control de acceso si la app evoluciona mas alla del uso individual local.
- Estudiar versionado de esquema para los JSON.

### Despliegue

- Decidir si la entrega final sera web local, escritorio empaquetado, o ambas.
- Preparar una distribucion mas sencilla para usuarios no tecnicos.

### Entrega academica

- Revisar README y documentacion final.
- Preparar presentacion y memoria del proyecto.

## Nota importante

El proyecto prioriza privacidad y procesamiento local. Los datos clinicos guardados en `data/patients/` no deberian versionarse ni compartirse fuera del entorno controlado de trabajo.
