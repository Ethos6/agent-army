"""Speech in, speech out over any OpenAI-compatible audio API (stdlib multipart, no SDK).

Env: OPENAI_API_KEY, optional OPENAI_BASE_URL, ARMY_STT_MODEL (default whisper-1),
ARMY_TTS_MODEL (default tts-1), ARMY_TTS_VOICE (default alloy).
"""
from __future__ import annotations

import json
import os
import urllib.request
import uuid

from .agent import tool
from .llm import LLMError, _key
from .tools import outputs_dir, safe_path


def _base() -> str:
    return os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")


def transcribe(path: str) -> str:
    p = safe_path(path)
    boundary = uuid.uuid4().hex
    model = os.environ.get("ARMY_STT_MODEL", "whisper-1")
    body = (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"model\"\r\n\r\n{model}\r\n"
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{p.name}\"\r\n"
        "Content-Type: application/octet-stream\r\n\r\n"
    ).encode() + p.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        f"{_base()}/audio/transcriptions", data=body, method="POST",
        headers={"authorization": f"Bearer {_key('OPENAI_API_KEY')}", "content-type": f"multipart/form-data; boundary={boundary}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return json.loads(r.read())["text"]
    except urllib.error.HTTPError as e:
        raise LLMError(f"transcription failed: HTTP {e.code} {e.read()[:300]!r}") from None


def speak(text: str, filename: str = "speech.mp3") -> str:
    payload = {
        "model": os.environ.get("ARMY_TTS_MODEL", "tts-1"),
        "voice": os.environ.get("ARMY_TTS_VOICE", "alloy"),
        "input": text[:4000],
    }
    req = urllib.request.Request(
        f"{_base()}/audio/speech", data=json.dumps(payload).encode(), method="POST",
        headers={"authorization": f"Bearer {_key('OPENAI_API_KEY')}", "content-type": "application/json"},
    )
    out = outputs_dir() / os.path.basename(filename)
    with urllib.request.urlopen(req, timeout=300) as r:
        out.write_bytes(r.read())
    return str(out)


@tool
def transcribe_audio(path: str) -> str:
    """Transcribe an audio file (mp3, wav, m4a, webm) to text."""
    return transcribe(path)


@tool
def text_to_speech(text: str, filename: str = "speech.mp3") -> str:
    """Turn text into a spoken MP3 saved in outputs/. Returns the file path."""
    return "saved " + speak(text, filename)
