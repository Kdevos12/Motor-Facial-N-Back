// Re-proportion a stick-figure sequence to the user's calibrated body (bone directions kept).
import { J, mirrorFrames } from './stickman.js';
import { state } from '../state.js';

const add = (a, b) => [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
const sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
const mul = (a, k) => [a[0] * k, a[1] * k, a[2] * k];
const mid = (a, b) => mul(add(a, b), 0.5);
const unit = (a) => { const n = Math.hypot(...a) || 1; return mul(a, 1 / n); };
const FEET = [J.l_ankle, J.r_ankle, J.l_foot, J.r_foot];

export function retargetFrame(f, d) {
  const out = new Array(19);
  const midHip = mid(f[J.l_hip], f[J.r_hip]);
  const midSh = mid(f[J.l_shoulder], f[J.r_shoulder]);
  const hipDir = unit(sub(f[J.l_hip], f[J.r_hip]));
  const shDir = unit(sub(f[J.l_shoulder], f[J.r_shoulder]));
  const newSh = add(midHip, mul(unit(sub(midSh, midHip)), d.torso));
  out[J.l_hip] = add(midHip, mul(hipDir, d.hip_half));
  out[J.r_hip] = sub(midHip, mul(hipDir, d.hip_half));
  out[J.l_shoulder] = add(newSh, mul(shDir, d.shoulder_half));
  out[J.r_shoulder] = sub(newSh, mul(shDir, d.shoulder_half));
  for (const k of [J.nose, J.l_ear, J.r_ear]) out[k] = add(newSh, sub(f[k], midSh));
  for (const s of ['l', 'r']) {
    const chain = (a, b, len) => { out[J[`${s}_${b}`]] = add(out[J[`${s}_${a}`]], mul(unit(sub(f[J[`${s}_${b}`]], f[J[`${s}_${a}`]])), len)); };
    chain('shoulder', 'elbow', d.upper_arm); chain('elbow', 'wrist', d.forearm); chain('wrist', 'index', d.hand);
    chain('hip', 'knee', d.thigh); chain('knee', 'ankle', d.shin); chain('ankle', 'foot', d.foot);
  }
  const lowBefore = Math.min(...FEET.map((k) => f[k][1]));
  const lowAfter = Math.min(...FEET.map((k) => out[k][1]));
  return out.map((p) => [p[0], p[1] - lowAfter + lowBefore, p[2]]);
}

// Frames ready for display for the active profile: mirrored if asked, re-proportioned if calibrated.
export function displayFrames(frames, mirrored = false) {
  const f = mirrored ? mirrorFrames(frames) : frames;
  const body = state.profile && state.profile.calibration && state.profile.calibration.body;
  return body ? f.map((fr) => retargetFrame(fr, body)) : f;
}
