// Voice helpers: WAV encoding, resampling and end-of-speech detection (node --test).
import { test } from "node:test";
import assert from "node:assert/strict";
import { encodeWav, toMono16k, rms, EndOfSpeech, RATE } from "../lib/wav.ts";

test("encodeWav writes a valid 16 kHz mono PCM header and clamps samples", () => {
  const w = encodeWav(Float32Array.from([0, 0.5, -0.5, 2, -2]));
  const v = new DataView(w.buffer);
  assert.equal(String.fromCharCode(...w.slice(0, 4)), "RIFF");
  assert.equal(String.fromCharCode(...w.slice(8, 12)), "WAVE");
  assert.equal(v.getUint16(20, true), 1);
  assert.equal(v.getUint16(22, true), 1);
  assert.equal(v.getUint32(24, true), RATE);
  assert.equal(v.getUint32(40, true), 10);
  assert.equal(v.getUint32(4, true), 36 + 10);
  assert.equal(v.getInt16(44 + 6, true), 32767); // 2.0 clamped
  assert.equal(v.getInt16(44 + 8, true), -32768);
});

test("toMono16k averages channels and resamples 48 kHz to 16 kHz", () => {
  const n = 4800;
  const l = new Float32Array(n).fill(0.4);
  const r = new Float32Array(n).fill(0.2);
  const out = toMono16k([l, r], 48000);
  assert.equal(out.length, 1600);
  assert.ok(out.every((x) => Math.abs(x - 0.3) < 1e-6));
  assert.equal(toMono16k([l], 16000).length, n);
  assert.equal(toMono16k([], 44100).length, 0);
});

test("rms of silence is 0 and of a constant is that constant", () => {
  assert.equal(rms([]), 0);
  assert.equal(rms([0, 0, 0]), 0);
  assert.ok(Math.abs(rms([0.5, -0.5, 0.5, -0.5]) - 0.5) < 1e-9);
});

test("EndOfSpeech stops after a pause that follows speech", () => {
  const e = new EndOfSpeech(0);
  assert.equal(e.update(0.001, 100), false); // waiting to hear someone
  assert.equal(e.update(0.2, 200), false);
  assert.equal(e.update(0.001, 900), false); // short pause
  assert.equal(e.update(0.2, 1000), false); // speaks again: pause resets
  assert.equal(e.update(0.001, 1200), false);
  assert.equal(e.update(0.001, 2600), true); // 1.4 s of quiet
  assert.equal(e.heardSpeech, true);
});

test("EndOfSpeech gives up on silence and never runs past the maximum", () => {
  const quiet = new EndOfSpeech(1000);
  assert.equal(quiet.update(0, 3000), false);
  assert.equal(quiet.update(0, 7000), true);
  assert.equal(quiet.heardSpeech, false);
  const talker = new EndOfSpeech(0);
  assert.equal(talker.update(0.3, 11000), false);
  assert.equal(talker.update(0.3, 12000), true);
});
