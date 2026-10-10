// Pose and face trackers: run MediaPipe on a <video> and emit canonical frames.
// A tracker exposes: start(), stop(), latest, onFrame(cb), record(seconds) -> {frames, visibility, times}.
import { faceLandmarker, poseLandmarker } from './mediapipe.js';

const MP_INDEX = [0, 7, 8, 11, 12, 13, 14, 15, 16, 19, 20, 23, 24, 25, 26, 27, 28, 31, 32];
export const KEY_JOINTS = [3, 4, 5, 6, 7, 8, 11, 12, 13, 14, 15, 16];

class BaseTracker {
  constructor() { this.listeners = new Set(); this.latest = null; this.running = false; this._rec = null; }
  onFrame(cb) { this.listeners.add(cb); return () => this.listeners.delete(cb); }
  _emit(sample) {
    this.latest = sample;
    if (this._rec) this._rec.push(sample);
    for (const cb of this.listeners) cb(sample);
  }
  // Collect samples for `seconds` (or until stopRecording()).
  record(seconds, onProgress) {
    this._rec = [];
    const t0 = performance.now();
    return new Promise((resolve) => {
      const tick = () => {
        const el = (performance.now() - t0) / 1000;
        if (onProgress) onProgress(Math.min(1, el / seconds));
        if (el >= seconds || this._stopRec) {
          const samples = this._rec || [];
          this._rec = null; this._stopRec = false;
          resolve(this.pack(samples, t0));
          return;
        }
        requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    });
  }
  stopRecording() { this._stopRec = true; }
}

export class PoseTracker extends BaseTracker {
  constructor(video) { super(); this.video = video; this.kind = 'pose'; }
  async start() {
    this.model = await poseLandmarker();
    this.running = true;
    let last = -1;
    const loop = () => {
      if (!this.running) return;
      const v = this.video;
      if (v.readyState >= 2 && v.currentTime !== last) {
        last = v.currentTime;
        const now = performance.now();
        const res = this.model.detectForVideo(v, now);
        const w = res.worldLandmarks?.[0];
        const img = res.landmarks?.[0];
        if (w) {
          const joints = MP_INDEX.map((k) => [w[k].x, -w[k].y, -w[k].z]);
          const vis = MP_INDEX.map((k) => (w[k].visibility ?? img?.[k]?.visibility ?? 1));
          this._emit({ t: now, joints, vis, image: img });
        } else {
          this._emit({ t: now, joints: null, vis: null, image: null });
        }
      }
      this._raf = requestAnimationFrame(loop);
    };
    loop();
  }
  stop() { this.running = false; if (this._raf) cancelAnimationFrame(this._raf); }
  pack(samples, t0) {
    const ok = samples.filter((s) => s.joints);
    return {
      frames: ok.map((s) => s.joints),
      visibility: ok.map((s) => s.vis),
      times: ok.map((s) => (s.t - t0) / 1000),
      tracked: samples.length ? ok.length / samples.length : 0,
    };
  }
}

export class FaceTracker extends BaseTracker {
  constructor(video) { super(); this.video = video; this.kind = 'face'; }
  async start() {
    this.model = await faceLandmarker();
    this.running = true;
    let last = -1;
    let names = null;
    const loop = () => {
      if (!this.running) return;
      const v = this.video;
      if (v.readyState >= 2 && v.currentTime !== last) {
        last = v.currentTime;
        const now = performance.now();
        const res = this.model.detectForVideo(v, now);
        const cats = res.faceBlendshapes?.[0]?.categories;
        if (cats) {
          if (!names) names = cats.map((c) => c.categoryName);
          const shapes = new Array(52).fill(0);
          cats.forEach((c) => { shapes[c.index ?? names.indexOf(c.categoryName)] = c.score; });
          this._emit({ t: now, shapes, landmarks: res.faceLandmarks?.[0] });
        } else {
          this._emit({ t: now, shapes: null });
        }
      }
      this._raf = requestAnimationFrame(loop);
    };
    loop();
  }
  stop() { this.running = false; if (this._raf) cancelAnimationFrame(this._raf); }
  pack(samples, t0) {
    const ok = samples.filter((s) => s.shapes);
    return { frames: ok.map((s) => s.shapes), times: ok.map((s) => (s.t - t0) / 1000),
      tracked: samples.length ? ok.length / samples.length : 0 };
  }
}

// Body-in-frame check from a pose sample.
export function bodyCheck(sample) {
  if (!sample || !sample.joints) return { person: false, full: false, centered: false };
  const vis = sample.vis || [];
  const full = KEY_JOINTS.every((k) => (vis[k] ?? 0) > 0.5);
  let centered = true;
  if (sample.image) {
    const xs = sample.image.map((p) => p.x);
    const ys = sample.image.map((p) => p.y);
    centered = Math.min(...xs) > 0.02 && Math.max(...xs) < 0.98 && Math.min(...ys) > 0.0 && Math.max(...ys) < 1.0;
  }
  return { person: true, full, centered };
}
