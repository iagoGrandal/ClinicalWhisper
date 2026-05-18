"""Local clinical summarization pipeline powered by Ollama."""

from __future__ import annotations

import json
import re
import uuid
from pathlib import Path
from typing import Any

from ollama import Client, ResponseError

from .models import PatientContext, SummaryResult
from .prompts import build_chunk_messages, build_final_messages
from .storage import JsonPatientStore, build_patient_context, normalize_free_text

SENTENCE_BOUNDARY_PATTERN = re.compile(r"(?<=[.!?])\s+")


class ClinicalSummarizer:
    """Generate structured clinical summaries and persist them locally."""

    def __init__(
        self,
        default_model: str = "llama3.2:3b",
        client: Client | None = None,
        store: JsonPatientStore | None = None,
        max_chunk_chars: int = 2200,
    ) -> None:
        """Initialize the Ollama client, storage backend and chunking settings."""
        self.default_model = default_model
        self.client = client or Client()
        self.store = store or JsonPatientStore()
        self.max_chunk_chars = max_chunk_chars

    def summarize_consultation(self, payload: dict[str, object]) -> dict[str, object]:
        """Summarize a consultation, persist it and return the public response."""
        patient_context, transcript, summary_result = self.generate_summary_result(payload)
        self.store.save_summary(patient_context, transcript, summary_result)
        response = summary_result.to_dict()
        response["saved"] = True
        return response

    def preview_summary(self, payload: dict[str, object]) -> dict[str, object]:
        """Summarize a consultation without persisting the result."""
        _, _, summary_result = self.generate_summary_result(payload)
        response = summary_result.to_dict()
        response["saved"] = False
        return response

    def list_models(self) -> list[str]:
        """Return the names of all local Ollama models available to the app."""
        response = self.client.list()
        models = [model.model for model in response.models]
        if not models:
            return [self.default_model]

        if self.default_model in models:
            ordered = [self.default_model]
            ordered.extend(model for model in models if model != self.default_model)
            return ordered
        return models

    def generate_summary_result(
        self,
        payload: dict[str, object],
    ) -> tuple[PatientContext, str, SummaryResult]:
        """Build a structured summary result from the raw consultation payload."""
        transcript = normalize_free_text(str(payload.get("transcript", "")))
        if not transcript:
            raise ValueError("La transcripcion no puede estar vacia.")

        patient_context = build_patient_context(payload)
        model = normalize_free_text(str(payload.get("model", ""))) or self.default_model
        chunk_summaries = self._summarize_chunks(transcript, patient_context, model)
        summary_result = self._build_final_summary(chunk_summaries, patient_context, model)
        return patient_context, transcript, summary_result

    def _summarize_chunks(
        self,
        transcript: str,
        patient_context: PatientContext,
        model: str,
    ) -> list[dict[str, object]]:
        """Summarize each transcript chunk before building the final summary."""
        chunks = split_text_chunks(transcript, self.max_chunk_chars)
        return [self._summarize_single_chunk(chunk, patient_context, model) for chunk in chunks]

    def _summarize_single_chunk(
        self,
        chunk: str,
        patient_context: PatientContext,
        model: str,
    ) -> dict[str, object]:
        """Run Ollama on one transcript chunk and validate the JSON response."""
        messages = build_chunk_messages(chunk, patient_context)
        content = self._chat_json(model, messages)
        parsed = parse_json_content(content)
        return {
            "summary": normalize_free_text(str(parsed.get("summary", ""))),
            "keypoints": normalize_keypoints(parsed.get("keypoints", [])),
        }

    def _build_final_summary(
        self,
        chunk_summaries: list[dict[str, object]],
        patient_context: PatientContext,
        model: str,
    ) -> SummaryResult:
        """Combine chunk summaries into the final structured consultation output."""
        messages = build_final_messages(chunk_summaries, patient_context)
        content = self._chat_json(model, messages)
        parsed = parse_json_content(content)
        summary = normalize_free_text(str(parsed.get("summary", "")))
        visit_reason = normalize_free_text(str(parsed.get("visit_reason", "")))
        keypoints = normalize_keypoints(parsed.get("keypoints", []))
        if not summary or not visit_reason or not keypoints:
            raise ValueError("El modelo no devolvio un resumen estructurado valido.")

        return SummaryResult(
            summary=summary,
            visit_reason=visit_reason,
            keypoints=keypoints,
            model=model,
            patient_id=patient_context.patient_id,
            session_id=str(uuid.uuid4()),
        )

    def _chat_json(self, model: str, messages: list[dict[str, str]]) -> str:
        """Execute a synchronous Ollama chat call that must return JSON text."""
        try:
            response = self.client.chat(
                model=model,
                messages=messages,
                format="json",
                options={"temperature": 0},
            )
        except ResponseError as exc:
            raise RuntimeError(f"Error al invocar Ollama con el modelo '{model}': {exc.error}") from exc
        return response.message.content


def split_text_chunks(text: str, max_chars: int) -> list[str]:
    """Split text into ordered chunks that stay close to the size budget."""
    cleaned = normalize_free_text(text)
    if not cleaned:
        return []

    sentences = SENTENCE_BOUNDARY_PATTERN.split(cleaned)
    chunks: list[str] = []
    current: list[str] = []
    current_length = 0

    for sentence in sentences:
        pieces = split_long_sentence(sentence, max_chars)
        for piece in pieces:
            piece_length = len(piece) + (1 if current else 0)
            if current and current_length + piece_length > max_chars:
                chunks.append(" ".join(current))
                current = [piece]
                current_length = len(piece)
            else:
                current.append(piece)
                current_length += piece_length

    if current:
        chunks.append(" ".join(current))
    return chunks


def split_long_sentence(sentence: str, max_chars: int) -> list[str]:
    """Split overly long sentence fragments by word boundary when required."""
    cleaned = normalize_free_text(sentence)
    if not cleaned:
        return []
    if len(cleaned) <= max_chars:
        return [cleaned]

    words = cleaned.split(" ")
    pieces: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if current and len(candidate) > max_chars:
            pieces.append(current)
            current = word
        else:
            current = candidate
    if current:
        pieces.append(current)
    return pieces


def parse_json_content(content: str) -> dict[str, Any]:
    """Parse JSON content returned by the model, tolerating wrapped objects."""
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        parsed = json.loads(extract_json_object(content))

    if not isinstance(parsed, dict):
        raise ValueError("La respuesta del modelo debe ser un objeto JSON.")
    return parsed


def extract_json_object(content: str) -> str:
    """Extract the first JSON object from a text response."""
    start = content.find("{")
    end = content.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No se encontro un objeto JSON valido en la respuesta del modelo.")
    return content[start : end + 1]


def normalize_keypoints(keypoints: Any) -> list[str]:
    """Normalize and filter keypoints returned by the model."""
    if not isinstance(keypoints, list):
        raise ValueError("Los puntos clave deben devolverse como lista.")

    normalized = [normalize_free_text(str(item)) for item in keypoints]
    return [item for item in normalized if item]


def create_store_from_path(base_path: str | Path) -> JsonPatientStore:
    """Build a JSON patient store rooted at the provided path."""
    return JsonPatientStore(base_path=base_path)
