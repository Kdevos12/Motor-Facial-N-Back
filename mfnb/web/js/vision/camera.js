// Camera access: one shared stream, a chosen camera per modality (e.g. the phone for moves, the laptop webcam for
// faces), rotation for a phone mounted sideways, and notice when the feed stops (unplugged, scrcpy closed...).
// A camera can also be a phone camera app on the network (prefs.url): the local server reads its MJPEG stream and
// the page turns its frames into an ordinary video stream, so everything downstream works the same.
import { state } from '../state.js';

let stream = null;
let streamDevice = null;          // deviceId of the live stream ('' = browser default, 'url:…' = network camera)
let urlSource = null;             // {alive, stalled, label, width, height} while a network camera is open
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
  return d;   // {url, label}
}

// Phone camera apps answering on this computer's gateway (the phone, when the computer is on its hotspot).
export async function discoverNetworkCameras() {
  const r = await fetch('/api/camera/discover');
  return r.ok ? (await r.json()).found : [];
}

function sleepMs(ms) { return new Promise((r) => setTimeout(r, ms)); }

// The server keeps the phone's newest frame; the page fetches frames one after the other, draws them on a canvas
// and turns the canvas into an ordinary video stream (works the same in every browser, and never queues old frames).
async function openNetworkCamera(prefs) {
  const canvas = document.createElement('canvas');
  const ctx = canvas.getContext('2d');
  const src = { alive: true, stalled: false, label: prefs.label || 'Phone over Wi-Fi', width: 0, height: 0, lastFrame: 0, error: null };
  const q = `/api/camera/frame?url=${encodeURIComponent(prefs.url)}`;
  let seq = 0;
  let first = null;
  const firstFrame = new Promise((resolve) => { first = resolve; });
  (async () => {
    let failures = 0;
    while (src.alive) {
      try {
        const r = await fetch(`${q}&after=${seq}`, { cache: 'no-store' });
        if (r.status === 204) continue;
        if (!r.ok) {
          src.error = (await r.json().catch(() => ({}))).detail || 'The phone camera stopped.';
          failures += 1;
          if (!src.lastFrame) { first(false); return; }
          await sleepMs(Math.min(3000, 400 * failures));
          continue;
        }
        failures = 0;
        seq = Number(r.headers.get('X-Frame-Seq')) || seq + 1;
        const bmp = await createImageBitmap(await r.blob());
        if (canvas.width !== bmp.width || canvas.height !== bmp.height) { canvas.width = bmp.width; canvas.height = bmp.height; }
        ctx.drawImage(bmp, 0, 0);
        src.width = bmp.width; src.height = bmp.height;
        bmp.close();
        if (!src.lastFrame) first(true);
        src.lastFrame = performance.now();
      } catch (err) {
        src.error = String(err.message || err);
        if (!src.lastFrame) { first(false); return; }
        await sleepMs(500);
      }
    }
  })();
  const ok = await Promise.race([firstFrame, sleepMs(15000).then(() => false)]);
  if (!ok) {
    src.alive = false;
    throw new CameraError(src.error || 'The phone camera did not send a picture.');
  }
  // no new frame for 3 s (Wi-Fi drop, app closed, phone asleep): report it like a muted camera
  src.watch = setInterval(() => {
    const late = performance.now() - src.lastFrame > 3000;
    if (late && !src.stalled) { src.stalled = true; if (urlSource === src) emit('muted'); }
    if (!late && src.stalled) { src.stalled = false; if (urlSource === src) emit('unmuted'); }
  }, 500);
  urlSource = src;
  return canvas.captureStream(30);
}

function closeNetworkCamera() {
  if (!urlSource) return;
  urlSource.alive = false;
  clearInterval(urlSource.watch);
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
  if (urlSource) return { deviceId: '', label: urlSource.label, width: urlSource.width, height: urlSource.height };
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
