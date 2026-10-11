// Camera access: one shared stream, a chosen camera per modality (e.g. the phone for moves, the laptop webcam for
// faces), rotation for a phone mounted sideways, and notice when the feed stops (unplugged, scrcpy closed...).
// A camera can also be a phone camera app on the network (prefs.url): the local server relays its MJPEG stream and
// the page turns it into an ordinary video stream, so everything downstream works the same.
import { state } from '../state.js';

let stream = null;
let streamDevice = null;          // deviceId of the live stream ('' = browser default, 'url:…' = network camera)
let urlSource = null;             // {img, timers, stalled, label} while a network camera is open
const listeners = new Set();

export const DEFAULT_PREFS = { deviceId: '', label: '', rotate: 0, url: '' };

// Camera preferences of the active profile for a modality.
export function cameraPrefs(modality) {
  const c = state.profile?.settings?.cameras?.[modality];
  return { ...DEFAULT_PREFS, ...(c || {}) };
}

// Key under which a camera's orientation (mirrored or not) is remembered: its name, or 'default' for the
// browser's default camera (the same key whether or not a camera is open, so Settings and blocks agree).
export function cameraKey(prefs) {
  return (prefs?.label || prefs?.deviceId || 'default').slice(0, 120);
}

export function trackMuted() {
  const t = stream?.getVideoTracks()[0];
  return !t || t.readyState !== 'live' || t.muted || !!urlSource?.stalled;
}

export function onCameraState(cb) { listeners.add(cb); return () => listeners.delete(cb); }
function emit(what) { for (const cb of listeners) cb(what); }

export class CameraError extends Error {}

function describe(err, label) {
  const name = err?.name || '';
  if (name === 'NotAllowedError' || name === 'SecurityError') return 'Camera access was refused. Allow the camera for this page in the browser (address bar), then retry.';
  if (name === 'NotReadableError' || name === 'AbortError') return 'The camera is busy: close other apps that use it (video calls, OBS…), then retry.';
  if (name === 'NotFoundError' || name === 'OverconstrainedError') {
    return label ? `Camera “${label}” not found. Is it plugged in? For a phone camera, start scrcpy/DroidCam before opening this page, then retry.` : 'No camera found.';
  }
  return String(err?.message || err);
}

async function open(constraints) {
  return navigator.mediaDevices.getUserMedia({
    audio: false,
    // resizeMode 'none': the camera's own picture, not cropped to 16:9 (a phone in portrait or 4:3 keeps its frame)
    video: { width: { ideal: 1280 }, height: { ideal: 720 }, frameRate: { ideal: 30 }, resizeMode: 'none', ...constraints },
  });
}

// Ask the server whether a network camera answers (and why not).
export async function checkNetworkCamera(url) {
  const r = await fetch(`/api/camera/check?url=${encodeURIComponent(url)}`);
  const d = await r.json().catch(() => ({}));
  if (!r.ok) throw new CameraError(d.detail || 'The phone camera did not answer.');
  return d;   // {url, label, content_type}
}

function sleepMs(ms) { return new Promise((r) => setTimeout(r, ms)); }

async function openNetworkCamera(prefs) {
  const img = new Image();
  let failed = false;
  img.onerror = () => { failed = true; if (urlSource?.img === img) emit('ended'); };
  img.src = `/api/camera/stream?url=${encodeURIComponent(prefs.url)}`;
  const t0 = performance.now();
  while (!(img.naturalWidth > 0) && !failed && performance.now() - t0 < 12000) await sleepMs(100);
  if (!(img.naturalWidth > 0)) {
    img.onerror = null; img.src = '';
    let msg = 'The phone camera did not answer.';
    try { await checkNetworkCamera(prefs.url); } catch (err) { msg = err.message; }
    throw new CameraError(msg);
  }
  const canvas = document.createElement('canvas');
  const ctx = canvas.getContext('2d');
  const draw = () => {
    const w = img.naturalWidth; const hgt = img.naturalHeight;
    if (!w) return;
    if (canvas.width !== w || canvas.height !== hgt) { canvas.width = w; canvas.height = hgt; }
    try { ctx.drawImage(img, 0, 0, w, hgt); } catch { /* frame not decodable yet */ }
  };
  draw();
  const src = { img, timers: [], stalled: false, label: prefs.label || 'Phone over Wi-Fi' };
  src.timers.push(setInterval(draw, 33));
  // a frozen picture (Wi-Fi drop, app closed) shows as identical frames: report it like a muted camera
  const probe = document.createElement('canvas');
  probe.width = 16; probe.height = 12;
  const pctx = probe.getContext('2d', { willReadFrequently: true });
  let last = null; let same = 0;
  src.timers.push(setInterval(() => {
    try { pctx.drawImage(img, 0, 0, 16, 12); } catch { return; }
    const sig = pctx.getImageData(0, 0, 16, 12).data.join(',');
    same = sig === last ? same + 1 : 0;
    last = sig;
    if (same >= 4 && !src.stalled) { src.stalled = true; if (urlSource === src) emit('muted'); }
    if (same === 0 && src.stalled) { src.stalled = false; if (urlSource === src) emit('unmuted'); }
  }, 1000));
  urlSource = src;
  return canvas.captureStream(30);
}

function closeNetworkCamera() {
  if (!urlSource) return;
  urlSource.timers.forEach(clearInterval);
  urlSource.img.onerror = null;
  urlSource.img.src = '';   // closes the relayed connection
  urlSource = null;
}

// Open the camera described by prefs ({deviceId, label} or {url}); reuses the live stream when it is the same camera.
export async function startCamera(prefs = {}) {
  if (prefs.url) {
    const key = `url:${prefs.url}`;
    if (stream && streamDevice === key && urlSource && !urlSource.stalled) return stream;
    stopCamera();
    stream = await openNetworkCamera(prefs);
    streamDevice = key;
    return stream;
  }
  if (!navigator.mediaDevices?.getUserMedia) throw new CameraError('This browser cannot access a camera (use Chrome, Edge or Firefox on http://localhost).');
  const want = prefs.deviceId || '';
  if (stream && streamDevice === want && stream.getVideoTracks().some((t) => t.readyState === 'live')) return stream;
  stopCamera();
  let s;
  try {
    s = await open(want ? { deviceId: { exact: want } } : { facingMode: 'user' });
  } catch (err) {
    if (!want || !['NotFoundError', 'OverconstrainedError'].includes(err?.name)) throw new CameraError(describe(err, prefs.label));
    // device ids change between origins (localhost vs 127.0.0.1) and after replugging: match the name instead
    const cams = await listCameras(true).catch(() => []);
    const same = prefs.label && cams.find((c) => c.label === prefs.label);
    if (!same) throw new CameraError(describe(err, prefs.label));
    try { s = await open({ deviceId: { exact: same.deviceId } }); } catch (err2) { throw new CameraError(describe(err2, prefs.label)); }
  }
  stream = s;
  streamDevice = want;
  for (const t of s.getVideoTracks()) {
    t.addEventListener('ended', () => { if (stream === s) emit('ended'); });
    t.addEventListener('mute', () => { if (stream === s) emit('muted'); });
    t.addEventListener('unmute', () => { if (stream === s) emit('unmuted'); });
  }
  return s;
}

export function stopCamera() {
  if (stream) stream.getTracks().forEach((t) => t.stop());
  closeNetworkCamera();
  stream = null;
  streamDevice = null;
}

// {deviceId, label, width, height, frameRate} of the live camera.
export function liveCamera() {
  const t = stream?.getVideoTracks()[0];
  if (!t) return { deviceId: '', label: '' };
  const st = t.getSettings ? t.getSettings() : {};
  if (urlSource) return { deviceId: '', label: urlSource.label, width: urlSource.img.naturalWidth, height: urlSource.img.naturalHeight };
  return { deviceId: st.deviceId || '', label: t.label || '', width: st.width, height: st.height, frameRate: st.frameRate };
}

export async function attachVideo(video, modality = null) {
  const s = await startCamera(modality ? cameraPrefs(modality) : {});
  video.srcObject = s;
  video.muted = true;
  video.playsInline = true;
  await video.play();
  if (video.readyState < 2) await new Promise((r) => video.addEventListener('loadeddata', r, { once: true }));
  return video;
}

// Video inputs. Labels are empty until camera access is granted; with ask=true, ask for it once to get them.
export async function listCameras(ask = false) {
  if (!navigator.mediaDevices?.enumerateDevices) return [];
  let cams = (await navigator.mediaDevices.enumerateDevices()).filter((d) => d.kind === 'videoinput');
  if (ask && cams.length && cams.every((c) => !c.label) && !stream) {
    try {
      const tmp = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
      tmp.getTracks().forEach((t) => t.stop());
      cams = (await navigator.mediaDevices.enumerateDevices()).filter((d) => d.kind === 'videoinput');
    } catch { /* permission refused: keep the unlabeled list */ }
  }
  return cams.map((c, i) => ({ deviceId: c.deviceId, label: c.label || `Camera ${i + 1}`, groupId: c.groupId }));
}

export function onDeviceChange(cb) {
  if (!navigator.mediaDevices?.addEventListener) return () => {};
  navigator.mediaDevices.addEventListener('devicechange', cb);
  return () => navigator.mediaDevices.removeEventListener('devicechange', cb);
}
