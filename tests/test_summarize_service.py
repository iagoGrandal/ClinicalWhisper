"""Tests for transcript chunking and model response parsing."""

from __future__ import annotations

import unittest

from src.summarize.service import normalize_keypoints, parse_json_content, split_text_chunks


class SplitTextChunksTests(unittest.TestCase):
    """Check that transcript chunking is robust and order-preserving."""

    def test_split_text_chunks_returns_empty_for_blank_text(self) -> None:
        """Blank transcripts should not produce chunk entries."""
        self.assertEqual(split_text_chunks("   ", 120), [])

    def test_split_text_chunks_keeps_short_text_in_single_chunk(self) -> None:
        """Short transcripts should remain as a single chunk."""
        chunks = split_text_chunks("Paciente con fiebre y tos.", 120)
        self.assertEqual(chunks, ["Paciente con fiebre y tos."])

    def test_split_text_chunks_splits_long_text_preserving_order(self) -> None:
        """Long transcripts should split without losing sentence order."""
        text = (
            "Primera frase bastante extensa sobre el motivo de consulta. "
            "Segunda frase sobre antecedentes recientes. "
            "Tercera frase con evolucion de los sintomas."
        )
        chunks = split_text_chunks(text, 70)
        self.assertGreater(len(chunks), 1)
        self.assertIn("Primera frase", chunks[0])
        self.assertIn("Tercera frase", chunks[-1])


class ParseJsonContentTests(unittest.TestCase):
    """Validate structured parsing for Ollama responses."""

    def test_parse_json_content_accepts_valid_json(self) -> None:
        """A plain JSON object should parse directly."""
        payload = parse_json_content('{"summary":"ok","keypoints":["uno"]}')
        self.assertEqual(payload["summary"], "ok")

    def test_parse_json_content_extracts_wrapped_json(self) -> None:
        """Wrapped JSON should still be recoverable from the response body."""
        payload = parse_json_content('Respuesta:\n{"summary":"ok","keypoints":["uno"]}')
        self.assertEqual(payload["keypoints"], ["uno"])

    def test_normalize_keypoints_rejects_non_list_values(self) -> None:
        """Keypoints must be represented as a JSON list."""
        with self.assertRaises(ValueError):
            normalize_keypoints("no-lista")

    def test_normalize_keypoints_filters_empty_items(self) -> None:
        """Empty or blank keypoints should be discarded."""
        result = normalize_keypoints([" dolor  ", "", "  ", "fiebre"])
        self.assertEqual(result, ["dolor", "fiebre"])
