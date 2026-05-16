from __future__ import annotations

import tempfile
from functools import lru_cache
from pathlib import Path

from flask import Flask, jsonify, render_template, request


app = Flask(__name__, template_folder="template")


@lru_cache(maxsize=4)
def get_transcriber(model_name: str, language: str | None):
    from src.speech import SpeechToText

    return SpeechToText(model_name=model_name, language=language)


@app.get("/")
def index() -> str:
    return render_template("main.html")


@app.post("/transcribe")
def transcribe() -> tuple[object, int] | object:
    audio = request.files.get("audio")
    if audio is None or audio.filename == "":
        return jsonify({"error": "No se recibió ningún audio."}), 400

    language = request.form.get("language") or None
    model_name = request.form.get("model") or "base"

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


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
