// 3D stick-figure renderer on a 2D canvas (perspective projection, depth-sorted limbs).
// Frames are arrays of 19 [x, y, z] joints in the canonical frame:
// y up, x = camera right (= subject's LEFT when facing the camera), z toward the camera.

export const J = {
  nose: 0, l_ear: 1, r_ear: 2, l_shoulder: 3, r_shoulder: 4, l_elbow: 5, r_elbow: 6, l_wrist: 7, r_wrist: 8,
  l_index: 9, r_index: 10, l_hip: 11, r_hip: 12, l_knee: 13, r_knee: 14, l_ankle: 15, r_ankle: 16, l_foot: 17, r_foot: 18,
};
const MIRROR_PERM = [0, 2, 1, 4, 3, 6, 5, 8, 7, 10, 9, 12, 11, 14, 13, 16, 15, 18, 17];

export function mirrorFrame(f) { return MIRROR_PERM.map((k) => [-f[k][0], f[k][1], f[k][2]]); }
export function mirrorFrames(frames) { return frames.map(mirrorFrame); }

const SEGMENTS = [
  ['l_shoulder', 'l_elbow', 'l', 1], ['l_elbow', 'l_wrist', 'l', 1], ['l_wrist', 'l_index', 'l', 0.7],
  ['r_shoulder', 'r_elbow', 'r', 1], ['r_elbow', 'r_wrist', 'r', 1], ['r_wrist', 'r_index', 'r', 0.7],
  ['l_hip', 'l_knee', 'l', 1.15], ['l_knee', 'l_ankle', 'l', 1.05], ['l_ankle', 'l_foot', 'l', 0.8],
  ['r_hip', 'r_knee', 'r', 1.15], ['r_knee', 'r_ankle', 'r', 1.05], ['r_ankle', 'r_foot', 'r', 0.8],
];

const css = getComputedStyle(document.documentElement);
export const COLORS = {
  l: css.getPropertyValue('--left').trim() || '#4ea8ff',
  r: css.getPropertyValue('--right').trim() || '#ff9a3c',
  c: '#dfe5ef',
  grid: 'rgba(160, 175, 200, 0.14)',
  shadow: 'rgba(0, 0, 0, 0.35)',
};

function sub(a, b) { return [a[0] - b[0], a[1] - b[1], a[2] - b[2]]; }
function dot(a, b) { return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]; }
function cross(a, b) { return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]; }
function norm(a) { const n = Math.hypot(...a) || 1; return [a[0] / n, a[1] / n, a[2] / n]; }
function mid(a, b) { return [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2, (a[2] + b[2]) / 2]; }

export class StickFigure {
  constructor(canvas, opts = {}) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.view = opts.view || 'mirror';   // mirror | facing | back | side
    this.yaw = opts.yaw ?? 25;           // camera angle in degrees
    this.sideInset = opts.sideInset ?? false;
    this.grid = opts.grid ?? true;
    this.colors = { ...COLORS, ...(opts.colors || {}) };
    this.cam = { pos: [0, 1.35, 4.3], target: [0, 0.85, 0] };
    this._raf = null;
    this.resize();
  }

  resize() {
    const r = this.canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    const w = Math.max(50, Math.round((r.width || this.canvas.width) * dpr));
    const hgt = Math.max(50, Math.round((r.height || this.canvas.height) * dpr));
    if (this.canvas.width !== w || this.canvas.height !== hgt) { this.canvas.width = w; this.canvas.height = hgt; }
    this.dpr = dpr;
  }

  // world -> view space according to the display mode and camera angle
  _viewTransform(p, view = this.view, yawDeg = this.yaw) {
    let [x, y, z] = p;
    if (view === 'mirror') x = -x;
    else if (view === 'back') { x = -x; z = -z; }
    else if (view === 'side') { const t = x; x = -z; z = t; }
    const a = (yawDeg * Math.PI) / 180;
    return [x * Math.cos(a) - z * Math.sin(a), y, x * Math.sin(a) + z * Math.cos(a)];
  }

  _projector(rect, view, yaw, camDist = 4.3) {
    const pos = [0, 1.35, camDist];
    const f = norm(sub(this.cam.target, pos));
    const r = norm(cross(f, [0, 1, 0]));
    const u = cross(r, f);
    const focal = rect.h * 1.62;
    const cx = rect.x + rect.w / 2;
    const cy = rect.y + rect.h * 0.52;
    return (p) => {
      const v = this._viewTransform(p, view, yaw);
      const d = sub(v, pos);
      const zc = Math.max(0.3, dot(d, f));
      return [cx + (focal * dot(d, r)) / zc, cy - (focal * dot(d, u)) / zc, zc];
    };
  }

  clear() {
    const { ctx, canvas } = this;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
  }

  draw(frame, opts = {}) {
    this.resize();
    if (!opts.keep) this.clear();
    const W = this.canvas.width;
    const H = this.canvas.height;
    const rect = opts.rect || { x: 0, y: 0, w: W, h: H };
    this._drawFigure(frame, rect, this.view, this.yaw, opts);
    if (this.sideInset && !opts.rect && !opts.noInset) {
      const iw = Math.min(W * 0.26, H * 0.34);
      const inset = { x: W - iw - 12 * this.dpr, y: 12 * this.dpr, w: iw, h: iw * 1.15 };
      const { ctx } = this;
      ctx.save();
      ctx.fillStyle = 'rgba(10, 13, 19, 0.55)';
      ctx.strokeStyle = 'rgba(160, 175, 200, 0.25)';
      ctx.lineWidth = this.dpr;
      ctx.beginPath(); ctx.roundRect(inset.x, inset.y, inset.w, inset.h, 10 * this.dpr); ctx.fill(); ctx.stroke();
      ctx.fillStyle = 'rgba(200, 210, 230, 0.6)';
      ctx.font = `${11 * this.dpr}px system-ui`;
      ctx.fillText('side view', inset.x + 8 * this.dpr, inset.y + 16 * this.dpr);
      ctx.restore();
      this._drawFigure(frame, inset, 'side', 0, { ...opts, grid: false, thin: true });
    }
  }

  _drawFigure(frame, rect, view, yaw, opts) {
    const { ctx } = this;
    const P = this._projector(rect, view, yaw);
    const scale = rect.h / 700;
    const alpha = opts.alpha ?? 1;
    ctx.save();
    ctx.globalAlpha = alpha;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    if ((opts.grid ?? this.grid) && !opts.keep) this._drawGrid(P, scale);
    // shadow
    const feet = [frame[J.l_ankle], frame[J.r_ankle], frame[J.l_foot], frame[J.r_foot]];
    const cxw = feet.reduce((s, p) => s + p[0], 0) / 4;
    const czw = feet.reduce((s, p) => s + p[2], 0) / 4;
    const sc = P([cxw, 0, czw]);
    const se = P([cxw + 0.35, 0, czw]);
    ctx.fillStyle = this.colors.shadow;
    ctx.beginPath();
    ctx.ellipse(sc[0], sc[1], Math.abs(se[0] - sc[0]) || 30 * scale, 10 * scale * (4.3 / sc[2]), 0, 0, Math.PI * 2);
    ctx.fill();

    const pts = frame.map(P);
    const items = [];
    for (const [a, b, side, wmul] of SEGMENTS) {
      const pa = pts[J[a]]; const pb = pts[J[b]];
      items.push({ z: (pa[2] + pb[2]) / 2, draw: () => this._limb(pa, pb, side, wmul, scale, opts) });
    }
    // torso as a filled quad
    const quad = [pts[J.l_shoulder], pts[J.r_shoulder], pts[J.r_hip], pts[J.l_hip]];
    items.push({ z: quad.reduce((s, p) => s + p[2], 0) / 4 + 0.05, draw: () => this._torso(quad, scale, opts) });
    // head
    const earMid = mid(frame[J.l_ear], frame[J.r_ear]);
    const headC = [earMid[0], earMid[1] + 0.02, earMid[2]];
    const ph = P(headC);
    const pr = P([headC[0], headC[1] + 0.11, headC[2]]);
    const pn = pts[J.nose];
    items.push({ z: ph[2], draw: () => this._head(ph, Math.abs(pr[1] - ph[1]), pn, scale, opts) });
    const neckA = P(mid(frame[J.l_shoulder], frame[J.r_shoulder]));
    items.push({ z: neckA[2] + 0.02, draw: () => this._line(neckA, ph, this.colors.c, 7 * scale * (4.3 / neckA[2]), opts) });
    items.sort((p, q) => q.z - p.z);
    for (const it of items) it.draw();
    ctx.restore();
  }

  _drawGrid(P, scale) {
    const { ctx } = this;
    ctx.strokeStyle = this.colors.grid;
    ctx.lineWidth = Math.max(1, scale);
    for (let k = -3; k <= 3; k++) {
      const a = P([k * 0.5, 0, -1.5]); const b = P([k * 0.5, 0, 1.5]);
      const c = P([-1.5, 0, k * 0.5]); const d = P([1.5, 0, k * 0.5]);
      ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]); ctx.moveTo(c[0], c[1]); ctx.lineTo(d[0], d[1]); ctx.stroke();
    }
  }

  _line(a, b, color, width, opts) {
    const { ctx } = this;
    ctx.strokeStyle = color;
    ctx.lineWidth = Math.max(1.5, width * (opts.thin ? 0.7 : 1));
    ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]); ctx.stroke();
  }

  _limb(a, b, side, wmul, scale, opts) {
    const color = opts.color || this.colors[side];
    const depth = 4.3 / ((a[2] + b[2]) / 2);
    this._line(a, b, color, 11 * wmul * scale * depth, opts);
    const { ctx } = this;
    ctx.fillStyle = color;
    ctx.beginPath(); ctx.arc(b[0], b[1], 4.5 * wmul * scale * depth * (opts.thin ? 0.7 : 1), 0, Math.PI * 2); ctx.fill();
  }

  _torso(q, scale, opts) {
    const { ctx } = this;
    ctx.fillStyle = opts.color ? 'rgba(255,255,255,0.08)' : 'rgba(205, 215, 235, 0.16)';
    ctx.strokeStyle = opts.color || this.colors.c;
    ctx.lineWidth = Math.max(1.5, 6 * scale * (opts.thin ? 0.7 : 1));
    ctx.beginPath();
    ctx.moveTo(q[0][0], q[0][1]);
    for (const p of q.slice(1)) ctx.lineTo(p[0], p[1]);
    ctx.closePath(); ctx.fill(); ctx.stroke();
  }

  _head(c, r, nose, scale, opts) {
    const { ctx } = this;
    ctx.fillStyle = opts.color ? 'rgba(255,255,255,0.06)' : '#2a3245';
    ctx.strokeStyle = opts.color || this.colors.c;
    ctx.lineWidth = Math.max(1.5, 5 * scale * (opts.thin ? 0.7 : 1));
    ctx.beginPath(); ctx.arc(c[0], c[1], Math.max(4, r), 0, Math.PI * 2); ctx.fill(); ctx.stroke();
    // nose marker shows where the head points
    ctx.fillStyle = opts.color || this.colors.c;
    ctx.beginPath(); ctx.arc(nose[0], nose[1], Math.max(2, r * 0.16), 0, Math.PI * 2); ctx.fill();
  }

  // Play a sequence; resolves when done (or immediately on stop()).
  play(frames, { fps = 30, speed = 1, loop = false, onFrame } = {}) {
    this.stop();
    return new Promise((resolve) => {
      const start = performance.now();
      const dur = (frames.length - 1) / (fps * speed);
      this._resolve = resolve;
      const tick = (now) => {
        let t = Math.max(0, (now - start) / 1000);
        if (loop) t %= Math.max(dur, 0.001);
        const i = Math.max(0, Math.min(frames.length - 1, Math.floor(t * fps * speed)));
        this.draw(frames[i]);
        if (onFrame) onFrame(i, t);
        if (!loop && t >= dur) { this._raf = null; this._resolve = null; resolve(); return; }
        this._raf = requestAnimationFrame(tick);
      };
      this._raf = requestAnimationFrame(tick);
    });
  }

  stop() {
    if (this._raf) cancelAnimationFrame(this._raf);
    this._raf = null;
    if (this._resolve) { const r = this._resolve; this._resolve = null; r(); }
  }
}

// Peak frame (largest deviation from the first one) for thumbnails.
export function peakFrame(frames) {
  let best = frames.length - 1; let bd = -1;
  for (let i = 0; i < frames.length; i++) {
    let d = 0;
    for (let k = 0; k < 19; k++) d += Math.hypot(...sub(frames[i][k], frames[0][k]));
    if (d > bd) { bd = d; best = i; }
  }
  return frames[best];
}
