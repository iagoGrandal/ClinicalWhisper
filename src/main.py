from __future__ import annotations

import argparse


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for local microphone transcription."""
    parser = argparse.ArgumentParser(
        description="Record audio from the microphone and transcribe it locally with Whisper."
    )
    parser.add_argument(
        "-d",
        "--duration",
        type=float,
        default=5.0,
        help="Recording duration in seconds. Default: 5.",
    )
    parser.add_argument(
        "-m",
        "--model",
        default="base",
        help="Whisper model to use: tiny, base, small, medium, large. Default: base.",
    )
    parser.add_argument(
        "-l",
        "--language",
        default="es",
        help="Spoken language code. Use an empty value for auto-detection. Default: es.",
    )
    return parser.parse_args()


def main() -> None:
    """Run the local Whisper transcription workflow from the command line."""
    args = parse_args()
    language = args.language or None

    if __package__:
        from .speech import SpeechToText
    else:
        from speech import SpeechToText

    transcriber = SpeechToText(model_name=args.model, language=language)
    text = transcriber.listen(seconds=args.duration)

    print("\nTranscripcion:")
    print(text)


if __name__ == "__main__":
    main()
