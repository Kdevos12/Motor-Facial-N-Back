// Profile settings and calibration flows.
import { api } from '../api.js';
import { setSound } from '../audio.js';
import { navigate, renderProfileSwitch } from '../main.js';
import { FaceAvatar } from '../render/face.js';
import { drawFaceOverlay, drawPoseOverlay } from '../render/overlay.js';
import { StickFigure } from '../render/stickman.js';
import { refreshProfile, setProfile, state } from '../state.js';
import { h, mount, segmented, sleep, toast } from '../ui.js';
import { attachVideo, stopCamera } from '../vision/camera.js';
import { SimFaceTracker, SimPoseTracker } from '../vision/sim.js';
import { bodyCheck, FaceTracker, PoseTracker } from '../vision/trackers.js';

export async function settingsView() {
  const prof = await refreshProfile();
  const s = prof.settings;
  const save = async (patch) => {
    try {
      const p = await api.patchProfile(prof.id, { settings: patch });
      setProfile(p); setSound(p.settings.sound);
      toast('Saved');
    } catch (err) { toast(err.message, 'error'); }
  };
  const range = (key, min, max, step, fmt) => {
    const out = h('span', { class: 'small muted' }, fmt(s[key]));
    const input = h('input', { type: 'range', min, max, step, value: s[key] });
    input.oninput = () => { out.textContent = fmt(Number(input.value)); };
    input.onchange = () => save({ [key]: Number(input.value) });
    return h('div', { class: 'field' }, input, out);
  };
  const toggle = (key, label, hint) => {
    const input = h('input', { type: 'checkbox', checked: !!s[key], onchange: (e) => save({ [key]: e.target.checked }) });
    return h('label', { class: 'switch' }, h('span', {}, label, hint ? h('div', { class: 'small muted' }, hint) : null), input);
  };
  const seg = (key, label, options) => h('div', { class: 'field' }, h('label', {}, label), segmented(options, s[key], (v) => save({ [key]: v })));
  const nameInput = h('input', { type: 'text', value: prof.name, maxlength: 60 });
  const cal = prof.calibration || {};

  // preview of the view settings
  const preview = h('canvas', { style: { width: '100%', height: '240px', background: 'var(--bg-2)', borderRadius: '10px' } });
  const jab = await api.motorItem('combo.jab+cross');

  mount(h('div', { class: 'stack' },
    h('h1', {}, 'Settings'),
    h('div', { class: 'grid cols-2' },
      h('div', { class: 'card stack' }, h('h3', {}, 'Body & space'),
        seg('flexibility', 'Lower-body flexibility', [['low', 'Low'], ['medium', 'Medium'], ['high', 'High']]),
        h('p', { class: 'muted small' }, 'Hides moves needing more flexibility and makes leg angles more tolerant.'),
        seg('space', 'Training space', [['small', '2–3 m²'], ['medium', '4–6 m²'], ['large', 'Large']]),
        seg('stance', 'Fighting stance', [['orthodox', 'Orthodox'], ['southpaw', 'Southpaw']]),
        toggle('allow_turn_away', 'Allow moves that turn your back to the camera', 'Tracking is less reliable when you face away.'),
        h('div', { class: 'row' },
          h('a', { class: 'btn', href: '#/calibrate/body' }, cal.body ? 'Recalibrate body' : 'Calibrate body'),
          h('span', { class: 'small muted' }, cal.body ? `arm ${Math.round((cal.body.upper_arm + cal.body.forearm) * 100)} cm · leg ${Math.round((cal.body.thigh + cal.body.shin) * 100)} cm` : 'Optional: adapts the figure to your proportions.'))),
      h('div', { class: 'card stack' }, h('h3', {}, 'Display'),
        seg('view', 'Stimulus view', [['mirror', 'Mirror'], ['facing', 'Facing you'], ['back', 'From behind']]),
        h('p', { class: 'muted small' }, 'Mirror: the figure moves like your reflection. From behind: you copy it like a teacher in front of you.'),
        range('camera_yaw', 0, 60, 5, (v) => `Camera angle ${v}°`),
        toggle('side_view', 'Side-view inset', 'A small side view helps with moves toward the camera.'),
        preview,
        toggle('show_names', 'Show move names', 'Off by default so you remember the movement, not a word.'),
        toggle('show_self_view', 'Show yourself while performing'),
        toggle('sound', 'Sound cues'))),
    h('div', { class: 'grid cols-2' },
      h('div', { class: 'card stack' }, h('h3', {}, 'Pacing & tolerance'),
        h('div', { class: 'field' }, h('label', {}, 'Stimulus speed'), range('playback_speed', 0.5, 1.5, 0.05, (v) => `${v.toFixed(2)}×`)),
        h('div', { class: 'field' }, h('label', {}, 'Response window'), range('response_multiplier', 2, 3, 0.1, (v) => `${v.toFixed(1)}× the move's duration`)),
        h('div', { class: 'field' }, h('label', {}, 'Pause between trials'), range('iti_s', 0.5, 4, 0.25, (v) => `${v.toFixed(2)} s`)),
        h('div', { class: 'field' }, h('label', {}, 'Strictness'), range('strictness', 0.7, 1.3, 0.05, (v) => (v < 0.9 ? `lenient (${v.toFixed(2)})` : v > 1.1 ? `strict (${v.toFixed(2)})` : `normal (${v.toFixed(2)})`))),
        h('div', { class: 'field' }, h('label', {}, 'Times each stimulus is shown'), segmented([[1, 'Once'], [2, 'Twice']], s.stimulus_repeats, (v) => save({ stimulus_repeats: v })))),
      h('div', { class: 'card stack' }, h('h3', {}, 'Face'),
        h('p', { class: 'muted small' }, 'Facial calibration records your resting face and how strongly you can smile, raise your brows, etc., so expressions are judged relative to you.'),
        h('div', { class: 'row' }, h('a', { class: 'btn', href: '#/calibrate/face' }, cal.face ? 'Recalibrate face' : 'Calibrate face'),
          h('span', { class: 'small muted' }, cal.face ? 'calibrated' : 'not calibrated yet')),
        h('h3', {}, 'Profile'),
        h('div', { class: 'row' }, nameInput, h('button', { class: 'btn', onclick: async () => {
          const p = await api.patchProfile(prof.id, { name: nameInput.value.trim() || prof.name });
          setProfile(p); renderProfileSwitch(); toast('Renamed');
        } }, 'Rename')),
        h('button', { class: 'btn danger', onclick: async () => {
          if (!confirm(`Delete the profile “${prof.name}” and all its progress?`)) return;
          await api.deleteProfile(prof.id);
          state.profiles = state.profiles.filter((p) => p.id !== prof.id);
          state.profile = state.profiles[0] || null;
          renderProfileSwitch(); navigate('#/home');
        } }, 'Delete this profile')))));
  const fig = new StickFigure(preview, { view: s.view, yaw: s.camera_yaw, sideInset: s.side_view });
  fig.play(jab.frames, { loop: true });
  return { destroy: () => fig.stop() };
}

// ---------------------------------------------------------------------------------
export async function calibrateView(kind) {
  const prof = await refreshProfile();
  const simulate = state.simulate;
  const video = h('video', { class: 'mirror', playsinline: true, muted: true });
  const overlay = h('canvas', { class: 'mirror' });
  const status = h('p', { class: 'muted' }, 'Starting the camera…');
  const big = h('h2', {}, '');
  const view = h('div', { class: 'camview' });
  if (!simulate) view.append(video, overlay); else view.append(overlay);
  const ctl = { stop: false, tracker: null };
  mount(h('div', { class: 'stack' }, h('h1', {}, kind === 'body' ? 'Body calibration' : 'Face calibration'),
    h('div', { class: 'camcheck' }, view, h('div', { class: 'card stack' }, big, status,
      h('a', { class: 'btn ghost', href: '#/settings' }, 'Cancel')))));
  const destroy = () => { ctl.stop = true; ctl.tracker?.stop(); if (!simulate) stopCamera(); };
  (async () => {
    try {
      if (simulate) {
        ctl.tracker = kind === 'body' ? new SimPoseTracker((await api.motorItem('pose.t_pose')).frames[0]) : new SimFaceTracker(state.meta.face_names);
      } else {
        await attachVideo(video);
        ctl.tracker = kind === 'body' ? new PoseTracker(video) : new FaceTracker(video);
      }
      await ctl.tracker.start();
    } catch (err) { status.textContent = `Camera unavailable: ${err.message || err}`; return; }
    if (ctl.stop) { destroy(); return; }
    let simFig = null;
    ctl.tracker.onFrame((sm) => {
      if (kind === 'body') {
        if (simulate) { simFig = simFig || new StickFigure(overlay, { view: 'mirror', yaw: 0 }); if (sm.joints) simFig.draw(sm.joints); }
        else drawPoseOverlay(overlay, video, sm.image);
      } else if (!simulate) drawFaceOverlay(overlay, video, sm.landmarks);
    });
    const countdown = async (text, seconds = 3) => {
      for (let k = seconds; k > 0 && !ctl.stop; k--) { big.textContent = `${text} in ${k}…`; await sleep(800); }
    };
    if (kind === 'body') {
      big.textContent = 'Stand relaxed, arms slightly away from the body, whole body in view.';
      status.textContent = 'Waiting until your whole body is visible…';
      while (!ctl.stop && !bodyCheck(ctl.tracker.latest).full) await sleep(200);
      if (ctl.stop) return;
      await countdown('Hold still');
      big.textContent = 'Hold still…';
      const rec = await ctl.tracker.record(3);
      if (ctl.stop) return;
      try {
        const dims = await api.calibrateBody(prof.id, rec.frames);
        big.textContent = 'Done!';
        status.textContent = `Measured: upper arm ${Math.round(dims.upper_arm * 100)} cm, forearm ${Math.round(dims.forearm * 100)} cm, thigh ${Math.round(dims.thigh * 100)} cm, shin ${Math.round(dims.shin * 100)} cm.`;
      } catch (err) { status.textContent = err.message; return; }
    } else {
      const prompts = [
        ['neutral', 'Relax your face (neutral)', {}],
        ['smile', 'Smile as wide as you can', { mouthSmileLeft: 0.9, mouthSmileRight: 0.9, cheekSquintLeft: 0.5, cheekSquintRight: 0.5 }],
        ['brows_up', 'Raise your eyebrows as high as you can', { browInnerUp: 0.9, browOuterUpLeft: 0.9, browOuterUpRight: 0.9 }],
        ['frown', 'Frown hard', { browDownLeft: 0.9, browDownRight: 0.9 }],
        ['jaw_open', 'Open your mouth wide', { jawOpen: 0.9 }],
        ['pucker', 'Pucker your lips (kiss)', { mouthPucker: 0.9 }],
        ['wink_left', 'Wink with your LEFT eye', { eyeBlinkLeft: 0.95 }],
      ];
      const data = {};
      const avatarCanvas = h('canvas', { class: 'face', style: { width: '220px' } });
      status.replaceWith(h('div', { class: 'stack' }, avatarCanvas, status));
      const avatar = new FaceAvatar(avatarCanvas, { view: 'mirror' });
      while (!ctl.stop && !(ctl.tracker.latest && ctl.tracker.latest.shapes)) { status.textContent = 'Looking for your face…'; await sleep(200); }
      for (const [key, text, shapes] of prompts) {
        if (ctl.stop) return;
        avatar.draw(shapes);
        status.textContent = text;
        await countdown(text, 2);
        big.textContent = `${text} — hold`;
        if (simulate) ctl.tracker.expect(key === 'wink_left' ? { eyeBlinkLeft: 0.9 } : shapes, { correct: true, delay: 0 });
        const rec = await ctl.tracker.record(2);
        data[key] = rec.frames;
      }
      if (ctl.stop) return;
      try {
        const { neutral, wink_left: wink, ...rest } = data;
        const res = await api.calibrateFace(prof.id, { neutral, wink_left: wink, prompts: rest });
        big.textContent = 'Done!';
        status.textContent = res.lr_swap ? 'Calibrated (left/right mapping corrected for your camera).' : 'Calibrated.';
      } catch (err) { status.textContent = err.message; return; }
    }
    await refreshProfile();
    await sleep(1500);
    if (!ctl.stop) navigate('#/settings');
  })();
  return { destroy };
}
