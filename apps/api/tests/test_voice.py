"""Voice: audio checks, silence and hallucination handling, and the endpoint (model faked)."""

import io
import wave
from collections.abc import Callable, Iterator
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.core import hardening
from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.services import voice

Make = Callable[[str], dict[str, str]]


def wav(seconds: float = 2.0, rate: int = 16_000, channels: int = 1, amp: float = 0.2) -> bytes:
    t = np.arange(int(seconds * rate)) / rate
    tone = (np.sin(2 * np.pi * 220 * t) * amp * 32767).astype("<i2")
    if channels == 2:
        tone = np.repeat(tone, 2)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(tone.tobytes())
    return buf.getvalue()


class FakeModel:
    def __init__(self, text: str = "आज की बिक्री कितनी है", logprob: float = -0.2) -> None:
        self.text, self.logprob = text, logprob
        self.calls: list[dict[str, Any]] = []

    def transcribe(self, audio: Any, **kw: Any):
        self.calls.append(kw)
        seg = SimpleNamespace(text=self.text, avg_logprob=self.logprob)
        return [seg] if self.text else [], SimpleNamespace()


@pytest.fixture
def fake(monkeypatch: pytest.MonkeyPatch) -> FakeModel:
    m = FakeModel()
    monkeypatch.setattr(voice, "_model", m)
    return m


def test_decode_mono_stereo_and_other_rates() -> None:
    assert voice.decode_wav(wav(1.0), 15).size == 16_000
    assert voice.decode_wav(wav(1.0, channels=2), 15).size == 16_000
    assert voice.decode_wav(wav(1.0, rate=44_100), 15).size == 16_000  # resampled


@pytest.mark.parametrize("bad", [b"", b"not audio", b"RIFF" + b"\x00" * 40])
def test_decode_rejects_unreadable_audio(bad: bytes) -> None:
    with pytest.raises(AppError):
        voice.decode_wav(bad, 15)


def test_decode_rejects_long_clips() -> None:
    with pytest.raises(AppError, match="at most 3 seconds"):
        voice.decode_wav(wav(5.0), 3)


def test_silence_and_short_clips_never_reach_the_model(fake: FakeModel) -> None:
    quiet = voice.transcribe(np.zeros(32_000, dtype=np.float32), "hi", Settings())
    assert (quiet.text, quiet.reason) == ("", "silence")
    short = voice.transcribe(np.full(2_000, 0.3, dtype=np.float32), "hi", Settings())
    assert (short.text, short.reason) == ("", "too_short")
    assert fake.calls == []


def test_transcribe_passes_the_safety_settings(fake: FakeModel) -> None:
    clip = voice.decode_wav(wav(2.0), 15)
    out = voice.transcribe(clip, "hi", Settings())
    assert out.text == "आज की बिक्री कितनी है" and out.reason is None
    kw = fake.calls[0]
    assert kw["language"] == "hi" and kw["task"] == "transcribe" and kw["vad_filter"] is True
    assert kw["condition_on_previous_text"] is False and "बिक्री" in kw["initial_prompt"]
    assert 0 < (out.confidence or 0) <= 1


def test_unknown_language_falls_back_to_hindi(fake: FakeModel) -> None:
    voice.transcribe(voice.decode_wav(wav(1.0), 15), "xx", Settings())
    assert fake.calls[0]["language"] == "hi"


@pytest.mark.parametrize(
    "text",
    [
        "Thanks for watching!",
        "Subtitles by the Amara.org community",
        "بیچنے کی رقم کیا ہے",  # Arabic script: a language mix-up
        " ".join(["यह वही है"] * 6),  # looping
        "",
    ],
)
def test_hallucinations_and_wrong_scripts_become_empty(text: str) -> None:
    assert voice.clean(text, "hi") == ""


def test_real_questions_survive_cleaning() -> None:
    for q in (
        "आज की बिक्री कितनी है",
        "aaj ki bikri kitni hai",
        "Who owes me money?",
        "स्टॉक कितना बचा",
    ):
        assert voice.clean(q, "hi") == q


def test_prompt_echo_is_dropped(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(voice, "_model", FakeModel(voice.PROMPTS["hi"]))
    out = voice.transcribe(voice.decode_wav(wav(2.0), 15), "hi", Settings())
    assert out.text == "" and out.reason == "not_understood"


@pytest.fixture
def with_voice(client: TestClient) -> Iterator[Callable[..., Settings]]:
    def _set(**kw: Any) -> Settings:
        s = Settings(app_env="test", **kw)
        client.app.dependency_overrides[get_settings] = lambda: s  # type: ignore[attr-defined]
        return s

    yield _set
    client.app.dependency_overrides.pop(get_settings, None)  # type: ignore[attr-defined]


def _shop(client: TestClient, h: dict[str, str]) -> str:
    return str(client.post("/api/v1/workspaces", json={"name": "Shop"}, headers=h).json()["id"])


def _post(client: TestClient, ws: str, h: dict[str, str], data: bytes, lang: str = "hi"):
    return client.post(
        f"/api/v1/workspaces/{ws}/assistant/voice",
        files={"audio": ("q.wav", data, "audio/wav")},
        data={"language": lang},
        headers=h,
    )


def test_voice_endpoint_returns_text_and_never_the_audio(
    client: TestClient, make_user: Make, fake: FakeModel
) -> None:
    h = make_user("o@x.com")
    ws = _shop(client, h)
    r = _post(client, ws, h, wav(2.0))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["text"] == "आज की बिक्री कितनी है" and body["reason"] is None
    assert set(body) == {"text", "language", "seconds", "ms", "reason", "confidence"}


def test_voice_requires_membership_and_valid_input(
    client: TestClient, make_user: Make, fake: FakeModel
) -> None:
    owner, other = make_user("o@x.com"), make_user("x@x.com")
    ws = _shop(client, owner)
    assert _post(client, ws, other, wav()).status_code == 404
    assert _post(client, ws, owner, b"junk").status_code == 400
    assert _post(client, ws, owner, wav(), lang="fr").status_code == 422
    assert _post(client, ws, owner, wav(20.0)).status_code in (400, 413)


def test_voice_oversize_upload_is_refused_before_reading(
    client: TestClient, make_user: Make, fake: FakeModel
) -> None:
    h = make_user("o@x.com")
    ws = _shop(client, h)
    assert _post(client, ws, h, b"\x00" * (3 * 1024 * 1024)).status_code == 413


def test_voice_can_be_switched_off(
    client: TestClient, make_user: Make, with_voice: Callable[..., Settings]
) -> None:
    h = make_user("o@x.com")
    ws = _shop(client, h)
    with_voice(voice_enabled=False)
    r = _post(client, ws, h, wav())
    assert r.status_code == 503 and r.json()["error"]["code"] == "voice_unavailable"


def test_missing_model_gives_a_clear_503_not_a_crash(
    client: TestClient,
    make_user: Make,
    with_voice: Callable[..., Settings],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(voice, "_model", None)
    h = make_user("o@x.com")
    ws = _shop(client, h)
    with_voice(stt_model="no-such-model-folder", stt_local_files_only=True)
    r = _post(client, ws, h, wav())
    assert r.status_code == 503 and "not set up" in r.json()["error"]["message"]


def test_voice_is_rate_limited_like_other_heavy_routes(
    client: TestClient, make_user: Make, fake: FakeModel, monkeypatch: pytest.MonkeyPatch
) -> None:
    h = make_user("o@x.com")
    ws = _shop(client, h)
    monkeypatch.setattr(get_settings(), "heavy_rate_limit_per_minute", 2)
    hardening.reset()
    codes = [_post(client, ws, h, wav()).status_code for _ in range(4)]
    assert codes[:2] == [200, 200] and 429 in codes[2:]


def test_faster_whisper_imports_without_pyav_and_pyav_is_never_used() -> None:
    """PyAV bundles GPL codecs so it is not installed; a stub lets faster-whisper import."""
    voice._stand_in_for_pyav()
    import av
    import faster_whisper  # noqa: F401

    with pytest.raises(RuntimeError, match="PyAV is not installed"):
        av.open("x.wav")
