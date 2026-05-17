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


def get_patient_store():
    """Expose the storage backend used by the shared summarizer."""
    return get_summarizer().store


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


@app.get("/historiales")
def histories() -> str:
    """Render the patient histories workspace."""
    return render_template(
        "history.html",
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


@app.get("/api/patients")
def list_patients() -> object:
    """Return the stored patient list used by the histories UI."""
    return jsonify({"patients": get_patient_store().list_patients()})


@app.get("/api/patients/<patient_id>")
def patient_detail(patient_id: str) -> tuple[object, int] | object:
    """Return one patient record with lightweight session metadata."""
    record = get_patient_store().get_patient_record(patient_id)
    if record is None:
        return jsonify({"error": "No se encontro el paciente solicitado."}), 404

    sessions = sorted(
        record.sessions,
        key=lambda session: session.updated_at or session.created_at,
        reverse=True,
    )
    return jsonify(
        {
            "patient": {
                "patient_id": record.patient_id,
                "patient_name": record.patient_name,
                "patient_identifier_raw": record.patient_identifier_raw,
                "created_at": record.created_at,
                "updated_at": record.updated_at,
                "sessions": [serialize_session_summary(session) for session in sessions],
            }
        }
    )


@app.get("/api/patients/<patient_id>/sessions/<session_id>")
def session_detail(patient_id: str, session_id: str) -> tuple[object, int] | object:
    """Return one stored consultation session with full editable content."""
    session = get_patient_store().get_session_record(patient_id, session_id)
    if session is None:
        return jsonify({"error": "No se encontro la sesion solicitada."}), 404

    return jsonify({"session": serialize_session_detail(patient_id, session)})


@app.post("/api/sessions/resummarize")
def resummarize_session() -> tuple[object, int] | object:
    """Regenerate the summary for the edited consultation without saving it yet."""
    payload = request.get_json(silent=True) or {}
    try:
        result = get_summarizer().preview_summary(payload)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

    return jsonify(result)


@app.put("/api/patients/<patient_id>/sessions/<session_id>")
def update_session(patient_id: str, session_id: str) -> tuple[object, int] | object:
    """Persist manual edits for one existing patient session."""
    from src.summarize.storage import build_patient_context, normalize_free_text, normalize_patient_identifier
    from src.summarize.service import normalize_keypoints

    payload = request.get_json(silent=True) or {}
    try:
        patient_context = build_patient_context(payload)
        if patient_context.patient_id != normalize_patient_identifier(patient_id):
            raise ValueError("No se puede cambiar el DNI del paciente desde esta pantalla.")

        transcript = normalize_free_text(str(payload.get("transcript", "")))
        if not transcript:
            raise ValueError("La transcripcion no puede estar vacia.")

        summary = normalize_free_text(str(payload.get("summary", "")))
        visit_reason = normalize_free_text(str(payload.get("visitReason", "")))
        model = normalize_free_text(str(payload.get("model", ""))) or DEFAULT_OLLAMA_MODEL
        keypoints = normalize_keypoints(parse_keypoints_payload(payload.get("keypoints", [])))
        session = get_patient_store().update_session(
            patient_id=patient_id,
            session_id=session_id,
            patient_context=patient_context,
            transcript=transcript,
            summary=summary,
            visit_reason=visit_reason,
            keypoints=keypoints,
            model=model,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except KeyError as exc:
        return jsonify({"error": str(exc.args[0])}), 404
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

    return jsonify({"session": serialize_session_detail(patient_context.patient_id, session), "saved": True})


def serialize_session_summary(session) -> dict[str, object]:
    """Return condensed session data for the histories sidebar."""
    context = session.patient_context or {}
    visit_date = context.get("visit_date", "")
    return {
        "session_id": session.session_id,
        "created_at": session.created_at,
        "updated_at": session.updated_at or session.created_at,
        "visit_date": visit_date,
        "visit_reason": session.visit_reason,
        "summary_preview": session.summary[:180],
    }


def serialize_session_detail(patient_id: str, session) -> dict[str, object]:
    """Return full editable session data for the histories editor."""
    return {
        "patient_id": patient_id,
        "session_id": session.session_id,
        "created_at": session.created_at,
        "updated_at": session.updated_at or session.created_at,
        "transcript": session.transcript,
        "summary": session.summary,
        "visit_reason": session.visit_reason,
        "keypoints": session.keypoints,
        "model": session.model,
        "patient_context": session.patient_context,
    }


def parse_keypoints_payload(value: object) -> list[str]:
    """Accept keypoints as a JSON list or as textarea lines."""
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str):
        return [line.lstrip("- ").strip() for line in value.splitlines()]
    return []


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
