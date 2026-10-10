// Pose and face trackers: run MediaPipe on a <video> and emit canonical frames.
// A tracker exposes: start(), stop(), latest, onFrame(cb), record(seconds) -> {frames, visibility, times},
// and `display`, the element that shows what the tracker sees (the video, or a rotated copy of it).
// Options: rotate (0/90/180/270, a phone mounted sideways) and mirrored (the camera sends a mirror image:
// left and right are swapped back so that "left" always means the user's left).
import { mirrorFrame } from '../render/stickman.js';
import { faceLandmarker, poseLandmarker } from './mediapipe.js';

const MP_INDEX = [0, 7, 8, 11, 12, 13, 14, 15, 16, 19, 20, 23, 24, 25, 26, 27, 28, 31, 32];
// MediaPipe's 33 pose landmarks with left and right exchanged
const MP_SWAP = [0, 4, 5, 6, 1, 2, 3, 8, 7, 10, 9, 12, 11, 14, 13, 16, 15, 18, 17, 20, 19, 22, 21, 24, 23, 26, 25, 28, 27, 30, 29, 32, 31];
// canonical joints (see motion/skeleton.py): nose, ears, shoulders, elbows, wrists, index, hips, knees, ankles, feet
export const KEY_JOINTS = [3, 4, 5, 6, 7, 8, 11, 12, 13, 14, 15, 16];
export const UPPER_JOINTS = [0, 3, 4, 5, 6, 7, 8];
// a landmark this close to the image border is treated as out of frame (MediaPipe invents hidden limbs)
const IN_X = [0.01, 0.99];
const IN_Y = [0.0, 0.985];

function inFrame(p) { return p && p.x >= IN_X[0] && p.x <= IN_X[1] && p.y >= IN_Y[0] && p.y <= IN_Y[1]; }

class BaseTracker {
  constructor(video, { rotate = 0, mirrored = false } = {}) {
    this.listeners = new Set(); this.latest = null; this.running = false; this._rec = null;
    this.video = video; this.rotate = ((Number(rotate) % 360) + 360) % 360; this.mirrored = !!mirrored;
    this.canvas = this.rotate ? document.createElement('canvas') : null;
    if (this.canvas) this.canvas.className = 'mirror';
    this.display = this.canvas || video;
  }
  onFrame(cb) { this.listeners.add(cb); return () => this.listeners.delete(cb); }
  _emit(sample) {
    this.latest = sample;
    if (this._rec) this._rec.push(sample);
    for (const cb of this.listeners) cb(sample);
  }
  // The image given to MediaPipe: the video, or the video turned upright.
  _source() {
    if (!this.canvas) return this.video;
    const v = this.video; const c = this.canvas;
    const side = this.rotate === 90 || this.rotate === 270;
    const w = side ? v.videoHeight : v.videoWidth; const hgt = side ? v.videoWidth : v.videoHeight;
    if (c.width !== w || c.height !== hgt) { c.width = w; c.height = hgt; }
    const ctx = c.getContext('2d');
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.translate(w / 2, hgt / 2);
    ctx.rotate((this.rotate * Math.PI) / 180);
    ctx.drawImage(v, -v.videoWidth / 2, -v.videoHeight / 2);
    return c;
  }
  _loop(handle) {
    let last = -1;
    const loop = () => {
      if (!this.running) return;
      const v = this.video;
      if (v.readyState >= 2 && v.currentTime !== last) {
        last = v.currentTime;
        try { handle(this._source(), performance.now()); } catch (err) { console.warn(err); }
      }
      this._raf = requestAnimationFrame(loop);
    };
    loop();
  }
  stop() { this.running = false; if (this._raf) cancelAnimationFrame(this._raf); }
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
  constructor(video, opts) { super(video, opts); this.kind = 'pose'; }
  async start() {
    this.model = await poseLandmarker();
    this.running = true;
    this._loop((src, now) => {
      const res = this.model.detectForVideo(src, now);
      const w = res.worldLandmarks?.[0];
      let img = res.landmarks?.[0];
      if (!w) { this._emit({ t: now, joints: null, vis: null, image: null }); return; }
      let joints = MP_INDEX.map((k) => [w[k].x, -w[k].y, -w[k].z]);
      // a joint outside the picture gets visibility 0, whatever the model guessed for it
      let vis = MP_INDEX.map((k) => (inFrame(img?.[k]) ? (w[k].visibility ?? img?.[k]?.visibility ?? 1) : 0));
      if (this.mirrored) {
        joints = mirrorFrame(joints);
        vis = mirrorFrame(vis.map((v) => [0, v, 0])).map((p) => p[1]);
        if (img) img = MP_SWAP.map((k) => img[k]);
      }
      this._emit({ t: now, joints, vis, image: img });
    });
  }
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
  // names: the 52 blendshape names in the order the server expects (state.meta.face_names)
  constructor(video, opts = {}) { super(video, opts); this.kind = 'face'; this.names = opts.names || null; }
  async start() {
    this.model = await faceLandmarker();
    this.running = true;
    let order = null;
    let orderMirrored = null;
    this._loop((src, now) => {
      const res = this.model.detectForVideo(src, now);
      const cats = res.faceBlendshapes?.[0]?.categories;
      if (!cats) { this._emit({ t: now, shapes: null }); return; }
      if (!order || orderMirrored !== this.mirrored) {
        orderMirrored = this.mirrored;
        // map by name, so the order never depends on the model's index field
        const names = this.names || cats.map((c) => c.categoryName);
        const pos = Object.fromEntries(names.map((n, i) => [n, i]));
        const partner = (n) => (n.endsWith('Left') ? `${n.slice(0, -4)}Right` : n.endsWith('Right') ? `${n.slice(0, -5)}Left` : n);
        order = cats.map((c) => pos[this.mirrored ? partner(c.categoryName) : c.categoryName]);
        this._n = names.length;
      }
      const shapes = new Array(this._n).fill(0);
      cats.forEach((c, i) => { if (order[i] !== undefined) shapes[order[i]] = c.score; });
      this._emit({ t: now, shapes, landmarks: res.faceLandmarks?.[0] });
    });
  }
  pack(samples, t0) {
    const ok = samples.filter((s) => s.shapes);
    return { frames: ok.map((s) => s.shapes), times: ok.map((s) => (s.t - t0) / 1000),
      tracked: samples.length ? ok.length / samples.length : 0 };
  }
}

// Body-in-frame check from a pose sample. framing 'full': head to feet; 'upper': head, shoulders, arms and hands
// (hips may be cut off). `margin` keeps the required joints off the image border.
export function bodyCheck(sample, framing = 'full') {
  if (!sample || !sample.joints) return { person: false, full: false, centered: false };
  const vis = sample.vis || [];
  const need = framing === 'upper' ? UPPER_JOINTS : KEY_JOINTS;
  const full = need.every((k) => (vis[k] ?? 0) > 0.5);
  let centered = true;
  if (sample.image) {
    const pts = framing === 'upper' ? [0, 11, 12, 13, 14, 15, 16].map((k) => sample.image[k]) : sample.image;
    const xs = pts.map((p) => p.x);
    const ys = pts.map((p) => p.y);
    centered = Math.min(...xs) > 0.02 && Math.max(...xs) < 0.98 && Math.min(...ys) > (framing === 'upper' ? 0.06 : 0.0) && Math.max(...ys) < 1.0;
  }
  return { person: true, full, centered };
}

// Side checks (is the camera image mirrored?), from raw image geometry so they do not depend on the model's
// left/right labels. Return true (mirrored), false (normal) or null (not decided yet).
export function raisedHandSide(sample) {
  // the user raises their RIGHT hand: unmirrored, it appears on the image's left
  const img = sample?.image;
  if (!img) return null;
  const nose = img[0]; const ls = img[11]; const rs = img[12]; const a = img[15]; const b = img[16];
  if (![nose, ls, rs, a, b].every(Boolean)) return null;
  const hand = a.y < b.y ? a : b;
  const other = a.y < b.y ? b : a;
  if (!(hand.y < nose.y && other.y > Math.max(ls.y, rs.y))) return null;     // one hand above the head, the other low
  const mid = (ls.x + rs.x) / 2;
  const width = Math.abs(ls.x - rs.x) || 0.1;
  if (Math.abs(hand.x - mid) < 0.3 * width) return null;
  return hand.x > mid;   // in the camera's own picture
}

export function headTurnSide(sample) {
  // the user turns their head to their LEFT: unmirrored, the nose moves toward the image's right
  const lm = sample?.landmarks;
  if (!lm || !lm[1] || !lm[234] || !lm[454]) return null;
  const left = Math.min(lm[234].x, lm[454].x); const right = Math.max(lm[234].x, lm[454].x);
  const width = right - left;
  if (width <= 0) return null;
  const off = (lm[1].x - (left + right) / 2) / width;
  if (Math.abs(off) < 0.15) return null;
  return off < 0;
}
