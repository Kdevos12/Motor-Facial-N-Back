// Camera access: one shared stream, a chosen camera per modality (e.g. the phone for moves, the laptop webcam for
// faces), rotation for a phone mounted sideways, and notice when the feed stops (unplugged, scrcpy closed...).
import { state } from '../state.js';

let stream = null;
let streamDevice = null;          // deviceId of the live stream ('' = browser default)
const listeners = new Set();

export const DEFAULT_PREFS = { deviceId: '', label: '', rotate: 0 };

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
  return !t || t.readyState !== 'live' || t.muted;
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

// Open the camera described by prefs ({deviceId, label}); reuses the live stream when it is the same camera.
export async function startCamera(prefs = {}) {
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
  stream = null;
  streamDevice = null;
}

// {deviceId, label, width, height, frameRate} of the live camera.
export function liveCamera() {
  const t = stream?.getVideoTracks()[0];
  if (!t) return { deviceId: '', label: '' };
  const st = t.getSettings ? t.getSettings() : {};
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
