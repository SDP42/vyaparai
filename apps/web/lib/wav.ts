/**
 * Pure audio helpers for voice questions (no browser APIs, so they are tested in Node).
 * The server wants 16 kHz mono 16-bit WAV, which is what `encodeWav(toMono16k(...))` makes.
 */
export const RATE = 16000;

/** Average the channels, then resample to 16 kHz by linear interpolation. */
export function toMono16k(channels: Float32Array[], rate: number): Float32Array {
  const n = channels[0]?.length ?? 0;
  const mono = new Float32Array(n);
  for (const ch of channels) for (let i = 0; i < n; i++) mono[i] += ch[i] / channels.length;
  if (rate === RATE || n === 0) return mono;
  const out = new Float32Array(Math.round((n * RATE) / rate));
  const step = (n - 1) / Math.max(out.length - 1, 1);
  for (let i = 0; i < out.length; i++) {
    const pos = i * step;
    const lo = Math.floor(pos);
    const hi = Math.min(lo + 1, n - 1);
    out[i] = mono[lo] + (mono[hi] - mono[lo]) * (pos - lo);
  }
  return out;
}

export function rms(samples: ArrayLike<number>): number {
  let s = 0;
  for (let i = 0; i < samples.length; i++) s += samples[i] * samples[i];
  return samples.length ? Math.sqrt(s / samples.length) : 0;
}

/** 16-bit PCM WAV bytes. */
export function encodeWav(samples: Float32Array, rate = RATE): Uint8Array {
  const bytes = new Uint8Array(44 + samples.length * 2);
  const v = new DataView(bytes.buffer);
  const text = (o: number, s: string) => [...s].forEach((c, i) => v.setUint8(o + i, c.charCodeAt(0)));
  text(0, "RIFF");
  v.setUint32(4, 36 + samples.length * 2, true);
  text(8, "WAVE");
  text(12, "fmt ");
  v.setUint32(16, 16, true);
  v.setUint16(20, 1, true); // PCM
  v.setUint16(22, 1, true); // mono
  v.setUint32(24, rate, true);
  v.setUint32(28, rate * 2, true);
  v.setUint16(32, 2, true);
  v.setUint16(34, 16, true);
  text(36, "data");
  v.setUint32(40, samples.length * 2, true);
  for (let i = 0; i < samples.length; i++) {
    const x = Math.max(-1, Math.min(1, samples[i]));
    v.setInt16(44 + i * 2, x < 0 ? x * 0x8000 : x * 0x7fff, true);
  }
  return bytes;
}

/**
 * Decides when a person has finished speaking: after they have said something, a pause of `quietMs`
 * ends the recording; a recording with no speech at all ends after `waitMs`; nothing runs past `maxMs`.
 */
export class EndOfSpeech {
  private spoke = false;
  private quietSince: number | null = null;
  private readonly startedAt: number;
  private readonly opts: { threshold: number; quietMs: number; waitMs: number; maxMs: number };
  constructor(startedAt: number, opts = { threshold: 0.02, quietMs: 1300, waitMs: 6000, maxMs: 12000 }) {
    this.startedAt = startedAt;
    this.opts = opts;
  }
  /** Feed the current loudness (0..1) and time (ms); true means stop now. */
  update(level: number, now: number): boolean {
    const t = now - this.startedAt;
    if (t >= this.opts.maxMs) return true;
    if (level >= this.opts.threshold) {
      this.spoke = true;
      this.quietSince = null;
      return false;
    }
    if (!this.spoke) return t >= this.opts.waitMs;
    this.quietSince ??= now;
    return now - this.quietSince >= this.opts.quietMs;
  }
  get heardSpeech(): boolean {
    return this.spoke;
  }
}
