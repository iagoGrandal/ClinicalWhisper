# 🩺 Clinical Whisper

Aplicación de escritorio orientada a personal médico para el registro automático de motivos de consulta a partir de conversación hablada.

## 📌 Descripción del proyecto

El objetivo de este proyecto es desarrollar una aplicación **100% local** (sin conexión a servidores externos) que:

- Capture audio de conversación (paciente - profesional).
- Transcriba el audio a texto mediante **Whisper**.
- Procese el texto con modelos de lenguaje de código abierto.
- Genere automáticamente:
  - 🧾 Resumen de la conversación
  - 🎯 Motivo de consulta
  - 🔑 Puntos clave (keypoints)

---

## ⚙️ Requisitos del proyecto

- Aplicación de escritorio (no web dependiente de servidor externo)
- Procesamiento completamente **local**
- Uso de:
  - Whisper (speech-to-text)
  - Modelo LLM open source (a elección)

---

## ✅ To-Do

- [ ] Código en GitHub (repositorio limpio)
- [ ] Presentación en PowerPoint
- [ ] Texto de presentación / memoria

---

## 🏗️ Estructura del repositorio

```bash
/
├── templates/              # HTML + CSS + JS (interfaz)
├── flask.py               # Backend principal (Flask)
├── src/
│   ├── speech/            # Procesamiento de audio
│   ├── whisper/           # Transcripción (audio → texto)
│   └── summary/           # Generación de resumen y keypoints