# ClinicalWhisper

Proyecto de la asignatura Bioinformática y Medicina del Grado en Inteligencia Artificial de la Universidade da Coruña.

ClinicalWhisper es una aplicacion local para registrar consultas clinicas a partir de audio. La herramienta transcribe conversaciones con Whisper, genera un resumen estructurado con Ollama y guarda un historial reutilizable por paciente.

|Integrante|Correo|
|:--|:--|
|Iago Grandal del Río|i.gdelrio@udc.es|
|Claudia Vidal Otero|claudia.votero@udc.es|



## Objetivo

El proyecto busca demostrar una integracion sencilla de modelos ML/LLM en un flujo clinico realista, manteniendo dos prioridades:

- procesamiento local siempre que sea posible
- interfaz simple y facil de explicar en una presentacion oral

## Que hace la aplicacion

- Graba audio desde el navegador.
- Transcribe la consulta con Whisper.
- Genera un resumen clinico estructurado con Ollama.
- Guarda cada consulta por paciente en `data/patients/`.
- Permite revisar y editar sesiones anteriores.
- Permite regenerar un resumen antes de guardar cambios.
- Permite crear una nueva consulta para un paciente ya existente con sus datos rellenados automaticamente.
- Permite borrar un paciente y todas sus sesiones guardadas.

## Flujo de uso

1. Abrir la pantalla `Nueva consulta`.
2. Introducir o reutilizar los datos del paciente.
3. Grabar la conversacion y revisar la transcripcion.
4. Enviar la transcripcion al modelo para obtener resumen, motivo de consulta y puntos clave.
5. Guardar automaticamente la sesion en el historial local.
6. Desde `Historiales`, abrir sesiones previas, corregir datos y regenerar el resumen si hace falta.

## Stack tecnologico

- `Flask` para servir la interfaz y la API local.
- `Whisper` para speech-to-text local.
- `Ollama` para el resumen clinico con modelos open source.
- `HTML + CSS + JavaScript` para la interfaz.
- `unittest` para pruebas automatizadas.

## Requisitos

- Python 3.10 o superior.
- Ollama instalado y funcionando en local.
- Un modelo compatible descargado en Ollama, por defecto `llama3.2:3b`.
- Microfono disponible si se quiere grabar audio desde la interfaz.
- `ffmpeg` solo es necesario para algunos formatos externos; la grabacion web genera WAV PCM directamente.

## Instalacion

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

Si necesitas `ffmpeg` en Windows:

```bash
winget install Gyan.FFmpeg
```

## Ejecucion

Lanza la aplicacion web local:

```bash
python app.py
```

Despues abre:

```text
http://127.0.0.1:5000
```

## Pruebas

```bash
python -m unittest discover -s tests
```

## Estructura del repositorio

```text
.
|-- app.py
|-- requirements.txt
|-- template/
|   |-- main.html
|   `-- history.html
|-- src/
|   |-- main.py
|   |-- speech/
|   `-- summarize/
|-- data/
|   `-- patients/
|-- tests/
|-- doc/
|   `-- PROJECT.md
`-- README.md
```

## Decisiones de diseño

- La app es local para reducir dependencia de servicios externos y simplificar la privacidad de los datos.
- El almacenamiento usa JSON por paciente para mantener la arquitectura facil de entender.
- La interfaz separa dos tareas claras: nueva consulta y revision de historiales.
- El resumen se puede regenerar antes de guardar, para facilitar correcciones humanas.

## Limitaciones actuales

- No hay autenticacion ni control de acceso.
- Los historiales no estan cifrados.
- El almacenamiento sigue siendo local y basado en JSON, no en una base de datos.
- La app esta pensada para demo y entorno academico, no para produccion clinica real.

## Entrega academica

Este repositorio debe entregarse con todos los miembros del grupo como colaboradores e incluir, como minimo:

- todo el codigo fuente
- este `README.md`
- el enlace a la aplicacion web, si existe despliegue publico
- el enlace al DOI del release en Zenodo
- el enlace a la presentacion del examen final

### Enlaces de entrega

- Aplicacion web: `NO APLICA`
- [DOI Zenodo](https://zenodo.org/records/20276215?token=eyJhbGciOiJIUzUxMiJ9.eyJpZCI6IjlhMWZkMDVkLTZhYzEtNDllYS04MThkLWJmNWI0OTA1NWYyYSIsImRhdGEiOnt9LCJyYW5kb20iOiJlYWQzOTVhNDg4MzY2NDlmNTc3MTU0NzI1OTMzZTgyNSJ9.OoONhdPq7rJvOP7qRaj6yp63oceFIomswD2GNsgaZWRRHFAycw0fB5ibgBH--Iz8YOd2shgqy3cPSFqN36ep4Q)
- [Presentación del examen](https://udcgal-my.sharepoint.com/:p:/g/personal/i_gdelrio_udc_es/IQDMMytfs311QL8TuONZaE32AagcTE46QsmTb_ZFKh67-XM?e=v5eYHx)
