// Camera choice per modality, rotation, and the remembered left/right orientation of each camera.
import { api } from '../api.js';
import { refreshProfile, setProfile, state } from '../state.js';
import { h, toast } from '../ui.js';
import { cameraKey, cameraPrefs, listCameras, liveCamera, onDeviceChange } from '../vision/camera.js';

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

// <select> of cameras + rotation. onChange(prefs) runs after the choice is saved.
export function cameraPicker(modality, onChange) {
  const prefs = cameraPrefs(modality);
  const sel = h('select', { 'aria-label': 'Camera' }, h('option', { value: '' }, 'Automatic (default camera)'));
  const rot = h('select', { 'aria-label': 'Rotation' },
    [[0, 'Upright'], [90, 'Rotate 90° ↻'], [180, 'Upside down'], [270, 'Rotate 90° ↺']].map(([v, l]) =>
      h('option', { value: v, selected: Number(prefs.rotate || 0) === v }, l)));
  const note = h('span', { class: 'small muted' });
  const fill = async (ask = false) => {
    let cams = [];
    try { cams = await listCameras(ask === true); } catch { /* no camera API */ }
    const live = liveCamera();
    const current = prefs.deviceId || '';
    sel.replaceChildren(h('option', { value: '' }, `Automatic (${live.label && !current ? live.label : 'default camera'})`),
      ...cams.map((c) => h('option', { value: c.deviceId, selected: c.deviceId === current || (!!prefs.label && c.label === prefs.label) }, c.label)));
    if (current && !cams.some((c) => c.deviceId === current || c.label === prefs.label)) {
      sel.append(h('option', { value: current, selected: true }, `${prefs.label || 'Saved camera'} (not connected)`));
    }
    note.textContent = !cams.length ? 'No camera found. Plug one in (or start the phone app), then press Refresh.'
      : cams.every((c) => /^Camera \d+$/.test(c.label)) ? 'Press Refresh and allow the camera to see the camera names.' : '';
  };
  sel.onchange = async () => {
    const opt = sel.selectedOptions[0];
    try {
      const p = await savePrefs(modality, { deviceId: sel.value, label: sel.value ? opt.textContent.replace(/ \(not connected\)$/, '') : '' });
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
    h('div', { class: 'row', style: { flexWrap: 'wrap' } }, sel, rot, refresh), note);
  el.cleanup = off;
  return el;
}

// Where to put the camera and how far, for the chosen framing.
export function setupAdvice(modality, framing, stance) {
  if (modality === 'facial') return 'Sit close to the camera (50–80 cm), face the screen, light on your face (not behind you).';
  const side = stance === 'southpaw' ? 'front-left' : 'front-right';
  const where = `Face the SCREEN during the whole block, even if the camera is to one side. If the camera is not in front of you, put it ${side} of you (your ${stance} stance then turns you toward it), within 45°.`;
  return framing === 'upper'
    ? `Upper body: head to mid-thigh in view, with room above your raised hands (sitting is fine). About 1.2–1.5 m from a phone in portrait, 1.5–2 m from a laptop webcam. ${where}`
    : `Whole body: head to feet in view. About 1.7 m from a phone in portrait, 2.8 m from a laptop webcam; camera around hip height. Clear about 1.5 × 1.5 m. ${where}`;
}

export { refreshProfile };
