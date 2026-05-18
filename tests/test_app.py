"""Integration-style tests for the Flask summarize endpoint."""

from __future__ import annotations

import tempfile
import unittest
from unittest.mock import patch

from app import app
from src.summarize import JsonPatientStore
from src.summarize.service import ClinicalSummarizer


class FakeModelClient:
    """Minimal Ollama-compatible client used to avoid real model calls in tests."""

    def __init__(self) -> None:
        """Prepare deterministic chunk and final responses."""
        self.chat_calls = 0

    def list(self):  # noqa: ANN201
        """Return one local model entry for the selector."""
        class Model:
            """Simple stand-in for the Ollama model object."""

            def __init__(self, model: str) -> None:
                """Store the model name for test assertions."""
                self.model = model

        class Response:
            """Simple stand-in for the Ollama list response."""

            def __init__(self) -> None:
                """Expose one fake local model."""
                self.models = [Model("llama3.2:3b")]

        return Response()

    def chat(self, model: str, messages: list[dict[str, str]], format: str, options: dict[str, int]):  # noqa: A002
        """Return valid JSON for chunk and final summarization stages."""
        del model, messages, format, options
        self.chat_calls += 1

        class Message:
            """Simple stand-in for the Ollama message object."""

            def __init__(self, content: str) -> None:
                """Store deterministic content for the fake response."""
                self.content = content

        class Response:
            """Simple stand-in for the Ollama chat response."""

            def __init__(self, content: str) -> None:
                """Expose a message payload compatible with the real client."""
                self.message = Message(content)

        if self.chat_calls == 1:
            return Response('{"summary":"bloque","keypoints":["fiebre","tos"]}')
        return Response(
            '{"summary":"Resumen global","visit_reason":"Fiebre y tos","keypoints":["fiebre","tos"]}'
        )


class SummarizeEndpointTests(unittest.TestCase):
    """Validate the Flask endpoint contract around summarization."""

    def setUp(self) -> None:
        """Create a test client and isolated summarizer storage."""
        self.temp_dir = tempfile.TemporaryDirectory()
        fake_client = FakeModelClient()
        self.summarizer = ClinicalSummarizer(
            client=fake_client,
            store=JsonPatientStore(base_path=self.temp_dir.name),
        )
        self.client = app.test_client()

    def tearDown(self) -> None:
        """Dispose of isolated storage after each test."""
        self.temp_dir.cleanup()

    def seed_saved_session(self) -> dict[str, object]:
        """Create one stored consultation that can be reused across API tests."""
        return self.summarizer.summarize_consultation(
            {
                "patientName": "Ana Perez",
                "patientDni": "12345678A",
                "visitDate": "2026-05-16",
                "transcript": "Paciente con fiebre y tos desde ayer.",
                "model": "llama3.2:3b",
            }
        )

    def test_summarize_endpoint_returns_structured_payload(self) -> None:
        """A valid request should return structured summary JSON."""
        payload = {
            "patientName": "Ana Perez",
            "patientDni": "12345678A",
            "transcript": "Paciente con fiebre y tos desde ayer.",
            "model": "llama3.2:3b",
        }

        with patch("app.get_summarizer", return_value=self.summarizer):
            response = self.client.post("/summarize", json=payload)

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["visit_reason"], "Fiebre y tos")
        self.assertEqual(data["keypoints"], ["fiebre", "tos"])
        self.assertTrue(data["saved"])

    def test_summarize_endpoint_rejects_missing_patient_name(self) -> None:
        """Missing required patient fields should return a 400 response."""
        payload = {
            "patientName": "",
            "patientDni": "12345678A",
            "transcript": "Paciente con fiebre y tos desde ayer.",
            "model": "llama3.2:3b",
        }

        with patch("app.get_summarizer", return_value=self.summarizer):
            response = self.client.post("/summarize", json=payload)

        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn("nombre del paciente", data["error"])

    def test_summarize_endpoint_rejects_missing_patient_dni(self) -> None:
        """DNI is required because it is used as the patient identifier."""
        payload = {
            "patientName": "Ana Perez",
            "patientDni": "",
            "transcript": "Paciente con fiebre y tos desde ayer.",
            "model": "llama3.2:3b",
        }

        with patch("app.get_summarizer", return_value=self.summarizer):
            response = self.client.post("/summarize", json=payload)

        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn("DNI del paciente", data["error"])

    def test_patients_history_endpoints_return_saved_records(self) -> None:
        """Saved consultations should be exposed through the history APIs."""
        saved = self.seed_saved_session()

        with patch("app.get_summarizer", return_value=self.summarizer):
            patients_response = self.client.get("/api/patients")
            patient_response = self.client.get("/api/patients/12345678a")
            session_response = self.client.get(f"/api/patients/12345678a/sessions/{saved['session_id']}")

        self.assertEqual(patients_response.status_code, 200)
        self.assertEqual(patient_response.status_code, 200)
        self.assertEqual(session_response.status_code, 200)

        patients = patients_response.get_json()["patients"]
        self.assertEqual(len(patients), 1)
        self.assertEqual(patients[0]["patient_name"], "Ana Perez")

        patient = patient_response.get_json()["patient"]
        self.assertEqual(patient["patient_identifier_raw"], "12345678A")
        self.assertEqual(patient["prefill"]["patientName"], "Ana Perez")
        self.assertEqual(patient["prefill"]["patientDni"], "12345678A")
        self.assertEqual(len(patient["sessions"]), 1)

        session = session_response.get_json()["session"]
        self.assertEqual(session["transcript"], "Paciente con fiebre y tos desde ayer.")
        self.assertEqual(session["visit_reason"], "Fiebre y tos")

    def test_history_endpoints_allow_resummarizing_and_saving_session(self) -> None:
        """The edit flow should support previewing a new summary and saving the final session."""
        saved = self.seed_saved_session()
        payload = {
            "patientName": "Ana Perez Revisada",
            "patientDni": "12345678A",
            "visitDate": "2026-05-17",
            "visitReason": "Consulta revisada",
            "transcript": "Paciente con fiebre, tos y cansancio desde hace dos dias.",
            "summary": "Resumen manual",
            "keypoints": ["fiebre", "cansancio"],
            "model": "llama3.2:3b",
        }

        with patch("app.get_summarizer", return_value=self.summarizer):
            preview_response = self.client.post("/api/sessions/resummarize", json=payload)
            save_response = self.client.put(
                f"/api/patients/12345678a/sessions/{saved['session_id']}",
                json=payload,
            )

        self.assertEqual(preview_response.status_code, 200)
        preview = preview_response.get_json()
        self.assertFalse(preview["saved"])
        self.assertEqual(preview["visit_reason"], "Fiebre y tos")

        self.assertEqual(save_response.status_code, 200)
        saved_session = save_response.get_json()["session"]
        self.assertEqual(saved_session["transcript"], payload["transcript"])
        self.assertEqual(saved_session["patient_context"]["patient_name"], "Ana Perez Revisada")
        self.assertEqual(saved_session["patient_context"]["visit_date"], "2026-05-17")

    def test_delete_patient_endpoint_removes_record(self) -> None:
        """Deleting a patient should remove every stored session from the API."""
        self.seed_saved_session()

        with patch("app.get_summarizer", return_value=self.summarizer):
            delete_response = self.client.delete("/api/patients/12345678a")
            patients_response = self.client.get("/api/patients")
            patient_response = self.client.get("/api/patients/12345678a")

        self.assertEqual(delete_response.status_code, 200)
        deleted = delete_response.get_json()
        self.assertTrue(deleted["deleted"])
        self.assertEqual(deleted["session_count"], 1)

        self.assertEqual(patients_response.status_code, 200)
        self.assertEqual(patients_response.get_json()["patients"], [])

        self.assertEqual(patient_response.status_code, 404)
