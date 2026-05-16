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
            updated_at=timestamp,
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

    def list_patients(self) -> list[dict[str, object]]:
        """Return lightweight metadata for each stored patient record."""
        patients: list[dict[str, object]] = []
        for path in self.base_path.glob("*.json"):
            patient_id = path.stem
            record = self._load_patient_record(patient_id)
            if record is None:
                continue

            last_session_at = ""
            if record.sessions:
                last_session = max(
                    record.sessions,
                    key=lambda session: session.updated_at or session.created_at,
                )
                last_session_at = last_session.updated_at or last_session.created_at

            patients.append(
                {
                    "patient_id": record.patient_id,
                    "patient_name": record.patient_name,
                    "patient_identifier_raw": record.patient_identifier_raw,
                    "session_count": len(record.sessions),
                    "created_at": record.created_at,
                    "updated_at": record.updated_at,
                    "last_session_at": last_session_at,
                }
            )

        patients.sort(key=lambda item: (str(item["patient_name"]).casefold(), str(item["patient_id"])))
        return patients

    def get_patient_record(self, patient_id: str) -> PatientRecord | None:
        """Return one stored patient record by identifier when present."""
        return self._load_patient_record(normalize_patient_identifier(patient_id))

    def get_session_record(self, patient_id: str, session_id: str) -> SessionRecord | None:
        """Return one stored session for the selected patient when present."""
        record = self.get_patient_record(patient_id)
        if record is None:
            return None

        for session in record.sessions:
            if session.session_id == session_id:
                return session
        return None

    def update_session(
        self,
        patient_id: str,
        session_id: str,
        patient_context: PatientContext,
        transcript: str,
        summary: str,
        visit_reason: str,
        keypoints: list[str],
        model: str,
    ) -> SessionRecord:
        """Persist manual edits to one existing consultation session."""
        record = self.get_patient_record(patient_id)
        if record is None:
            raise KeyError(f"No existe el paciente '{patient_id}'.")

        timestamp = current_timestamp()
        updated_session: SessionRecord | None = None
        sessions: list[SessionRecord] = []

        for session in record.sessions:
            if session.session_id != session_id:
                sessions.append(session)
                continue

            updated_session = replace(
                session,
                updated_at=timestamp,
                transcript=transcript,
                summary=summary,
                visit_reason=visit_reason,
                keypoints=keypoints,
                model=model,
                patient_context=patient_context.to_storage_dict(),
            )
            sessions.append(updated_session)

        if updated_session is None:
            raise KeyError(f"No existe la sesion '{session_id}' para el paciente '{patient_id}'.")

        updated_record = replace(
            record,
            patient_name=patient_context.patient_name,
            patient_name_normalized=patient_context.patient_name_normalized,
            patient_identifier_raw=patient_context.patient_identifier_raw,
            updated_at=timestamp,
            sessions=sessions,
        )
        self._write_patient_record(updated_record)
        return updated_session

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

        sessions = [self._session_from_dict(session) for session in data.get("sessions", [])]
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

    def _session_from_dict(self, data: dict[str, object]) -> SessionRecord:
        """Build a session model while tolerating older JSON payloads."""
        return SessionRecord(
            session_id=str(data["session_id"]),
            created_at=str(data["created_at"]),
            updated_at=str(data.get("updated_at", data["created_at"])),
            transcript=str(data.get("transcript", "")),
            summary=str(data.get("summary", "")),
            visit_reason=str(data.get("visit_reason", "")),
            keypoints=[str(item) for item in data.get("keypoints", [])],
            model=str(data.get("model", "")),
            patient_context={str(key): str(value) for key, value in dict(data.get("patient_context", {})).items()},
        )


def current_timestamp() -> str:
    """Return an ISO 8601 timestamp in UTC for persisted session records."""
    return datetime.now(UTC).replace(microsecond=0).isoformat()
