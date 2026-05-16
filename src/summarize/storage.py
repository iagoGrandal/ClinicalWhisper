"""Helpers to normalize patient identity and persist local JSON records."""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from .models import PatientContext, PatientRecord, SessionRecord, SummaryResult

WHITESPACE_PATTERN = re.compile(r"\s+")
NON_ALNUM_PATTERN = re.compile(r"[^a-z0-9]+")


def normalize_free_text(value: str) -> str:
    """Trim text and collapse internal whitespace while preserving casing."""
    return WHITESPACE_PATTERN.sub(" ", value.strip())


def normalize_patient_name(value: str) -> str:
    """Normalize a patient name for comparisons and filesystem-safe grouping."""
    collapsed = normalize_free_text(value)
    normalized = unicodedata.normalize("NFKD", collapsed)
    without_accents = "".join(char for char in normalized if not unicodedata.combining(char))
    return without_accents.casefold()


def normalize_patient_identifier(value: str) -> str:
    """Normalize the manual patient identifier into a stable slug."""
    normalized = normalize_patient_name(value)
    slug = NON_ALNUM_PATTERN.sub("-", normalized).strip("-")
    return slug


def build_patient_context(payload: dict[str, object]) -> PatientContext:
    """Validate raw request data and convert it into a typed patient context."""
    raw_identifier = normalize_free_text(str(payload.get("patientIdentifier", "")))
    patient_name = normalize_free_text(str(payload.get("patientName", "")))
    patient_id = normalize_patient_identifier(raw_identifier)
    patient_name_normalized = normalize_patient_name(patient_name)

    if not patient_id:
        raise ValueError("Debes indicar un identificador del paciente.")
    if not patient_name:
        raise ValueError("Debes indicar el nombre del paciente.")

    return PatientContext(
        patient_id=patient_id,
        patient_name=patient_name,
        patient_name_normalized=patient_name_normalized,
        patient_identifier_raw=raw_identifier,
        patient_dni=normalize_free_text(str(payload.get("patientDni", ""))),
        patient_sex=normalize_free_text(str(payload.get("patientSex", ""))),
        patient_phone=normalize_free_text(str(payload.get("patientPhone", ""))),
        birth_date=normalize_free_text(str(payload.get("birthDate", ""))),
        visit_date=normalize_free_text(str(payload.get("visitDate", ""))),
        medical_history=normalize_free_text(str(payload.get("medicalHistory", ""))),
        current_medication=normalize_free_text(str(payload.get("currentMedication", ""))),
        allergies=normalize_free_text(str(payload.get("allergies", ""))),
        visit_reason=normalize_free_text(str(payload.get("visitReason", ""))),
    )


class JsonPatientStore:
    """Persist patient records as local JSON files grouped by patient identifier."""

    def __init__(self, base_path: str | Path = "data/patients") -> None:
        """Create the store and ensure the target directory exists."""
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def save_summary(
        self,
        patient_context: PatientContext,
        transcript: str,
        summary_result: SummaryResult,
    ) -> PatientRecord:
        """Append a new summarized session to the patient record and persist it."""
        record = self._load_patient_record(patient_context.patient_id)
        timestamp = current_timestamp()
        if record is None:
            record = self._create_patient_record(patient_context, timestamp)

        session = SessionRecord(
            session_id=summary_result.session_id,
            created_at=timestamp,
            transcript=transcript,
            summary=summary_result.summary,
            visit_reason=summary_result.visit_reason,
            keypoints=summary_result.keypoints,
            model=summary_result.model,
            patient_context=patient_context.to_storage_dict(),
        )
        updated = replace(record, updated_at=timestamp, sessions=[*record.sessions, session])
        self._write_patient_record(updated)
        return updated

    def _create_patient_record(self, patient_context: PatientContext, timestamp: str) -> PatientRecord:
        """Build a new patient record from the first known consultation."""
        return PatientRecord(
            patient_id=patient_context.patient_id,
            patient_name=patient_context.patient_name,
            patient_name_normalized=patient_context.patient_name_normalized,
            patient_identifier_raw=patient_context.patient_identifier_raw,
            created_at=timestamp,
            updated_at=timestamp,
        )

    def _load_patient_record(self, patient_id: str) -> PatientRecord | None:
        """Load an existing patient record from disk when present."""
        path = self._patient_path(patient_id)
        if not path.exists():
            return None

        with path.open("r", encoding="utf-8") as file_handle:
            data = json.load(file_handle)

        sessions = [SessionRecord(**session) for session in data.get("sessions", [])]
        return PatientRecord(
            patient_id=data["patient_id"],
            patient_name=data["patient_name"],
            patient_name_normalized=data["patient_name_normalized"],
            patient_identifier_raw=data["patient_identifier_raw"],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            sessions=sessions,
        )

    def _write_patient_record(self, patient_record: PatientRecord) -> None:
        """Write the complete patient record to its JSON file."""
        path = self._patient_path(patient_record.patient_id)
        with path.open("w", encoding="utf-8") as file_handle:
            json.dump(patient_record.to_dict(), file_handle, ensure_ascii=False, indent=2)

    def _patient_path(self, patient_id: str) -> Path:
        """Return the JSON path assigned to the provided patient identifier."""
        return self.base_path / f"{patient_id}.json"


def current_timestamp() -> str:
    """Return an ISO 8601 timestamp in UTC for persisted session records."""
    return datetime.now(UTC).replace(microsecond=0).isoformat()
