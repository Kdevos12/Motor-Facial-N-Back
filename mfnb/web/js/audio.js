// Short synthesized cues (no audio files needed).
let ctx = null;
let enabled = true;
export function setSound(on) { enabled = on; }
function ac() { if (!ctx) ctx = new (window.AudioContext || window.webkitAudioContext)(); return ctx; }
export function beep(freq = 660, ms = 120, vol = 0.12) {
  if (!enabled) return;
  try {
    const a = ac();
    const o = a.createOscillator(); const g = a.createGain();
    o.frequency.value = freq; o.type = 'sine';
    g.gain.setValueAtTime(vol, a.currentTime);
    g.gain.exponentialRampToValueAtTime(0.0001, a.currentTime + ms / 1000);
    o.connect(g).connect(a.destination); o.start(); o.stop(a.currentTime + ms / 1000);
  } catch { /* audio unavailable */ }
}
export const cue = {
  tick: () => beep(520, 90),
  go: () => beep(880, 180),
  good: () => beep(990, 110, 0.08),
  bad: () => beep(300, 160, 0.08),
};
