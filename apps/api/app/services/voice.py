"""Speech to text for the assistant, on this server, with a free multilingual Whisper model.

Shopkeepers often prefer to speak, in Hindi, Hinglish or English. The browser records a few seconds, turns
them into 16 kHz mono 16-bit WAV (so the server needs no audio converter), and sends it here. We:

- check the clip (length, loudness) and refuse silence instead of letting the model invent words;
- run faster-whisper (CTranslate2, int8, CPU) with a language hint, voice-activity detection and a short
  domain prompt, and with "transcribe" only (never translate);
- drop the known silence hallucinations and any answer in a script the shop does not use;
- return the text. The browser shows it for the person to confirm, and only then asks the question.

Audio lives in memory for the request and is never written to disk or logged. Whisper is MIT (code and weights).
See docs/VOICE.md for limits and measured results.
"""

import importlib.util
import io
import logging
import re
import sys
import threading
import time
import types
import wave
from dataclasses import dataclass
from typing import Any

import numpy as np

from app.core.config import Settings
from app.core.errors import AppError

SAMPLE_RATE = 16_000
MIN_SECONDS = 0.5
MIN_RMS = 0.004  # below this the clip is treated as silence (full scale is 1.0)

LANGUAGES = {"hi": "Hindi", "en": "English", "mr": "Marathi", "gu": "Gujarati"}
# A few words in the right script nudge the model toward our vocabulary. Kept short: a long prompt leaks into output.
PROMPTS = {
    "hi": "बिक्री, स्टॉक, मुनाफ़ा, उधार, ग्राहक, बिल, GST",
    "en": "sales, stock, profit, udhaar, customers, bill, GST",
    "mr": "विक्री, स्टॉक, नफा, उधार, ग्राहक, बिल",
    "gu": "વેચાણ, સ્ટોક, નફો, ઉધાર, ગ્રાહક, બિલ",
}
# What Whisper tends to say when there is nothing to transcribe (it learned these from subtitles).
HALLUCINATIONS = (
    "thanks for watching", "thank you for watching", "please subscribe", "like and subscribe",
    "subtitles by", "subtitles", "amara.org", "www.", "बीट्स", "सब्सक्राइब", "धन्यवाद दोस्तों", "देखने के लिए धन्यवाद",
)  # fmt: skip
_DEVANAGARI = re.compile(r"[ऀ-ॿ]")
_ARABIC = re.compile(r"[؀-ۿ]")
_LATIN = re.compile(r"[A-Za-z]")


class VoiceUnavailable(AppError):
    status_code = 503
    code = "voice_unavailable"


@dataclass(slots=True)
class Transcript:
    text: str
    language: str
    seconds: float
    ms: int
    reason: str | None = None  # why the text is empty: silence | too_short | not_understood
    confidence: float | None = None  # mean token probability, 0-1; None when empty


def decode_wav(data: bytes, max_seconds: int) -> np.ndarray:
    """16-bit PCM WAV (any channels, any rate) to mono float32 at 16 kHz. Anything else is refused."""
    try:
        with wave.open(io.BytesIO(data)) as w:
            if w.getsampwidth() != 2 or w.getcomptype() != "NONE":
                raise AppError("Send 16-bit PCM WAV audio")
            rate, channels, frames = w.getframerate(), w.getnchannels(), w.getnframes()
            if rate < 8_000 or rate > 48_000 or channels > 2:
                raise AppError("Send mono or stereo audio between 8 and 48 kHz")
            if frames / rate > max_seconds + 0.5:
                raise AppError(f"Speak for at most {max_seconds} seconds")
            raw = w.readframes(frames)
    except (wave.Error, EOFError) as exc:
        raise AppError("That is not a readable WAV recording") from exc
    pcm = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    if channels == 2:
        pcm = pcm.reshape(-1, 2).mean(axis=1)
    if rate != SAMPLE_RATE and pcm.size:
        n = round(pcm.size * SAMPLE_RATE / rate)
        pcm = np.interp(np.linspace(0, pcm.size - 1, n), np.arange(pcm.size), pcm).astype(
            np.float32
        )
    return pcm


def rms(audio: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(audio)))) if audio.size else 0.0


def clean(text: str, language: str) -> str:
    """Remove silence hallucinations and text in a script this shop does not use; '' when nothing is left."""
    t = " ".join(text.split()).strip()
    low = t.lower()
    if not t or any(h in low for h in HALLUCINATIONS):
        return ""
    letters = [c for c in t if c.isalpha()]
    if letters and sum(bool(_ARABIC.match(c)) for c in letters) / len(letters) > 0.3:
        return ""  # Urdu/Arabic script: a language mix-up, not something this shop said
    if language == "hi" and not (_DEVANAGARI.search(t) or _LATIN.search(t)):
        return ""
    # a phrase repeated over and over is the model looping
    words = low.split()
    if len(words) >= 8 and len(set(words)) <= len(words) // 4:
        return ""
    return t


_model: Any = None
_lock = threading.Lock()  # one model, one inference at a time: CPU decoding is not shared safely


def _stand_in_for_pyav() -> None:
    """faster-whisper imports PyAV to read audio *files*; we pass it samples and never use it.

    PyAV's wheels bundle GPL codecs, which this project's licence rule excludes, so it is not installed.
    If it is missing, a stub lets faster-whisper import; any attempt to actually use it fails loudly.
    """
    if "av" in sys.modules or importlib.util.find_spec("av") is not None:
        return
    stub = types.ModuleType("av")

    def _unavailable(name: str) -> Any:
        raise RuntimeError("PyAV is not installed; pass audio as samples, not as a file")

    stub.__dict__["__getattr__"] = _unavailable
    sys.modules["av"] = stub


def _load(settings: Settings) -> Any:
    global _model
    if _model is None:
        try:
            _stand_in_for_pyav()
            from faster_whisper import WhisperModel

            _model = WhisperModel(
                settings.stt_model,
                device="cpu",
                compute_type=settings.stt_compute_type,
                cpu_threads=settings.stt_cpu_threads,
                local_files_only=settings.stt_local_files_only,
            )
        except Exception as exc:  # missing package, weights not downloaded, no network
            raise VoiceUnavailable(
                "Voice is not set up on this server (the speech model could not be loaded)."
            ) from exc
    return _model


def warm(settings: Settings) -> None:
    """Load the model ahead of the first question. Failure is fine: the first request reports it."""
    try:
        with _lock:
            _load(settings)
    except VoiceUnavailable:
        logging.getLogger(__name__).warning(
            "Speech model not loaded at startup; voice will report it"
        )


def transcribe(audio: np.ndarray, language: str, settings: Settings) -> Transcript:
    t0 = time.perf_counter()
    seconds = audio.size / SAMPLE_RATE
    lang = language if language in LANGUAGES else "hi"

    def done(text: str, reason: str | None, conf: float | None = None) -> Transcript:
        ms = round((time.perf_counter() - t0) * 1000)
        return Transcript(text, lang, round(seconds, 2), ms, reason, conf)

    if seconds < MIN_SECONDS:
        return done("", "too_short")
    if rms(audio) < MIN_RMS:
        return done("", "silence")
    with _lock:
        model = _load(settings)
        segments, _info = model.transcribe(
            audio,
            language=lang,
            task="transcribe",
            beam_size=2,
            temperature=0.0,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 400, "speech_pad_ms": 300},
            initial_prompt=PROMPTS[lang],
            condition_on_previous_text=False,
            no_speech_threshold=0.6,
            log_prob_threshold=-1.0,
            compression_ratio_threshold=2.4,
        )
        parts = list(segments)
    text = clean(" ".join(s.text for s in parts), lang)
    if text and text.strip(" ,.।") == PROMPTS[lang].strip(" ,.।"):
        text = ""  # the model echoed the prompt
    if not text:
        return done("", "silence" if not parts else "not_understood")
    probs = [float(np.exp(s.avg_logprob)) for s in parts if s.avg_logprob is not None]
    return done(text, None, round(sum(probs) / len(probs), 2) if probs else None)
