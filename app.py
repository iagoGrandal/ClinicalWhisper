from __future__ import annotations

import tempfile
from functools import lru_cache
from pathlib import Path

from flask import Flask, jsonify, render_template, request

DEFAULT_WHISPER_MODEL = "base"
DEFAULT_OLLAMA_MODEL = "llama3.2:3b"

app = Flask(__name__, template_folder="template")


@lru_cache(maxsize=4)
def get_transcriber(model_name: str, language: str | None):
    """Return a cached Whisper transcriber instance for the requested settings."""
    from src.speech import SpeechToText

    return SpeechToText(model_name=model_name, language=language)


@lru_cache(maxsize=1)
def get_summarizer():
    """Return the shared Ollama-based clinical summarizer."""
    from src.summarize import ClinicalSummarizer

    return ClinicalSummarizer(default_model=DEFAULT_OLLAMA_MODEL)


def get_available_ollama_models() -> list[str]:
    """Return the list of local Ollama models shown in the UI selector."""
    try:
        return get_summarizer().list_models()
    except Exception:
        return [DEFAULT_OLLAMA_MODEL]


@app.get("/")
def index() -> str:
    """Render the main local transcription and summarization interface."""
    return render_template(
        "main.html",
        default_ollama_model=DEFAULT_OLLAMA_MODEL,
        ollama_models=get_available_ollama_models(),
    )


@app.post("/transcribe")
def transcribe() -> tuple[object, int] | object:
    """Transcribe an uploaded audio file using the selected Whisper model."""
    audio = request.files.get("audio")
    if audio is None or audio.filename == "":
        return jsonify({"error": "No se recibio ningun audio."}), 400

    language = request.form.get("language") or None
    model_name = request.form.get("model") or DEFAULT_WHISPER_MODEL

    suffix = Path(audio.filename).suffix or ".wav"
    temp_file = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    temp_path = Path(temp_file.name)
    temp_file.close()

    try:
        audio.save(temp_path)
        text = get_transcriber(model_name, language).transcribe_file(temp_path)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
    finally:
        temp_path.unlink(missing_ok=True)

    return jsonify({"text": text})


@app.post("/summarize")
def summarize() -> tuple[object, int] | object:
    """Summarize the current consultation and persist the structured result."""
    payload = request.get_json(silent=True) or {}
    try:
        result = get_summarizer().summarize_consultation(payload)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

    return jsonify(result)


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
