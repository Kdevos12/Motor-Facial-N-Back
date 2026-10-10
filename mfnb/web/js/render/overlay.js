// Draws the tracked skeleton over the webcam video (normalized image landmarks).
// `video` is the element the tracker reads: a <video>, or the canvas holding the rotated picture.
import { COLORS } from './stickman.js';

const MP_PAIRS = [[11, 12, 'c'], [23, 24, 'c'], [11, 23, 'c'], [12, 24, 'c'],
  [11, 13, 'l'], [13, 15, 'l'], [15, 19, 'l'], [12, 14, 'r'], [14, 16, 'r'], [16, 20, 'r'],
  [23, 25, 'l'], [25, 27, 'l'], [27, 31, 'l'], [24, 26, 'r'], [26, 28, 'r'], [28, 32, 'r']];

export function drawPoseOverlay(canvas, video, image) {
  const ctx = canvas.getContext('2d');
  const w = video.videoWidth || video.width || 640; const hgt = video.videoHeight || video.height || 480;
  if (canvas.width !== w || canvas.height !== hgt) { canvas.width = w; canvas.height = hgt; }
  ctx.clearRect(0, 0, w, hgt);
  if (!image) return;
  ctx.lineCap = 'round';
  ctx.lineWidth = Math.max(3, w / 160);
  for (const [a, b, side] of MP_PAIRS) {
    const pa = image[a]; const pb = image[b];
    if (!pa || !pb || (pa.visibility ?? 1) < 0.3 || (pb.visibility ?? 1) < 0.3) continue;
    ctx.strokeStyle = COLORS[side];
    ctx.beginPath(); ctx.moveTo(pa.x * w, pa.y * hgt); ctx.lineTo(pb.x * w, pb.y * hgt); ctx.stroke();
  }
  const nose = image[0];
  if (nose) { ctx.fillStyle = COLORS.c; ctx.beginPath(); ctx.arc(nose.x * w, nose.y * hgt, w / 120, 0, Math.PI * 2); ctx.fill(); }
}

export function drawFaceOverlay(canvas, video, landmarks) {
  const ctx = canvas.getContext('2d');
  const w = video.videoWidth || video.width || 640; const hgt = video.videoHeight || video.height || 480;
  if (canvas.width !== w || canvas.height !== hgt) { canvas.width = w; canvas.height = hgt; }
  ctx.clearRect(0, 0, w, hgt);
  if (!landmarks) return;
  ctx.fillStyle = 'rgba(124, 140, 255, 0.7)';
  for (let i = 0; i < landmarks.length; i += 3) {
    const p = landmarks[i];
    ctx.fillRect(p.x * w - 1, p.y * hgt - 1, 2, 2);
  }
}
