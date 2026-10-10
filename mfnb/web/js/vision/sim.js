// Simulated trackers for the camera-less demo mode (?simulate) and automated tests.
// The session tells the tracker what it expects; the tracker "performs" it with noise.
import { J, mirrorFrame } from '../render/stickman.js';

function gauss() { return Math.sqrt(-2 * Math.log(Math.random() + 1e-9)) * Math.cos(2 * Math.PI * Math.random()); }

class SimBase {
  constructor() { this.listeners = new Set(); this.latest = null; this.running = false; this.expected = null; this.accuracy = 0.85; }
  onFrame(cb) { this.listeners.add(cb); return () => this.listeners.delete(cb); }
  _emit(s) { this.latest = s; if (this._rec) this._rec.push(s); for (const cb of this.listeners) cb(s); }
  async start() {
    this.running = true;
    this._t0 = performance.now();
    this._timer = setInterval(() => this._tick(), 33);
  }
  stop() { this.running = false; clearInterval(this._timer); }
  record(seconds, onProgress) {
    this._rec = [];
    this._recStart = performance.now();
    const t0 = this._recStart;
    return new Promise((resolve) => {
      const iv = setInterval(() => {
        const el = (performance.now() - t0) / 1000;
        if (onProgress) onProgress(Math.min(1, el / seconds));
        if (el >= seconds) { clearInterval(iv); const s = this._rec; this._rec = null; resolve(this.pack(s, t0)); }
      }, 50);
    });
  }
  stopRecording() {}
}

export class SimPoseTracker extends SimBase {
  constructor(restFrame) { super(); this.kind = 'pose'; this.rest = restFrame; }
  // frames: the move to perform (already in the right side); null = stay idle
  expect(frames, { correct = Math.random() < this.accuracy, delay = 0.6 } = {}) {
    this.expected = frames && correct ? frames : null;
    this.wrong = frames && !correct;
    this._moveStart = performance.now() + delay * 1000;
  }
  _tick() {
    const now = performance.now();
    let pose = this.rest;
    if (this.expected) {
      const i = Math.floor(((now - this._moveStart) / 1000) * 30);
      pose = i < 0 ? this.expected[0] : this.expected[Math.min(i, this.expected.length - 1)];
    } else if (this.wrong && this.rest) {
      pose = mirrorFrame(this.rest);
    }
    if (!pose) return;
    const joints = pose.map((p) => [p[0] + gauss() * 0.012, p[1] + gauss() * 0.012, p[2] + gauss() * 0.03]);
    this._emit({ t: now, joints, vis: joints.map(() => 0.95), image: null });
  }
  pack(samples, t0) {
    return { frames: samples.map((s) => s.joints), visibility: samples.map((s) => s.vis),
      times: samples.map((s) => (s.t - t0) / 1000), tracked: 1 };
  }
}

export class SimFaceTracker extends SimBase {
  constructor(names) { super(); this.kind = 'face'; this.names = names; }
  expect(target, { correct = Math.random() < this.accuracy, delay = 0.7 } = {}) {
    this.target = target && correct ? target : (target ? { jawOpen: 0.5 } : null);
    this._start = performance.now() + delay * 1000;
  }
  _tick() {
    const now = performance.now();
    const ramp = Math.max(0, Math.min(1, (now - this._start) / 300));
    const shapes = this.names.map((n) => Math.max(0, Math.min(1, ((this.target?.[n] || 0) * ramp) + Math.abs(gauss()) * 0.03)));
    this._emit({ t: now, shapes });
  }
  pack(samples, t0) {
    return { frames: samples.map((s) => s.shapes), times: samples.map((s) => (s.t - t0) / 1000), tracked: 1 };
  }
}

export { J };
