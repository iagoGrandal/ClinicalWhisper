# ClinicalWhisper

Aplicacion creada para la asignatura Bioinformatica y Medicina del grado de Inteligencia Artificial de la UDC.

## Speech to text local con Whisper

Este repositorio incluye un primer modulo reutilizable para capturar audio del microfono y convertirlo en texto con Whisper.

### Instalacion

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

La grabacion desde microfono no necesita `ffmpeg`, porque la aplicacion envia a Whisper un WAV PCM de 16 kHz. Para transcribir otros formatos de audio externos, Whisper si necesita `ffmpeg` instalado en el sistema. En Windows se puede instalar con:

```bash
winget install Gyan.FFmpeg
```

### Uso desde terminal

```bash
python src/main.py --duration 5 --model base --language es
```

El comando graba 5 segundos desde el microfono por defecto y muestra un `str` con la transcripcion.

Modelos utiles:

- `tiny`: mas rapido, menos preciso.
- `base`: buen punto de partida para pruebas.
- `small`, `medium`, `large`: mas precisos, pero mas lentos y pesados.

### Uso desde Python

```python
from src.speech import SpeechToText

stt = SpeechToText(model_name="base", language="es")
texto = stt.listen(seconds=5)
print(texto)
```

### Uso con interfaz web

```bash
python app.py
```

Abre `http://127.0.0.1:5000` en el navegador. La interfaz permite elegir duracion y idioma, grabar desde el micrófono, ver la transcripcion y corregirla en una caja de texto.
