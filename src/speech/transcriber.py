"""Local microphone recording and Whisper transcription."""

from __future__ import annotations

import tempfile
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import sounddevice as sd
import whisper


@dataclass(slots=True)
class SpeechToText:
    """Capture speech from the microphone and return a transcribed string."""

    model_name: str = "base"
    language: str | None = "es"
    sample_rate: int = 16_000
    channels: int = 1
    _model: Any = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._model = whisper.load_model(self.model_name)

    def listen(self, seconds: float = 5.0) -> str:
        """Record audio from the default microphone and transcribe it."""
        audio_path = self.record_to_temp_wav(seconds)
        try:
            return self.transcribe_file(audio_path)
        finally:
            audio_path.unlink(missing_ok=True)

    def record_to_temp_wav(self, seconds: float) -> Path:
        """Record microphone input into a temporary WAV file."""
        if seconds <= 0:
            raise ValueError("Recording duration must be greater than 0 seconds.")

        print(f"Grabando durante {seconds:g} segundos...")
        recording = sd.rec(
            int(seconds * self.sample_rate),
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="int16",
        )
        sd.wait()

        temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        temp_path = Path(temp_file.name)
        temp_file.close()

        with wave.open(str(temp_path), "wb") as wav_file:
            wav_file.setnchannels(self.channels)
            wav_file.setsampwidth(2)
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(recording.tobytes())

        return temp_path

    def transcribe_file(self, audio_path: str | Path) -> str:
        """Transcribe an existing audio file with Whisper."""
        audio = self._load_wav_audio(Path(audio_path))
        return self.transcribe_audio(audio)

    def transcribe_audio(self, audio: np.ndarray) -> str:
        """Transcribe a 16 kHz mono audio array with Whisper."""
        options: dict[str, Any] = {"fp16": False}
        if self.language:
            options["language"] = self.language

        result = self._model.transcribe(audio, **options)
        return str(result["text"]).strip()

    def _load_wav_audio(self, audio_path: Path) -> np.ndarray:
        """Load a 16-bit PCM WAV file without requiring ffmpeg."""
        try:
            with wave.open(str(audio_path), "rb") as wav_file:
                channels = wav_file.getnchannels()
                sample_width = wav_file.getsampwidth()
                frame_rate = wav_file.getframerate()
                frames = wav_file.readframes(wav_file.getnframes())
        except wave.Error as exc:
            raise RuntimeError(
                "Only 16 kHz WAV files can be transcribed without ffmpeg. "
                "Install ffmpeg to transcribe other audio formats."
            ) from exc

        if sample_width != 2:
            raise ValueError("Only 16-bit PCM WAV files are supported without ffmpeg.")
        if frame_rate != self.sample_rate:
            raise ValueError(
                f"Expected a {self.sample_rate} Hz WAV file, got {frame_rate} Hz."
            )

        audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
        if channels > 1:
            audio = audio.reshape(-1, channels).mean(axis=1)

        return audio
