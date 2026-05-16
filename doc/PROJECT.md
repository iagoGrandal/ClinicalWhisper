# Clinical Whisper

Aplicacion local orientada a personal medico para registrar consultas clinicas a partir de conversaciones habladas, sin depender de servicios externos.

## Descripcion del proyecto

El objetivo es construir una herramienta que funcione de manera 100% local y que permita:

- Capturar audio entre paciente y profesional.
- Transcribir el audio con Whisper.
- Procesar la transcripcion con modelos open source ejecutados en Ollama.
- Generar automaticamente:
  - Resumen de la conversacion.
  - Motivo de consulta.
  - Puntos clave clinicos.
- Guardar cada consulta en un historial local por paciente.

## Estado actual del repositorio

### Ya implementado

- Backend Flask local en `app.py`.
- Captura de audio desde navegador y envio al backend.
- Transcripcion local con Whisper mediante `src/speech/`.
- Modulo `src/summarize/` para resumir con Ollama usando salida JSON estricta.
- Estrategia de resumen por fases:
  - troceado de la transcripcion,
  - resumen parcial por bloques,
  - resumen final estructurado.
- Persistencia local en JSON dentro de `data/patients/`.
- Interfaz web para:
  - introducir datos del paciente,
  - grabar audio,
  - corregir la transcripcion,
  - seleccionar modelo Ollama,
  - generar resumen, motivo de consulta y puntos clave.
- Pruebas automatizadas de normalizacion, chunking, parseo, persistencia y endpoint.

### En progreso funcional

- La app ya cubre el flujo base de transcripcion y resumen local.
- El historial se guarda por identificador manual del paciente y nombre normalizado.
- La memoria historica se persiste, pero todavia no se reutiliza como contexto en consultas futuras.

## Decisiones tecnicas actuales

- Whisper se usa para speech-to-text local.
- Ollama se usa para ejecutar LLMs open source de manera local.
- Modelo por defecto actual para resumen: `llama3.2:3b`.
- El resumen se exige en JSON estricto para simplificar el parseo y la persistencia.
- La estructura de pacientes se basa en:
  - un identificador manual explicito,
  - nombre original,
  - nombre normalizado,
  - lista de sesiones.

## Estructura real del repositorio

```text
/
|-- app.py                    # Backend Flask
|-- requirements.txt          # Dependencias Python
|-- template/
|   `-- main.html             # Interfaz web local
|-- src/
|   |-- main.py               # CLI simple para Whisper
|   |-- speech/
|   |   |-- __init__.py
|   |   `-- transcriber.py    # Grabacion y transcripcion local
|   `-- summarize/
|       |-- __init__.py
|       |-- models.py         # Contratos tipados
|       |-- prompts.py        # Prompts para Ollama
|       |-- service.py        # Pipeline de resumen
|       `-- storage.py        # Persistencia local JSON
|-- data/
|   `-- patients/             # Historial local por paciente
|-- tests/                    # Pruebas automatizadas
`-- doc/
    `-- PROJECT.md
```

## Que queda por hacer

### Producto

- Mejorar la experiencia clinica de la interfaz web.
- Mostrar historial previo de un paciente dentro de la app.
- Permitir editar y volver a guardar un resumen ya generado.
- Añadir exportacion a formatos utiles para consulta o entrega.

### LLM y resumen

- Reutilizar historiales previos como contexto resumido en nuevas sesiones.
- Afinar prompts para consultas largas o conversaciones poco estructuradas.
- Evaluar modelos locales alternativos y comparar calidad frente a coste.
- Añadir validaciones adicionales para evitar respuestas incompletas o ambiguas.

### Persistencia y datos

- Endurecer la capa de almacenamiento local.
- Definir politica de backup, cifrado o control de acceso si el proyecto evoluciona.
- Incorporar versionado de esquema para futuros cambios en los JSON.

### Interfaz y despliegue

- Decidir si la version final sera:
  - app web local servida por Flask,
  - aplicacion de escritorio empaquetada,
  - o una combinacion de ambas.
- Mejorar el layout responsive y la presentacion visual.
- Separar mejor frontend y backend si el alcance crece.

### Entrega academica

- Limpiar y revisar el repositorio final para GitHub.
- Preparar la presentacion en PowerPoint.
- Redactar la memoria o texto de presentacion del proyecto.

## Notas importantes

- El proyecto prioriza procesamiento local y privacidad.
- Los datos clinicos guardados en `data/patients/` no deben versionarse.
- El flujo actual sirve como base funcional para una futura app de escritorio o una web local mas pulida.
