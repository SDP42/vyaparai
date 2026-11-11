"use client";

/** Read an answer aloud with the device's own voice (nothing is sent anywhere). Best effort: text is always shown. */
export type SpeakLang = "en" | "hinglish" | "hi";

const TAG: Record<SpeakLang, string> = { en: "en-IN", hinglish: "hi-IN", hi: "hi-IN" };

export function canSpeak(): boolean {
  return typeof window !== "undefined" && "speechSynthesis" in window && typeof SpeechSynthesisUtterance !== "undefined";
}

/** The best installed voice for the language, or null when the device has none. */
export function voiceFor(lang: SpeakLang): SpeechSynthesisVoice | null {
  if (!canSpeak()) return null;
  const tag = TAG[lang].toLowerCase();
  const base = tag.slice(0, 2);
  const all = window.speechSynthesis.getVoices();
  return all.find((v) => v.lang.toLowerCase().replace("_", "-") === tag) ?? all.find((v) => v.lang.toLowerCase().startsWith(base)) ?? null;
}

/** Speaks `text`; returns false when no voice exists so the page can say the answer is text only. */
export function speak(text: string, lang: SpeakLang, rate = 0.95): boolean {
  if (!canSpeak()) return false;
  const voice = voiceFor(lang);
  if (!voice) return false;
  window.speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.voice = voice;
  u.lang = voice.lang;
  u.rate = rate;
  window.speechSynthesis.speak(u);
  return true;
}

export function stopSpeaking() {
  if (canSpeak()) window.speechSynthesis.cancel();
}
