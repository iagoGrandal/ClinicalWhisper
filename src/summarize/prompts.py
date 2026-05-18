"""Prompt builders for chunked clinical summarization."""

from __future__ import annotations

import json

from .models import PatientContext

CHUNK_RESPONSE_SCHEMA = {
    "summary": "Resumen corto del bloque actual.",
    "keypoints": ["Punto clave 1", "Punto clave 2"],
}

FINAL_RESPONSE_SCHEMA = {
    "summary": "Resumen global de la conversacion.",
    "visit_reason": "Motivo principal de consulta en una frase breve.",
    "keypoints": ["Punto clave 1", "Punto clave 2", "Punto clave 3"],
}


def build_chunk_messages(chunk_text: str, patient_context: PatientContext) -> list[dict[str, str]]:
    """Build the prompt used to summarize a single transcript chunk."""
    context_text = render_patient_context(patient_context)
    schema = json.dumps(CHUNK_RESPONSE_SCHEMA, ensure_ascii=False)
    user_prompt = (
        "Contexto del paciente:\n"
        f"{context_text}\n\n"
        "Transcripcion del bloque:\n"
        f"{chunk_text}\n\n"
        "Devuelve exclusivamente un JSON valido con este formato:\n"
        f"{schema}"
    )
    return [
        {
            "role": "system",
            "content": (
                "Eres un asistente clinico local. Resume el bloque en espanol claro y breve. "
                "No inventes datos. Respeta negaciones y sintomas ausentes exactamente como aparezcan. "
                "Devuelve solo JSON valido sin texto adicional."
            ),
        },
        {"role": "user", "content": user_prompt},
    ]


def build_final_messages(
    chunk_summaries: list[dict[str, object]],
    patient_context: PatientContext,
) -> list[dict[str, str]]:
    """Build the prompt used to create the final clinical summary."""
    context_text = render_patient_context(patient_context)
    chunk_text = json.dumps(chunk_summaries, ensure_ascii=False, indent=2)
    schema = json.dumps(FINAL_RESPONSE_SCHEMA, ensure_ascii=False)
    user_prompt = (
        "Contexto del paciente:\n"
        f"{context_text}\n\n"
        "Resumenes parciales en orden cronologico:\n"
        f"{chunk_text}\n\n"
        "Genera un resumen final breve, un motivo de consulta conciso y puntos clave clinicos.\n"
        "Devuelve exclusivamente un JSON valido con este formato:\n"
        f"{schema}"
    )
    return [
        {
            "role": "system",
            "content": (
                "Eres un asistente clinico local. Fusiona la informacion disponible en espanol. "
                "No inventes, no diagnostiques y conserva las negaciones clinicas sin invertirlas. "
                "No escribas nada fuera del JSON solicitado."
            ),
        },
        {"role": "user", "content": user_prompt},
    ]


def render_patient_context(patient_context: PatientContext) -> str:
    """Render patient context as compact text for the prompt."""
    sections = patient_context.to_prompt_sections()
    if not sections:
        return "Sin contexto adicional."

    lines = [f"- {label}: {value}" for label, value in sections.items()]
    return "\n".join(lines)
