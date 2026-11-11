"use client";

import { Mic, Square } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, api } from "@/lib/api";
import { useT, type Lang } from "@/lib/i18n";
import { EndOfSpeech, encodeWav, rms, toMono16k } from "@/lib/wav";

type Phase = "idle" | "listening" | "working" | "confirm";
type Heard = { text: string; confidence: number | null; reason: string | null };

/**
 * Ask by voice. The person taps once and speaks; recording stops by itself after a pause. The recording is
 * turned into 16 kHz WAV here, sent to our own server for transcription, and shown back as words to confirm
 * or fix before anything is asked. Nothing is stored. Without a microphone, or without permission, the page
 * says so in plain words and typing keeps working.
 */
export function VoiceInput({ workspaceId, disabled, onAsk }: { workspaceId: string; disabled: boolean; onAsk: (text: string) => void }) {
  const { t, lang } = useT();
  const [phase, setPhase] = useState<Phase>("idle");
  const [level, setLevel] = useState(0);
  const [heard, setHeard] = useState<Heard | null>(null);
  const [text, setText] = useState("");
  const [notice, setNotice] = useState<string | null>(null);
  const [supported, setSupported] = useState(true);
  const stopRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    setSupported(typeof navigator !== "undefined" && Boolean(navigator.mediaDevices?.getUserMedia) && typeof MediaRecorder !== "undefined");
    return () => stopRef.current?.();
  }, []);

  const send = useCallback(
    async (blob: Blob) => {
      setPhase("working");
      try {
        const ctx = new AudioContext();
        const buf = await ctx.decodeAudioData(await blob.arrayBuffer());
        void ctx.close();
        const samples = toMono16k(Array.from({ length: buf.numberOfChannels }, (_, i) => buf.getChannelData(i)), buf.sampleRate);
        if (rms(samples) < 0.003) throw new Error("quiet");
        const form = new FormData();
        form.append("audio", new Blob([encodeWav(samples) as BlobPart], { type: "audio/wav" }), "question.wav");
        form.append("language", (lang as Lang) === "en" ? "en" : "hi");
        const r = await api<{ text: string; confidence: number | null; reason: string | null }>(`/workspaces/${workspaceId}/assistant/voice`, { method: "POST", body: form });
        if (!r.text) {
          setNotice(t("voice.none"));
          setPhase("idle");
          return;
        }
        setHeard(r);
        setText(r.text);
        setPhase("confirm");
      } catch (e) {
        setNotice(e instanceof ApiError && e.code === "voice_unavailable" ? t("voice.unavailable") : e instanceof ApiError ? e.message : t("voice.none"));
        setPhase("idle");
      }
    },
    [lang, t, workspaceId],
  );

  const start = useCallback(async () => {
    setNotice(null);
    setHeard(null);
    if (!supported) {
      setNotice(t("voice.unsupported"));
      return;
    }
    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true } });
    } catch {
      setNotice(t("voice.denied"));
      return;
    }
    const ctx = new AudioContext();
    const analyser = ctx.createAnalyser();
    analyser.fftSize = 1024;
    ctx.createMediaStreamSource(stream).connect(analyser);
    const frame = new Float32Array(analyser.fftSize);
    const recorder = new MediaRecorder(stream);
    const chunks: Blob[] = [];
    const eos = new EndOfSpeech(performance.now());
    let raf = 0;
    let done = false;
    const finish = () => {
      if (done) return;
      done = true;
      cancelAnimationFrame(raf);
      if (recorder.state !== "inactive") recorder.stop();
    };
    recorder.ondataavailable = (e) => e.data.size && chunks.push(e.data);
    recorder.onstop = () => {
      stream.getTracks().forEach((tr) => tr.stop());
      void ctx.close();
      stopRef.current = null;
      setLevel(0);
      if (!eos.heardSpeech) {
        setNotice(t("voice.none"));
        setPhase("idle");
        return;
      }
      void send(new Blob(chunks, { type: recorder.mimeType || "audio/webm" }));
    };
    const tick = () => {
      analyser.getFloatTimeDomainData(frame);
      const l = rms(frame);
      setLevel(Math.min(1, l * 8));
      if (eos.update(l, performance.now())) finish();
      else raf = requestAnimationFrame(tick);
    };
    stopRef.current = finish;
    recorder.start();
    setPhase("listening");
    raf = requestAnimationFrame(tick);
  }, [send, supported, t]);

  const ring = 1 + level * 0.35;
  return (
    <section aria-label="Ask by voice" className="rounded-2xl border border-line bg-surface p-4">
      {phase !== "confirm" && (
        <div className="flex items-center gap-4">
          <button
            type="button"
            onClick={phase === "listening" ? () => stopRef.current?.() : start}
            disabled={disabled || phase === "working"}
            aria-pressed={phase === "listening"}
            aria-label={phase === "listening" ? t("voice.stop") : t("voice.tap")}
            style={{ transform: phase === "listening" ? `scale(${ring})` : undefined }}
            className={`grid h-16 w-16 shrink-0 place-items-center rounded-full text-canvas transition-transform duration-100 disabled:opacity-50 ${phase === "listening" ? "bg-sindoor" : "bg-fg hover:bg-sindoor"}`}
          >
            {phase === "listening" ? <Square aria-hidden className="h-6 w-6" fill="currentColor" /> : <Mic aria-hidden className="h-7 w-7" />}
          </button>
          <div className="min-w-0">
            <p className="text-base font-semibold" aria-live="polite">
              {phase === "listening" ? t("voice.listening") : phase === "working" ? t("voice.working") : t("voice.tap")}
            </p>
            <p className="mt-0.5 text-xs text-muted">{t("voice.privacy")}</p>
          </div>
        </div>
      )}
      {phase === "confirm" && heard && (
        <div>
          <label htmlFor="heard" className="text-sm font-semibold">
            {t("voice.heard")}
          </label>
          <input id="heard" value={text} onChange={(e) => setText(e.target.value)} maxLength={300} lang={lang === "en" ? "en" : "hi"} className="mt-1.5 w-full rounded-xl border border-line bg-canvas px-4 py-3 text-lg outline-none focus:border-haldi" />
          <p className="mt-1 text-xs text-muted">{heard.confidence !== null && heard.confidence < 0.5 ? t("voice.low") : t("voice.edit")}</p>
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              type="button"
              disabled={!text.trim() || disabled}
              onClick={() => {
                onAsk(text);
                setPhase("idle");
                setHeard(null);
              }}
              className="rounded-full bg-fg px-6 py-3 text-base font-semibold text-canvas hover:bg-sindoor disabled:opacity-50"
            >
              {t("voice.ask")}
            </button>
            <button type="button" onClick={start} className="rounded-full border border-line px-5 py-3 text-base hover:bg-surface-2">
              {t("voice.again")}
            </button>
          </div>
        </div>
      )}
      {notice && (
        <p role="alert" className="mt-3 rounded-xl bg-haldi/20 px-3 py-2 text-sm">
          {notice}
        </p>
      )}
    </section>
  );
}
