"""Measure the voice pipeline end to end on synthetic speech (macOS only: uses `say` and `afconvert`).

    cd apps/api && .venv/bin/python ../../scripts/eval_voice.py

Speech is made by the built-in macOS voices (Lekha for Hindi, Rishi for Indian English), so this is a
smoke test and a regression check, NOT a measure of how real shopkeepers will be understood: synthetic voices
are clean, evenly paced and accent-free. Recordings are made in a temporary folder and deleted; nothing is saved.
Reported: transcript, whether the question reached the intended intent, seconds to transcribe, and how often
silence or noise produced words (hallucination).
"""

import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "api"))
from datetime import date  # noqa: E402

from app.core.config import Settings  # noqa: E402
from app.services import voice  # noqa: E402
from app.services.assistant import nlu  # noqa: E402

# (voice, language hint, spoken text, acceptable intents)
CASES = [
    ("Lekha", "hi", "आज की बिक्री कितनी हुई", {"sales"}),
    ("Lekha", "hi", "पिछले हफ्ते की बिक्री बताओ", {"sales"}),
    ("Lekha", "hi", "किस किस से पैसा लेना है", {"udhaar"}),
    ("Lekha", "hi", "कौन सा माल खत्म होने वाला है", {"stock"}),
    ("Lekha", "hi", "कौन सा सामान नहीं बिक रहा", {"slow_products", "dead_stock"}),
    ("Lekha", "hi", "इस हफ्ते क्या मंगवाना चाहिए", {"recommend", "stock"}),
    ("Lekha", "hi", "मुनाफा कितना है", {"margin"}),
    ("Lekha", "hi", "सबसे ज़्यादा क्या बिकता है", {"top_products"}),
    ("Lekha", "hi", "बिक्री क्यों गिरी", {"why"}),
    ("Lekha", "hi", "कौन सा त्योहार आ रहा है", {"festival"}),
    ("Lekha", "hi", "आज का stock कितना बचा है", {"stock"}),
    ("Lekha", "hi", "इस महीने की sales कितनी हुई", {"sales"}),
    ("Rishi", "en", "How much did I sell last week", {"sales"}),
    ("Rishi", "en", "Who owes me money", {"udhaar"}),
    ("Rishi", "en", "What will run out first", {"stock"}),
    ("Rishi", "en", "Show me the top five products", {"top_products"}),
    ("Rishi", "en", "What is my margin", {"margin"}),
]


def speak(voice_name: str, text: str, folder: Path, i: int) -> np.ndarray:
    aiff, wav = folder / f"{i}.aiff", folder / f"{i}.wav"
    subprocess.run(["say", "-v", voice_name, "-o", str(aiff), text], check=True)
    subprocess.run(
        ["afconvert", "-f", "WAVE", "-d", "LEI16@16000", "-c", "1", str(aiff), str(wav)], check=True
    )
    return voice.decode_wav(wav.read_bytes(), 15)


def pad(clip: np.ndarray, seconds: float = 0.4) -> np.ndarray:
    gap = np.zeros(int(voice.SAMPLE_RATE * seconds), dtype=np.float32)
    return np.concatenate([gap, clip, gap])


def with_noise(clip: np.ndarray, snr_db: float, rng: np.random.Generator) -> np.ndarray:
    noise = rng.normal(0, 1, clip.size).astype(np.float32)
    noise *= voice.rms(clip) / (10 ** (snr_db / 20)) / max(voice.rms(noise), 1e-9)
    return np.clip(clip + noise, -1, 1)


def main() -> None:
    settings = Settings(app_env="test")
    rng = np.random.default_rng(7)
    rows: list[tuple[str, str, str, bool, float]] = []
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        voice.transcribe(np.zeros(16_000, dtype=np.float32) + 0.1, "hi", settings)  # load the model once
        for cond, snr in (("clean", None), ("noisy 10 dB", 10.0)):
            for i, (vn, lang, text, want) in enumerate(CASES):
                clip = pad(speak(vn, text, folder, i))
                if snr is not None:
                    clip = with_noise(clip, snr, rng)
                t = voice.transcribe(clip, lang, settings)
                intent = nlu.route(t.text, date.today()).intent if t.text else "(empty)"
                rows.append((cond, text, t.text or f"[{t.reason}]", intent in want, t.ms / 1000))
        # silence and noise: the model must say nothing
        junk = {
            "digital silence 4 s": np.zeros(64_000, dtype=np.float32),
            "room hiss": rng.normal(0, 0.01, 64_000).astype(np.float32),
            "loud noise": rng.normal(0, 0.15, 64_000).astype(np.float32),
            "hum": (0.1 * np.sin(2 * np.pi * 120 * np.arange(64_000) / 16_000)).astype(np.float32),
        }
        said = {name: voice.transcribe(c, "hi", settings).text for name, c in junk.items()}

    for cond in ("clean", "noisy 10 dB"):
        sub = [r for r in rows if r[0] == cond]
        ok = sum(r[3] for r in sub)
        times = [r[4] for r in sub]
        print(f"\n## {cond}: right intent {ok}/{len(sub)}; seconds per clip median {statistics.median(times):.1f}, max {max(times):.1f}")
        for _, text, heard, good, s in sub:
            print(f"{'ok ' if good else 'BAD'} | {text} | {heard} | {s:.1f}s")
    print("\n## silence and noise (the right answer is nothing)")
    for name, text in said.items():
        print(f"{'ok ' if not text else 'BAD'} | {name} | {text!r}")


if __name__ == "__main__":
    main()
