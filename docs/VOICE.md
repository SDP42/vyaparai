# Voice: ask in your own language

Many shopkeepers would rather speak than type, and speak Hindi or Hinglish. Tap the microphone on the Ask
page, say the question, check the words, and the answer comes back (and can be read aloud).
Research and rationale: [research/PERSONAS-VOICE.md](research/PERSONAS-VOICE.md).

## How it works

```
browser: tap → record → stops after a pause → 16 kHz mono WAV in the browser
   → POST /workspaces/{id}/assistant/voice            (own server; audio in memory only)
   → check length and loudness → faster-whisper (Whisper medium, int8, CPU) with a Hindi/English hint
   → drop silence "hallucinations", wrong scripts, prompt echoes
   → text back → shown for the person to confirm or fix → normal /ask (persona rules apply)
   → answer shown; optionally read aloud by the device's own voice
```

- **Speech to text**: [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (MIT) running the
  multilingual Whisper `medium` weights (MIT, `Systran/faster-whisper-medium`), int8 on CPU. Set `STT_MODEL`
  (`small` is about three times faster and lighter but mishears more; see the numbers below).
  Weights download on first use (about 1.5 GB for medium) or are pre-loaded at startup; set
  `STT_LOCAL_FILES_ONLY=true` on a server that must never fetch them.
- **Speech out**: the browser's own `speechSynthesis` (hi-IN / en-IN). No server voice, so no extra licence
  or cost. If the phone has no voice for the language the page says so and the answer stays text.
- **Never acts on a transcript alone**: the words are shown first ("I heard: …") and can be edited.
  Only the question is asked, which only reads data.
- **Privacy**: audio is processed in memory and discarded; it is not written to disk or logged, neither are the
  words. Nothing is sent to a third party. A request over about 1 MB is refused before it is read, and the
  route shares the "heavy" per-address rate limit.

## Guards against Whisper's known failure modes

| Failure | What we do |
|---|---|
| Invents words on silence or noise ("thanks for watching") | Refuse clips under 0.5 s or too quiet; voice-activity detection; no-speech and log-probability thresholds; blocklist; looping-text check |
| Writes Hindi in Urdu script or translates | Language is forced from the page language; `task=transcribe`; Arabic-script output is discarded |
| Misses our words | A short in-script domain prompt (sales, stock, profit, udhaar, GST); an echoed prompt is discarded |
| Spells Hindi by ear ("मुनाफ़", "कुन सा") | The question understanding matches on the consonant skeleton and allows one slip, and knows common Devanagari spellings of English words (सेल्स, प्रॉफिट). Typed words still need an exact match first |
| First request slow | The model is loaded when the server starts |

## Measured (synthetic speech, a smoke test, not a user study)

`scripts/eval_voice.py` makes speech with the macOS voices Lekha (Hindi) and Rishi (Indian English), 17 shop
questions, and counts how often the transcribed question reaches the right assistant intent. It also feeds four
kinds of silence and noise and counts words invented. On an Apple-silicon laptop:

| Model | Clean | Noisy (10 dB hiss) | Seconds per question (median) |
|---|---|---|---|
| Whisper small (int8) | 15 / 17 | 13 / 17 | 1.4 |
| **Whisper medium (int8), the default** | **17 / 17** | **15 / 17** | **4.3** |

Silence, hiss, loud noise and a hum: nothing was invented (0 of 4 clips, both models).

**These numbers are optimistic.** The voices are synthetic: clean, evenly paced, accent-free, and the speech
sets were also used while tuning the keyword matching, so they are a development set. Real shopkeepers speak
faster, with regional accents, background noise and half-words. Hindi spelling by Whisper is only phonetic. Before
trusting it, record 50-100 real questions in a real shop and measure again. Times on a small cloud server will be
higher than on this laptop.

## Not done yet

- Marathi, Gujarati, Tamil and Bengali speech (Whisper small/medium is weak there; the AI4Bharat IndicWhisper
  models are MIT-licensed and a better fit, but need conversion and a licence check of the exact checkpoint).
  The API accepts `hi`, `en`, `mr`, `gu` hints; only Hindi and English have been tested.
- Reading numbers back as words ("बारह हज़ार पाँच सौ") and a Hindi number parser for amounts.
- Matching spoken product names to the shop's catalogue with suggestions as buttons.
- A real-device test (iOS Safari recording, Android Chrome) and a user test with shopkeepers.
- Piper and similar offline TTS voices were rejected: current Piper is GPL-3.0 and the Hindi voices cite a
  non-commercial dataset licence.

## API

`POST /workspaces/{id}/assistant/voice` (multipart: `audio` = 16-bit PCM WAV up to 15 s, `language` = hi|en|mr|gu)
→ `{text, language, seconds, ms, reason, confidence}`. `reason` is `silence`, `too_short` or `not_understood` when
`text` is empty. 503 `voice_unavailable` when switched off (`VOICE_ENABLED=false`) or when the model cannot be loaded.
