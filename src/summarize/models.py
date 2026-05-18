"""Typed models used by the summarization pipeline."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(slots=True)
class PatientContext:
    """Clinical and identification context collected from the intake form."""

    patient_id: str
    patient_name: str
    patient_name_normalized: str
    patient_identifier_raw: str
    patient_dni: str = ""
    patient_sex: str = ""
    patient_phone: str = ""
    birth_date: str = ""
    visit_date: str = ""
    medical_history: str = ""
    current_medication: str = ""
    allergies: str = ""
    visit_reason: str = ""

    def to_prompt_sections(self) -> dict[str, str]:
        """Return only non-empty context fields suitable for prompt rendering."""
        fields = {
            "identificador_paciente": self.patient_id,
            "nombre_paciente": self.patient_name,
            "dni": self.patient_dni,
            "sexo": self.patient_sex,
            "telefono": self.patient_phone,
            "fecha_nacimiento": self.birth_date,
            "fecha_consulta": self.visit_date,
            "antecedentes_medicos": self.medical_history,
            "medicacion_actual": self.current_medication,
            "alergias": self.allergies,
            "motivo_consulta_previo": self.visit_reason,
        }
        return {key: value for key, value in fields.items() if value}

    def to_storage_dict(self) -> dict[str, str]:
        """Serialize the patient context snapshot for persistent storage."""
        return asdict(self)


@dataclass(slots=True)
class SummaryResult:
    """Structured response returned by the summarization pipeline."""

    summary: str
    visit_reason: str
    keypoints: list[str]
    model: str
    patient_id: str
    session_id: str

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-ready representation of the summary result."""
        return asdict(self)


@dataclass(slots=True)
class SessionRecord:
    """Persistent representation of a summarized consultation."""

    session_id: str
    created_at: str
    transcript: str
    summary: str
    visit_reason: str
    keypoints: list[str]
    model: str
    patient_context: dict[str, str] = field(default_factory=dict)
    updated_at: str = ""

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-ready representation of a patient session."""
        return asdict(self)


@dataclass(slots=True)
class PatientRecord:
    """Persistent representation of a patient and all stored sessions."""

    patient_id: str
    patient_name: str
    patient_name_normalized: str
    patient_identifier_raw: str
    created_at: str
    updated_at: str
    sessions: list[SessionRecord] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-ready representation of the patient record."""
        data = asdict(self)
        data["sessions"] = [session.to_dict() for session in self.sessions]
        return data
