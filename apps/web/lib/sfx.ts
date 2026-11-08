"use client";

/**
 * Tiny synthesized sound effects (Web Audio). No audio files are downloaded:
 * every sound is generated from noise bursts, filters and oscillators.
 * The AudioContext is created lazily on the first user gesture (browser autoplay rules).
 */

let ctx: AudioContext | null = null;
let master: GainNode | null = null;
let muted = false;
let ambienceNodes: { g: GainNode; src: AudioBufferSourceNode; hum: OscillatorNode } | null = null;

export const isMuted = () => muted;
export function setMuted(m: boolean) {
  muted = m;
  if (master) master.gain.value = m ? 0 : 0.9;
}

function audio(): AudioContext | null {
  if (typeof window === "undefined") return null;
  if (!ctx) {
    const AC = window.AudioContext ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!AC) return null;
    ctx = new AC();
    master = ctx.createGain();
    master.gain.value = muted ? 0 : 0.9;
    master.connect(ctx.destination);
  }
  if (ctx.state === "suspended") void ctx.resume();
  return ctx;
}

/** Call from a click/keydown handler so later sounds are allowed to play. */
export function unlockAudio() {
  audio();
}

function noise(c: AudioContext, seconds: number) {
  const buf = c.createBuffer(1, Math.max(1, Math.floor(c.sampleRate * seconds)), c.sampleRate);
  const d = buf.getChannelData(0);
  for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
  const src = c.createBufferSource();
  src.buffer = buf;
  return src;
}

function env(c: AudioContext, at: number, peak: number, attack: number, decay: number) {
  const g = c.createGain();
  g.gain.setValueAtTime(0.0001, at);
  g.gain.exponentialRampToValueAtTime(peak, at + attack);
  g.gain.exponentialRampToValueAtTime(0.0001, at + attack + decay);
  return g;
}

/** A short metallic tick: band-passed noise plus a quickly decaying ping. */
function tick(c: AudioContext, at: number, freq: number, gain = 0.5) {
  const n = noise(c, 0.06);
  const bp = c.createBiquadFilter();
  bp.type = "bandpass";
  bp.frequency.value = freq;
  bp.Q.value = 7;
  const g = env(c, at, gain, 0.002, 0.045);
  n.connect(bp).connect(g).connect(master!);
  n.start(at);
  n.stop(at + 0.07);

  const o = c.createOscillator();
  o.type = "triangle";
  o.frequency.setValueAtTime(freq * 0.55, at);
  const og = env(c, at, gain * 0.35, 0.002, 0.08);
  o.connect(og).connect(master!);
  o.start(at);
  o.stop(at + 0.1);
}

function thud(c: AudioContext, at: number, from: number, to: number, gain: number, dur: number) {
  const o = c.createOscillator();
  o.type = "sine";
  o.frequency.setValueAtTime(from, at);
  o.frequency.exponentialRampToValueAtTime(to, at + dur);
  const g = env(c, at, gain, 0.004, dur);
  o.connect(g).connect(master!);
  o.start(at);
  o.stop(at + dur + 0.05);
}

export const sfx = {
  /** Key slides into the cylinder: two soft scrapes. */
  insert() {
    const c = audio();
    if (!c || muted) return;
    const t = c.currentTime;
    tick(c, t, 2400, 0.25);
    tick(c, t + 0.07, 2900, 0.3);
    const n = noise(c, 0.18);
    const hp = c.createBiquadFilter();
    hp.type = "highpass";
    hp.frequency.value = 3500;
    const g = env(c, t, 0.08, 0.02, 0.14);
    n.connect(hp).connect(g).connect(master!);
    n.start(t);
    n.stop(t + 0.2);
  },
  /** Key lifted and carried: a soft metallic jingle. */
  keyMove() {
    const c = audio();
    if (!c || muted) return;
    const t = c.currentTime;
    [0, 0.05, 0.13, 0.19, 0.3].forEach((d, i) => tick(c, t + d, 4200 + (i % 2) * 900, 0.12 + (i % 3) * 0.04));
  },
  /** Key seats fully in the cylinder. */
  seat() {
    const c = audio();
    if (!c || muted) return;
    const t = c.currentTime;
    tick(c, t, 2100, 0.35);
    thud(c, t, 300, 160, 0.15, 0.08);
  },
  /** Low shop-room ambience (fan hum + distant street), looped while inside. */
  ambience(on: boolean) {
    const c = audio();
    if (!c) return;
    if (!on) {
      if (ambienceNodes) {
        const { g, src, hum } = ambienceNodes;
        g.gain.setTargetAtTime(0.0001, c.currentTime, 0.3);
        src.stop(c.currentTime + 1.2);
        hum.stop(c.currentTime + 1.2);
        ambienceNodes = null;
      }
      return;
    }
    if (ambienceNodes || muted) return;
    const src = noise(c, 4);
    src.loop = true;
    const lp = c.createBiquadFilter();
    lp.type = "lowpass";
    lp.frequency.value = 420;
    const hum = c.createOscillator();
    hum.frequency.value = 100; // mains-frequency fan hum
    const humGain = c.createGain();
    humGain.gain.value = 0.04;
    const g = c.createGain();
    g.gain.setValueAtTime(0.0001, c.currentTime);
    g.gain.setTargetAtTime(0.18, c.currentTime, 0.6);
    src.connect(lp).connect(g);
    hum.connect(humGain).connect(g);
    g.connect(master!);
    src.start();
    hum.start();
    ambienceNodes = { g, src, hum };
  },
  /** Key turns: a ratchet of pin clicks. */
  turn() {
    const c = audio();
    if (!c || muted) return;
    const t = c.currentTime;
    [0, 0.06, 0.12, 0.2].forEach((d, i) => tick(c, t + d, 3600 - i * 250, 0.4));
  },
  /** Shackle springs open: thunk + bright ring. */
  unlock() {
    const c = audio();
    if (!c || muted) return;
    const t = c.currentTime;
    thud(c, t, 220, 70, 0.6, 0.18);
    tick(c, t, 1800, 0.55);
    const o = c.createOscillator();
    o.type = "sine";
    o.frequency.value = 1320;
    const g = env(c, t + 0.01, 0.12, 0.003, 0.5);
    o.connect(g).connect(master!);
    o.start(t);
    o.stop(t + 0.6);
  },
  /** Lock hits the floor. */
  drop() {
    const c = audio();
    if (!c || muted) return;
    const t = c.currentTime;
    thud(c, t, 140, 45, 0.7, 0.25);
    tick(c, t + 0.01, 900, 0.35);
    tick(c, t + 0.16, 1100, 0.18);
  },
  /** Rolling shutter: band-passed noise chopped by a fast LFO for the slat rattle. */
  shutter(seconds = 1.2) {
    const c = audio();
    if (!c || muted) return;
    const t = c.currentTime;
    const n = noise(c, seconds + 0.2);
    const bp = c.createBiquadFilter();
    bp.type = "bandpass";
    bp.Q.value = 0.9;
    bp.frequency.setValueAtTime(700, t);
    bp.frequency.exponentialRampToValueAtTime(2200, t + seconds);
    const rattle = c.createGain();
    rattle.gain.value = 0.5;
    const lfo = c.createOscillator();
    lfo.type = "square";
    lfo.frequency.setValueAtTime(18, t);
    lfo.frequency.linearRampToValueAtTime(34, t + seconds);
    const lfoGain = c.createGain();
    lfoGain.gain.value = 0.5;
    lfo.connect(lfoGain).connect(rattle.gain);
    const g = c.createGain();
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(0.32, t + 0.12);
    g.gain.setValueAtTime(0.32, t + seconds - 0.2);
    g.gain.exponentialRampToValueAtTime(0.0001, t + seconds);
    n.connect(bp).connect(rattle).connect(g).connect(master!);
    n.start(t);
    lfo.start(t);
    n.stop(t + seconds + 0.2);
    lfo.stop(t + seconds + 0.2);
    thud(c, t + seconds - 0.05, 160, 60, 0.35, 0.2); // drum stops at the top
  },
  /** Air rush as the camera dives into the shop. */
  whoosh() {
    const c = audio();
    if (!c || muted) return;
    const t = c.currentTime;
    const n = noise(c, 1.1);
    const lp = c.createBiquadFilter();
    lp.type = "lowpass";
    lp.frequency.setValueAtTime(250, t);
    lp.frequency.exponentialRampToValueAtTime(4200, t + 0.8);
    const g = env(c, t, 0.25, 0.5, 0.5);
    n.connect(lp).connect(g).connect(master!);
    n.start(t);
    n.stop(t + 1.1);
  },
  /** Soft paper flip for the ledger pages. */
  page() {
    const c = audio();
    if (!c || muted) return;
    const t = c.currentTime;
    const n = noise(c, 0.25);
    const bp = c.createBiquadFilter();
    bp.type = "bandpass";
    bp.frequency.setValueAtTime(1800, t);
    bp.frequency.exponentialRampToValueAtTime(5000, t + 0.18);
    bp.Q.value = 0.7;
    const g = env(c, t, 0.12, 0.03, 0.18);
    n.connect(bp).connect(g).connect(master!);
    n.start(t);
    n.stop(t + 0.25);
  },
};
