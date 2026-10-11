// Camera choice per modality, rotation, and the remembered left/right orientation of each camera.
import { api } from '../api.js';
import { refreshProfile, setProfile, state } from '../state.js';
import { h, toast } from '../ui.js';
import { cameraKey, cameraPrefs, checkNetworkCamera, discoverNetworkCameras, listCameras, liveCamera, onDeviceChange } from '../vision/camera.js';

// Options for a tracker reading this modality's camera.
export function trackerOptions(modality) {
  const prefs = cameraPrefs(modality);
  return { rotate: prefs.rotate || 0, mirrored: cameraMirrored(modality) === true, names: state.meta.face_names };
}

// true / false once checked for the camera in use, undefined before.
export function cameraMirrored(modality) {
  const m = state.profile?.settings?.camera_mirror || {};
  return m[cameraKey(cameraPrefs(modality))];
}

export async function saveMirrored(modality, mirrored) {
  const key = cameraKey(cameraPrefs(modality));
  const p = await api.patchProfile(state.profile.id, { settings: { camera_mirror: { [key]: mirrored } } });
  setProfile(p);
}

export async function forgetMirrored(modality) {
  const key = cameraKey(cameraPrefs(modality));
  const p = await api.patchProfile(state.profile.id, { settings: { camera_mirror: { [key]: null } } });
  setProfile(p);
}

async function savePrefs(modality, patch) {
  const prefs = { ...cameraPrefs(modality), ...patch };
  const p = await api.patchProfile(state.profile.id, { settings: { cameras: { [modality]: prefs } } });
  setProfile(p);
  return prefs;
}

// <select> of cameras (plus a phone camera app over Wi-Fi) + rotation. onChange(prefs) runs after the choice is saved.
const NET = '__network';
export function cameraPicker(modality, onChange) {
  let prefs = cameraPrefs(modality);
  const sel = h('select', { 'aria-label': 'Camera' }, h('option', { value: '' }, 'Automatic (default camera)'));
  const rot = h('select', { 'aria-label': 'Rotation' },
    [[0, 'Upright'], [90, 'Rotate 90° ↻'], [180, 'Upside down'], [270, 'Rotate 90° ↺']].map(([v, l]) =>
      h('option', { value: v, selected: Number(prefs.rotate || 0) === v }, l)));
  const note = h('span', { class: 'small muted' });
  // phone camera app over Wi-Fi (IP Webcam, DroidCam…)
  const urlInput = h('input', { type: 'text', placeholder: 'address shown by the phone app, e.g. 10.0.0.5:8080', value: prefs.url || '',
    style: { minWidth: '260px', flex: '1' } });
  const urlStatus = h('div', { class: 'small muted' });
  const connectTo = async (address) => {
    urlStatus.textContent = 'Connecting…';
    try {
      const r = await checkNetworkCamera(address);
      urlInput.value = r.url;
      const p = await savePrefs(modality, { deviceId: '', label: r.label, url: r.url });
      urlStatus.textContent = `Connected: ${r.label}`;
      await fill();
      onChange && onChange(p);
    } catch (err) { urlStatus.textContent = err.message; }
  };
  const connect = h('button', { class: 'btn', type: 'button', onclick: () => connectTo(urlInput.value) }, 'Connect');
  const find = h('button', { class: 'btn ghost', type: 'button', onclick: async () => {
    urlStatus.textContent = 'Looking for a phone camera app on this network…';
    const found = await discoverNetworkCameras().catch(() => []);
    if (!found.length) {
      urlStatus.textContent = 'None found. On the phone\'s hotspot, start the camera app (IP Webcam: Start server); otherwise type the address it shows.';
      return;
    }
    urlInput.value = found[0].url;
    await connectTo(found[0].url);
  } }, 'Find my phone (hotspot)');
  const urlRow = h('div', { class: 'stack', style: { gap: '4px' } },
    h('div', { class: 'row', style: { flexWrap: 'wrap' } }, urlInput, connect, find), urlStatus,
    h('div', { class: 'small muted' }, 'Start the camera app on the phone (e.g. IP Webcam → Start server), then type the address it shows. ',
      h('a', { href: '#/help/camera' }, 'Guide')));
  urlRow.hidden = !prefs.url;
  const fill = async (ask = false) => {
    prefs = cameraPrefs(modality);
    let cams = [];
    try { cams = await listCameras(ask === true); } catch { /* no camera API */ }
    const live = liveCamera();
    const current = prefs.url ? '' : (prefs.deviceId || '');
    sel.replaceChildren(h('option', { value: '' , selected: !prefs.url && !current }, `Automatic (${live.label && !current && !prefs.url ? live.label : 'default camera'})`),
      ...cams.map((c) => h('option', { value: c.deviceId, selected: !prefs.url && (c.deviceId === current || (!!prefs.label && c.label === prefs.label)) }, c.label)),
      h('option', { value: NET, selected: !!prefs.url }, prefs.url ? `${prefs.label || 'Phone over Wi-Fi'}` : 'Phone over Wi-Fi (camera app)…'));
    if (current && !cams.some((c) => c.deviceId === current || c.label === prefs.label)) {
      sel.append(h('option', { value: current, selected: true }, `${prefs.label || 'Saved camera'} (not connected)`));
    }
    urlRow.hidden = sel.value !== NET;
    note.textContent = prefs.url ? '' : !cams.length ? 'No camera found. Plug one in, or choose “Phone over Wi-Fi”, then press Refresh.'
      : cams.every((c) => /^Camera \d+$/.test(c.label)) ? 'Press Refresh and allow the camera to see the camera names.' : '';
  };
  sel.onchange = async () => {
    if (sel.value === NET) { urlRow.hidden = false; urlInput.focus(); return; }
    urlRow.hidden = true;
    const opt = sel.selectedOptions[0];
    try {
      const p = await savePrefs(modality, { deviceId: sel.value, url: '', label: sel.value ? opt.textContent.replace(/ \(not connected\)$/, '') : '' });
      onChange && onChange(p);
    } catch (err) { toast(err.message, 'error'); }
  };
  rot.onchange = async () => {
    try { const p = await savePrefs(modality, { rotate: Number(rot.value) }); onChange && onChange(p); } catch (err) { toast(err.message, 'error'); }
  };
  const refresh = h('button', { class: 'btn ghost', type: 'button', onclick: () => fill(true) }, 'Refresh');
  const off = onDeviceChange(() => fill());
  fill();
  const el = h('div', { class: 'stack', style: { gap: '6px' } },
    h('div', { class: 'row', style: { flexWrap: 'wrap' } }, sel, rot, refresh), note, urlRow);
  el.cleanup = off;
  return el;
}

// Where to put the camera and how far, for the chosen framing.
export function setupAdvice(modality, framing, stance) {
  if (modality === 'facial') return 'Sit close to the camera (50–80 cm), face the screen, light on your face (not behind you).';
  const side = stance === 'southpaw' ? 'front-left' : 'front-right';
  const where = `Face the SCREEN during the whole block, even if the camera is to one side. If the camera is not in front of you, put it ${side} of you (your ${stance} stance then turns you toward it), within 45°.`;
  return framing === 'upper'
    ? `Upper body: head to mid-thigh in view, with room above your raised hands (sitting is fine). About 1.2–1.5 m from a phone in portrait, 2–2.5 m from a laptop webcam. ${where}`
    : `Whole body: head to feet in view. About 1.7 m from a phone in portrait, 2.8 m from a laptop webcam; camera around hip height. Clear about 1.5 × 1.5 m. ${where}`;
}

export { refreshProfile };
