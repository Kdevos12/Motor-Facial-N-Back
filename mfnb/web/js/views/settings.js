// Profile settings and calibration flows.
import { api } from '../api.js';
import { cue, setSound } from '../audio.js';
import { navigate, renderProfileSwitch } from '../main.js';
import { FaceAvatar } from '../render/face.js';
import { drawFaceOverlay, drawPoseOverlay } from '../render/overlay.js';
import { displayFrames } from '../render/retarget.js';
import { StickFigure } from '../render/stickman.js';
import { refreshProfile, setProfile, state } from '../state.js';
import { h, mount, segmented, sleep, toast } from '../ui.js';
import { attachVideo, stopCamera } from '../vision/camera.js';
import { cameraMirrored, cameraPicker, forgetMirrored, trackerOptions } from './camera_setup.js';
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
  const pickers = [];

  mount(h('div', { class: 'stack' },
    h('h1', {}, 'Settings'),
    h('div', { class: 'grid cols-2' },
      h('div', { class: 'card stack' }, h('h3', {}, 'Body & space'),
        seg('flexibility', 'Lower-body flexibility', [['low', 'Low'], ['medium', 'Medium'], ['high', 'High']]),
        h('p', { class: 'muted small' }, 'Hides moves needing more flexibility and makes leg angles more tolerant.'),
        seg('space', 'Training space', [['small', '2–3 m²'], ['medium', '4–6 m²'], ['large', 'Large']]),
        seg('stance', 'Fighting stance', [['orthodox', 'Orthodox'], ['southpaw', 'Southpaw']]),
        h('div', { class: 'field' }, h('label', {}, 'Framing (motor)'),
          segmented([['full', 'Whole body'], ['upper', 'Upper body']], s.motor.framing || 'full', (v) => save({ motor: { framing: v } }))),
        h('p', { class: 'muted small' }, 'Upper body: for a camera that cannot be placed far enough, or sitting. Only arm and trunk moves are used and the legs are not scored; keep head to mid-thigh in view.'),
        toggle('allow_turn_away', 'Allow moves that turn your back to the camera', 'Tracking is less reliable when you face away. Judged from where the camera actually is (measured at the start of each block).'),
        h('div', { class: 'row' },
          h('a', { class: 'btn', href: '#/calibrate/body' }, cal.body ? 'Recalibrate body' : 'Calibrate body'),
          h('span', { class: 'small muted' }, cal.body ? `arm ${Math.round((cal.body.upper_arm + cal.body.forearm) * 100)} cm · leg ${Math.round((cal.body.thigh + cal.body.shin) * 100)} cm` : 'Optional: adapts the figure to your proportions.'))),
      h('div', { class: 'card stack' }, h('h3', {}, 'Display'),
        seg('view', 'Stimulus view', [['mirror', 'Mirror'], ['facing', 'Facing you'], ['back', 'From behind']]),
        h('p', { class: 'muted small' }, 'Mirror: the figure moves like your reflection. From behind: you copy it like a teacher in front of you.'),
        range('camera_yaw', 0, 60, 5, (v) => `Figure turned ${v}° (drawing only)`),
        toggle('side_view', 'Side-view inset', 'A small side view helps with moves toward the camera.'),
        preview,
        toggle('show_names', 'Show move names', 'Off by default so you remember the movement, not a word.'),
        toggle('show_self_view', 'Show yourself while performing'),
        toggle('sound', 'Sound cues'))),
    h('div', { class: 'card stack' }, h('h3', {}, 'Cameras'),
      h('p', { class: 'muted small' }, 'Choose a camera for each game, e.g. your phone for the moves (it fits your body at a shorter distance) and the laptop webcam for faces. ',
        h('a', { href: '#/help/camera' }, 'How to use your phone as a camera'), '.'),
      h('div', { class: 'grid cols-2' },
        ...['motor', 'facial'].map((m) => {
          const known = cameraMirrored(m);
          const picker = cameraPicker(m, () => toast('Camera saved'));
          pickers.push(picker);
          return h('div', { class: 'stack' }, h('strong', {}, m === 'motor' ? 'Moves (body)' : 'Expressions (face)'),
            picker,
            h('div', { class: 'row small muted' },
              typeof known === 'boolean' ? (known ? 'Mirror image (corrected)' : 'Left/right checked') : 'Left/right is checked at the next block',
              typeof known === 'boolean' ? h('button', { class: 'btn ghost', onclick: async () => { await forgetMirrored(m); toast('Will check again'); } }, 'Check again') : null));
        }))),
    h('div', { class: 'grid cols-2' },
      h('div', { class: 'card stack' }, h('h3', {}, 'Pacing & tolerance'),
        h('div', { class: 'field' }, h('label', {}, 'Stimulus speed'), range('playback_speed', 0.5, 1.5, 0.05, (v) => `${v.toFixed(2)}×`)),
        h('div', { class: 'field' }, h('label', {}, 'Response window'), range('response_multiplier', 2, 3, 0.1, (v) => `${v.toFixed(1)}× the move's duration`)),
        h('div', { class: 'field' }, h('label', {}, 'Pause between trials'), range('iti_s', 0.5, 4, 0.25, (v) => `${v.toFixed(2)} s`)),
        h('div', { class: 'field' }, h('label', {}, 'Strictness'), range('strictness', 0.7, 1.3, 0.05, (v) => (v < 0.9 ? `lenient (${v.toFixed(2)})` : v > 1.1 ? `strict (${v.toFixed(2)})` : `normal (${v.toFixed(2)})`))),
        h('div', { class: 'field' }, h('label', {}, 'Times each stimulus is shown'), segmented([[1, 'Once'], [2, 'Twice']], s.stimulus_repeats, (v) => save({ stimulus_repeats: v })))),
      h('div', { class: 'card stack' }, h('h3', {}, 'Face'),
        h('p', { class: 'muted small' }, 'Facial calibration (about a minute) measures how far each movement goes on your face, so expressions are judged relative to you, and unlocks the mouth movements the tracker can see on your face. Your resting face is also recorded at the start of each facial block.'),
        h('div', { class: 'row' }, h('a', { class: 'btn', href: '#/calibrate/face' }, cal.face ? 'Recalibrate face' : 'Calibrate face'),
          h('span', { class: 'small muted' }, cal.face ? `calibrated · ${(cal.face.measured || []).length} movements measured${cal.face.lr_swap ? ' · mirrored camera' : ''}` : 'not calibrated yet')),
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
  fig.play(displayFrames(jab.frames), { loop: true });
  return { destroy: () => { fig.stop(); pickers.forEach((p) => p.cleanup?.()); } };
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
  const modality = kind === 'body' ? 'motor' : 'facial';
  const framing = kind === 'body' ? (prof.settings.motor.framing || 'full') : null;
  if (simulate) view.append(overlay);
  const ctl = { stop: false, tracker: null };
  mount(h('div', { class: 'stack' }, h('h1', {}, kind === 'body' ? 'Body calibration' : 'Face calibration'),
    h('div', { class: 'camcheck' }, view, h('div', { class: 'card stack' }, big, status,
      h('a', { class: 'btn ghost', href: '#/settings' }, 'Cancel')))));
  const destroy = () => { ctl.stop = true; ctl.tracker?.stop(); if (!simulate) stopCamera(); };
  (async () => {
    try {
      if (simulate) {
        ctl.tracker = kind === 'body' ? new SimPoseTracker((await api.motorItem('pose.t_pose')).frames[0]) : new SimFaceTracker(state.meta.face_names, { typicalMax: state.meta.face_typical_max, rest: state.meta.face_rest });
      } else {
        await attachVideo(video, modality);
        const opts = trackerOptions(modality);
        ctl.tracker = kind === 'body' ? new PoseTracker(video, opts) : new FaceTracker(video, opts);
        view.append(ctl.tracker.display, overlay);
      }
      await ctl.tracker.start();
    } catch (err) { status.textContent = `Camera unavailable: ${err.message || err}`; return; }
    if (ctl.stop) { destroy(); return; }
    let simFig = null;
    ctl.tracker.onFrame((sm) => {
      if (kind === 'body') {
        if (simulate) { simFig = simFig || new StickFigure(overlay, { view: 'mirror', yaw: 0 }); if (sm.joints) simFig.draw(sm.joints); }
        else drawPoseOverlay(overlay, ctl.tracker.display, sm.image);
      } else if (!simulate) drawFaceOverlay(overlay, ctl.tracker.display, sm.landmarks);
    });
    const countdown = async (text, seconds = 3) => {
      for (let k = seconds; k > 0 && !ctl.stop; k--) { big.textContent = `${text} in ${k}…`; await sleep(800); }
    };
    if (kind === 'body') {
      big.textContent = framing === 'upper'
        ? 'Sit or stand relaxed, arms slightly away from the body, head to mid-thigh in view.'
        : 'Stand relaxed, arms slightly away from the body, whole body in view.';
      status.textContent = framing === 'upper' ? 'Waiting until your head, arms and hands are visible…' : 'Waiting until your whole body is visible…';
      while (!ctl.stop && !bodyCheck(ctl.tracker.latest, framing).full) await sleep(200);
      if (ctl.stop) return;
      await countdown('Hold still');
      big.textContent = 'Hold still…';
      const rec = await ctl.tracker.record(3);
      if (ctl.stop) return;
      try {
        const dims = await api.calibrateBody(prof.id, rec.frames, framing);
        big.textContent = 'Done!';
        status.textContent = `Measured: upper arm ${Math.round(dims.upper_arm * 100)} cm, forearm ${Math.round(dims.forearm * 100)} cm` +
          (framing === 'upper' ? ' (legs: default proportions, they are out of view).' : `, thigh ${Math.round(dims.thigh * 100)} cm, shin ${Math.round(dims.shin * 100)} cm.`);
      } catch (err) { status.textContent = err.message; return; }
    } else {
      // [key, instruction, avatar shapes]; the first three set the reference and the left/right check
      const prompts = [
        ['neutral', 'Relax your face (neutral), look at the screen', {}],
        ['wink_left', 'Wink with your LEFT eye (close only that one)', { eyeBlinkLeft: 0.95, cheekSquintLeft: 0.3 }],
        ['smile', 'Smile as wide as you can', { mouthSmileLeft: 0.9, mouthSmileRight: 0.9, cheekSquintLeft: 0.5, cheekSquintRight: 0.5 }],
        ['brows_up', 'Raise your eyebrows as high as you can', { browInnerUp: 0.9, browOuterUpLeft: 0.9, browOuterUpRight: 0.9 }],
        ['frown', 'Frown: pull your eyebrows down', { browDownLeft: 0.9, browDownRight: 0.9 }],
        ['eyes_closed', 'Close both eyes (open them when you hear the beep)', { eyeBlinkLeft: 0.95, eyeBlinkRight: 0.95 }],
        ['jaw_open', 'Open your mouth wide', { jawOpen: 0.9, mouthLowerDownLeft: 0.3, mouthLowerDownRight: 0.3 }],
        ['pucker', 'Pucker your lips (kiss)', { mouthPucker: 0.9 }],
        ['upper_lip', 'Wrinkle your nose and lift your upper lip', { noseSneerLeft: 0.7, noseSneerRight: 0.7, mouthUpperUpLeft: 0.7, mouthUpperUpRight: 0.7 }],
        ['mouth_frown', 'Pull the corners of your mouth down', { mouthFrownLeft: 0.8, mouthFrownRight: 0.8, mouthShrugLower: 0.3 }],
        ['funnel', "Round your lips into an 'O'", { mouthFunnel: 0.85, jawOpen: 0.25 }],
        ['lips_press', 'Press your lips together hard', { mouthPressLeft: 0.8, mouthPressRight: 0.8, mouthClose: 0.3 }],
        ['lips_roll', 'Roll your lips in (hide them)', { mouthRollLower: 0.8, mouthRollUpper: 0.8 }],
        ['jaw_left', 'Move your jaw to your LEFT', { jawLeft: 0.8 }],
        ['mouth_left', 'Move your mouth to your LEFT', { mouthLeft: 0.85 }],
      ];
      const data = {};
      const avatarCanvas = h('canvas', { class: 'face', style: { width: '220px' } });
      const steps = h('div', { class: 'steps' });
      let skip = false;
      const skipBtn = h('button', { class: 'btn ghost', onclick: () => { skip = true; ctl.tracker.stopRecording?.(); } }, "Skip this one (I can't do it)");
      status.before(avatarCanvas, steps);
      status.after(skipBtn);
      big.after(h('p', { class: 'muted small' }, 'Copy the face on the left. Each movement is held for 2 seconds; do it clearly but without strain. Skipped movements stay out of your training.'));
      const avatar = new FaceAvatar(avatarCanvas, { view: 'mirror' });
      while (!ctl.stop && !(ctl.tracker.latest && ctl.tracker.latest.shapes)) { status.textContent = 'Looking for your face…'; await sleep(200); }
      for (const [k, [key, text, shapes]] of prompts.entries()) {
        if (ctl.stop) return;
        skip = false;
        skipBtn.hidden = k < 3;
        steps.textContent = `Step ${k + 1} of ${prompts.length}`;
        avatar.draw(shapes);
        status.textContent = text;
        await countdown(text, 2);
        if (skip) continue;
        big.textContent = `${text} — hold`;
        if (simulate) ctl.tracker.expect(shapes, { correct: true, delay: 0 });
        const rec = await ctl.tracker.record(2);
        if (key === 'eyes_closed') cue.tick();
        if (!skip && rec.frames.length >= 10) data[key] = rec.frames;
      }
      if (ctl.stop) return;
      skipBtn.remove();
      try {
        const { neutral, wink_left: wink, ...rest } = data;
        if (!neutral) throw new Error('Your face was not tracked during the neutral step. Move closer to the camera and try again.');
        const res = await api.calibrateFace(prof.id, { neutral, wink_left: wink, prompts: rest });
        big.textContent = 'Done!';
        const unlocked = (res.measured || []).length;
        status.textContent = `Calibrated: ${unlocked} facial movements measured on your face.`;
        if (res.side_check === 'mirrored') {
          status.after(h('p', { class: 'small notice warn' }, 'Your wink showed up on the right eye: this camera sends a mirrored image. Left and right are now swapped for scoring.'));
        } else if (res.side_check === 'unclear') {
          status.after(h('p', { class: 'small notice' }, "The wink did not show clearly on one eye, so left/right could not be checked (that's fine if you can't wink). If one-sided expressions keep failing, recalibrate."));
        }
      } catch (err) { status.textContent = err.message; return; }
    }
    await refreshProfile();
    await sleep(1500);
    if (!ctl.stop) navigate('#/settings');
  })();
  return { destroy };
}
