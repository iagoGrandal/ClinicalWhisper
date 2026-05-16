"""Tests for patient normalization and JSON persistence."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.summarize.models import PatientContext, SummaryResult
from src.summarize.storage import (
    JsonPatientStore,
    normalize_patient_identifier,
    normalize_patient_name,
)


class NormalizePatientDataTests(unittest.TestCase):
    """Validate normalization helpers for patient identity fields."""

    def test_normalize_patient_name_removes_accents_and_extra_spaces(self) -> None:
        """Patient names should normalize accents and repeated whitespace."""
        result = normalize_patient_name("  María   López  ")
        self.assertEqual(result, "maria lopez")

    def test_normalize_patient_identifier_returns_slug(self) -> None:
        """Patient identifiers should become stable lowercase slugs."""
        result = normalize_patient_identifier(" Historial 001 / A ")
        self.assertEqual(result, "historial-001-a")


class JsonPatientStoreTests(unittest.TestCase):
    """Exercise creation and update flows for the JSON patient store."""

    def setUp(self) -> None:
        """Create an isolated temporary storage directory for each test."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store = JsonPatientStore(base_path=self.temp_dir.name)
        self.patient_context = PatientContext(
            patient_id="paciente-001",
            patient_name="Ana Perez",
            patient_name_normalized="ana perez",
            patient_identifier_raw="Paciente 001",
            medical_history="asma",
        )

    def tearDown(self) -> None:
        """Dispose of the temporary directory backing the store."""
        self.temp_dir.cleanup()

    def test_save_summary_creates_patient_file(self) -> None:
        """Saving the first session should create a JSON file on disk."""
        result = SummaryResult(
            summary="Resumen breve",
            visit_reason="Dolor abdominal",
            keypoints=["fiebre", "malestar"],
            model="llama3.2:3b",
            patient_id="paciente-001",
            session_id="session-1",
        )

        self.store.save_summary(self.patient_context, "texto transcrito", result)

        path = Path(self.temp_dir.name) / "paciente-001.json"
        with path.open("r", encoding="utf-8") as file_handle:
            payload = json.load(file_handle)

        self.assertEqual(payload["patient_name"], "Ana Perez")
        self.assertEqual(len(payload["sessions"]), 1)
        self.assertEqual(payload["sessions"][0]["summary"], "Resumen breve")

    def test_save_summary_appends_new_session(self) -> None:
        """Saving twice for the same patient should append sessions in order."""
        first = SummaryResult("uno", "motivo uno", ["a"], "llama3.2:3b", "paciente-001", "s1")
        second = SummaryResult("dos", "motivo dos", ["b"], "llama3.2:3b", "paciente-001", "s2")

        self.store.save_summary(self.patient_context, "texto 1", first)
        record = self.store.save_summary(self.patient_context, "texto 2", second)

        self.assertEqual(len(record.sessions), 2)
        self.assertEqual(record.sessions[-1].session_id, "s2")

    def test_list_patients_returns_summary_metadata(self) -> None:
        """The patient list should expose lightweight data for the histories view."""
        result = SummaryResult("uno", "motivo", ["clave"], "llama3.2:3b", "paciente-001", "s1")
        self.store.save_summary(self.patient_context, "texto 1", result)

        patients = self.store.list_patients()

        self.assertEqual(len(patients), 1)
        self.assertEqual(patients[0]["patient_id"], "paciente-001")
        self.assertEqual(patients[0]["session_count"], 1)
        self.assertTrue(patients[0]["last_session_at"])

    def test_update_session_persists_manual_edits(self) -> None:
        """Manual edits should update the stored transcript, summary and keypoints."""
        result = SummaryResult("uno", "motivo", ["clave"], "llama3.2:3b", "paciente-001", "s1")
        self.store.save_summary(self.patient_context, "texto original", result)

        edited_context = PatientContext(
            patient_id="paciente-001",
            patient_name="Ana Perez Actualizada",
            patient_name_normalized="ana perez actualizada",
            patient_identifier_raw="Paciente 001",
            visit_reason="motivo revisado",
        )
        session = self.store.update_session(
            patient_id="paciente-001",
            session_id="s1",
            patient_context=edited_context,
            transcript="texto corregido",
            summary="resumen corregido",
            visit_reason="motivo revisado",
            keypoints=["uno", "dos"],
            model="llama3.2:3b",
        )

        self.assertEqual(session.transcript, "texto corregido")
        self.assertEqual(session.summary, "resumen corregido")
        self.assertEqual(session.keypoints, ["uno", "dos"])

        record = self.store.get_patient_record("paciente-001")
        assert record is not None
        self.assertEqual(record.patient_name, "Ana Perez Actualizada")
        self.assertEqual(record.sessions[0].updated_at, session.updated_at)
