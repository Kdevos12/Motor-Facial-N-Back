// Stylised 2D face driven by the 52 MediaPipe/ARKit blendshapes.
// `shapes` is an object {blendshapeName: 0..1}; missing names are 0.
// view: 'mirror' shows the face like your reflection (its left on screen left),
// 'facing' like a person facing you (its left on screen right).

export function mirrorShapes(shapes) {
  const out = {};
  for (const [k, v] of Object.entries(shapes)) {
    let m = k;
    if (k.endsWith('Left')) m = `${k.slice(0, -4)}Right`;
    else if (k.endsWith('Right')) m = `${k.slice(0, -5)}Left`;
    out[m] = v;
  }
  return out;
}

export function lerpShapes(a, b, t) {
  const out = {};
  for (const k of new Set([...Object.keys(a), ...Object.keys(b)])) out[k] = (a[k] || 0) * (1 - t) + (b[k] || 0) * t;
  return out;
}

const SKIN = '#f0d2b6';
const SKIN_SHADE = '#d9b394';
const LINE = '#2b2230';
const LIP = '#c4636c';
const MOUTH = '#3a1c26';

export class FaceAvatar {
  constructor(canvas, { view = 'mirror' } = {}) {
    this.canvas = canvas; this.ctx = canvas.getContext('2d'); this.view = view; this._raf = null;
  }

  resize() {
    const r = this.canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    const w = Math.max(60, Math.round((r.width || this.canvas.width) * dpr));
    const hgt = Math.max(60, Math.round((r.height || this.canvas.height) * dpr));
    if (this.canvas.width !== w || this.canvas.height !== hgt) { this.canvas.width = w; this.canvas.height = hgt; }
  }

  draw(shapes = {}) {
    this.resize();
    const { ctx, canvas } = this;
    const W = canvas.width; const H = canvas.height;
    const g = (n) => Math.max(0, Math.min(1, shapes[n] || 0));
    // screen direction of the face's anatomical LEFT side
    const sL = this.view === 'mirror' ? -1 : 1;
    const side = (s) => (s === 'Left' ? sL : -sL);
    const S = Math.min(W, H) / 400;
    ctx.clearRect(0, 0, W, H);
    ctx.save();
    ctx.translate(W / 2, H / 2 + 10 * S);
    ctx.scale(S, S);
    ctx.lineCap = 'round'; ctx.lineJoin = 'round';

    const jawOpen = g('jawOpen');
    const jawShift = (g('jawLeft') * side('Left') + g('jawRight') * side('Right')) * 14;
    const puff = g('cheekPuff');
    const chinDrop = jawOpen * 34;

    // head shape
    ctx.fillStyle = SKIN; ctx.strokeStyle = LINE; ctx.lineWidth = 4;
    ctx.beginPath();
    ctx.moveTo(0, -165);
    ctx.bezierCurveTo(105, -165, 132, -80, 128 + puff * 14, 10);
    ctx.bezierCurveTo(124 + puff * 18, 85, 70 + jawShift, 140 + chinDrop, jawShift, 150 + chinDrop + g('jawForward') * 6);
    ctx.bezierCurveTo(-70 + jawShift, 140 + chinDrop, -124 - puff * 18, 85, -128 - puff * 14, 10);
    ctx.bezierCurveTo(-132, -80, -105, -165, 0, -165);
    ctx.fill(); ctx.stroke();
    // ears
    for (const sx of [-1, 1]) {
      ctx.beginPath(); ctx.ellipse(sx * 132, 0, 14, 30, 0, 0, Math.PI * 2); ctx.fillStyle = SKIN_SHADE; ctx.fill(); ctx.stroke();
    }
    // hair cap
    ctx.fillStyle = '#3b2f3f';
    ctx.beginPath();
    ctx.moveTo(-122, -60); ctx.bezierCurveTo(-130, -170, 130, -170, 122, -60);
    ctx.bezierCurveTo(90, -120, -90, -120, -122, -60); ctx.fill();

    // cheeks
    for (const s of ['Left', 'Right']) {
      const x = side(s) * 70;
      const sq = g(`cheekSquint${s}`);
      ctx.fillStyle = `rgba(230, 120, 120, ${0.12 + 0.35 * sq + 0.25 * puff})`;
      ctx.beginPath(); ctx.ellipse(x + side(s) * puff * 8, 40 - sq * 10, 26 + puff * 14, 18 + puff * 10, 0, 0, Math.PI * 2); ctx.fill();
    }

    // brows
    for (const s of ['Left', 'Right']) {
      const sx = side(s);
      const down = g(`browDown${s}`);
      const outer = g(`browOuterUp${s}`);
      const inner = g('browInnerUp');
      const innerX = sx * (26 - down * 6); const outerX = sx * 82;
      const innerY = -62 - inner * 24 + down * 14;
      const outerY = -60 - outer * 26 + down * 6;
      const midY = (innerY + outerY) / 2 - 10 - outer * 6 + down * 4;
      ctx.strokeStyle = '#3b2f3f'; ctx.lineWidth = 9;
      ctx.beginPath(); ctx.moveTo(innerX, innerY); ctx.quadraticCurveTo(sx * 55, midY, outerX, outerY); ctx.stroke();
    }

    // eyes
    for (const s of ['Left', 'Right']) {
      const sx = side(s);
      const cx = sx * 52; const cy = -22;
      const blink = g(`eyeBlink${s}`); const wide = g(`eyeWide${s}`);
      const squint = g(`eyeSquint${s}`) * 0.7 + g(`cheekSquint${s}`) * 0.3;
      const open = Math.max(0.04, 1 - blink * 0.96 + wide * 0.4 - squint * 0.45);
      const hTop = 15 * open; const hBot = 11 * Math.max(0.1, open - squint * 0.2);
      ctx.fillStyle = '#ffffff'; ctx.strokeStyle = LINE; ctx.lineWidth = 3.5;
      ctx.beginPath();
      ctx.moveTo(cx - 26, cy);
      ctx.quadraticCurveTo(cx, cy - hTop * 2, cx + 26, cy);
      ctx.quadraticCurveTo(cx, cy + hBot * 2, cx - 26, cy);
      ctx.closePath(); ctx.fill();
      if (open > 0.12) {
        // gaze: In = toward the nose, Out = away from it
        const gx = (g(`eyeLookOut${s}`) - g(`eyeLookIn${s}`)) * sx * 11;
        const gy = (g(`eyeLookDown${s}`) - g(`eyeLookUp${s}`)) * 7;
        ctx.save(); ctx.clip();
        ctx.fillStyle = '#4a6b8a'; ctx.beginPath(); ctx.arc(cx + gx, cy + gy, 10, 0, Math.PI * 2); ctx.fill();
        ctx.fillStyle = '#111'; ctx.beginPath(); ctx.arc(cx + gx, cy + gy, 5, 0, Math.PI * 2); ctx.fill();
        ctx.fillStyle = '#fff'; ctx.beginPath(); ctx.arc(cx + gx + 3, cy + gy - 3, 2, 0, Math.PI * 2); ctx.fill();
        ctx.restore();
      }
      ctx.beginPath();
      ctx.moveTo(cx - 26, cy);
      ctx.quadraticCurveTo(cx, cy - hTop * 2, cx + 26, cy);
      ctx.stroke();
      if (open < 0.12) { ctx.beginPath(); ctx.moveTo(cx - 24, cy + 2); ctx.quadraticCurveTo(cx, cy + 8, cx + 24, cy + 2); ctx.stroke(); }
    }

    // nose
    const sneerL = g('noseSneerLeft'); const sneerR = g('noseSneerRight');
    ctx.strokeStyle = LINE; ctx.lineWidth = 3.5;
    ctx.beginPath(); ctx.moveTo(0, -18); ctx.quadraticCurveTo(-4, 20, 0, 34); ctx.stroke();
    for (const s of ['Left', 'Right']) {
      const sx = side(s); const sn = s === 'Left' ? sneerL : sneerR;
      ctx.beginPath(); ctx.ellipse(sx * 13, 36 - sn * 6, 7, 4, 0, 0, Math.PI * 2); ctx.stroke();
      if (sn > 0.2) { ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(sx * 10, 6); ctx.lineTo(sx * 24, 0); ctx.moveTo(sx * 12, 14); ctx.lineTo(sx * 26, 10); ctx.stroke(); ctx.lineWidth = 3.5; }
    }

    // mouth
    const shiftX = (g('mouthLeft') * side('Left') + g('mouthRight') * side('Right')) * 22 + jawShift * 0.6;
    const pucker = g('mouthPucker'); const funnel = g('mouthFunnel');
    const narrow = 1 - 0.5 * pucker - 0.3 * funnel;
    const mouthY = 82 + jawOpen * 10;
    const corner = (s) => {
      const sx = side(s);
      const smile = g(`mouthSmile${s}`); const frown = g(`mouthFrown${s}`);
      const stretch = g(`mouthStretch${s}`); const dimple = g(`mouthDimple${s}`);
      return [shiftX + sx * (46 * narrow + smile * 8 + stretch * 16 + dimple * 4), mouthY - smile * 20 + frown * 16 + stretch * 4];
    };
    const cl = corner('Left'); const cr = corner('Right');
    const [a, b] = cl[0] < cr[0] ? [cl, cr] : [cr, cl];
    const press = Math.max(g('mouthPressLeft'), g('mouthPressRight'));
    const roll = Math.max(g('mouthRollUpper'), g('mouthRollLower'));
    const lipT = Math.max(2, 9 * (1 - press * 0.6 - roll * 0.8) + pucker * 6 + funnel * 3);
    const upperUp = (s) => g(`mouthUpperUp${s}`) * 12;
    const lowerDn = (s) => g(`mouthLowerDown${s}`) * 12;
    const shrugU = g('mouthShrugUpper') * 6; const shrugL = g('mouthShrugLower') * 8;
    const open = Math.max(0, jawOpen * 46 + (lowerDn('Left') + lowerDn('Right')) / 2 + funnel * 16 - g('mouthClose') * 10 - press * 8);
    const upY = mouthY - 4 - (upperUp('Left') + upperUp('Right')) / 2 - shrugU;
    const loY = mouthY + 4 + open + shrugL * -0.4;
    // opening
    if (open > 3) {
      ctx.fillStyle = MOUTH;
      ctx.beginPath(); ctx.moveTo(a[0], a[1]);
      ctx.quadraticCurveTo(shiftX, upY - 4, b[0], b[1]);
      ctx.quadraticCurveTo(shiftX, loY + 8, a[0], a[1]); ctx.fill();
      const teeth = Math.max(g('mouthSmileLeft'), g('mouthSmileRight'), upperUp('Left') / 12, upperUp('Right') / 12);
      if (teeth > 0.25) {
        ctx.fillStyle = '#f7f3ee';
        ctx.beginPath(); ctx.moveTo(a[0] + 6, a[1] - 1); ctx.quadraticCurveTo(shiftX, upY + 2, b[0] - 6, b[1] - 1);
        ctx.quadraticCurveTo(shiftX, upY + 14, a[0] + 6, a[1] - 1); ctx.fill();
      }
    }
    // lips
    ctx.fillStyle = LIP; ctx.strokeStyle = LINE; ctx.lineWidth = 3;
    ctx.beginPath(); ctx.moveTo(a[0], a[1]);
    ctx.quadraticCurveTo(shiftX, upY - 8 - lipT, b[0], b[1]);
    ctx.quadraticCurveTo(shiftX, upY + (open > 3 ? 2 : lipT * 0.3), a[0], a[1]); ctx.fill(); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(a[0], a[1]);
    ctx.quadraticCurveTo(shiftX, loY + 8 + lipT, b[0], b[1]);
    ctx.quadraticCurveTo(shiftX, loY - (open > 3 ? 2 : lipT * 0.3), a[0], a[1]); ctx.fill(); ctx.stroke();
    if (pucker > 0.3 || funnel > 0.3) {
      ctx.strokeStyle = 'rgba(43,34,48,0.5)'; ctx.lineWidth = 2;
      ctx.beginPath(); ctx.ellipse(shiftX, (upY + loY) / 2, (b[0] - a[0]) / 2 + 6, (loY - upY) / 2 + 12, 0, 0, Math.PI * 2); ctx.stroke();
    }
    ctx.restore();
  }

  // neutral -> target -> hold -> neutral, resolves at the end
  play(shapes, durationS = 2.4) {
    this.stop();
    return new Promise((resolve) => {
      const t0 = performance.now();
      this._resolve = resolve;
      const tick = (now) => {
        const t = Math.max(0, (now - t0) / 1000);
        const ramp = 0.45;
        const k = t < ramp ? t / ramp : t > durationS - ramp ? Math.max(0, (durationS - t) / ramp) : 1;
        const e = k * k * (3 - 2 * k);
        this.draw(lerpShapes({}, shapes, e));
        if (t >= durationS) { this._raf = null; this._resolve = null; resolve(); return; }
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
