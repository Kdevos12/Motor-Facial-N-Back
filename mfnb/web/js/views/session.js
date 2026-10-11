// The training session: camera check, then the block (watch -> instruction -> perform -> cue).
import { api } from '../api.js';
import { cue, setSound } from '../audio.js';
import { navigate } from '../main.js';
import { FaceAvatar, mirrorShapes } from '../render/face.js';
import { drawFaceOverlay, drawPoseOverlay } from '../render/overlay.js';
import { displayFrames } from '../render/retarget.js';
import { mirrorFrames, StickFigure } from '../render/stickman.js';
import { refreshProfile, state } from '../state.js';
import { h, itemLabel, mount, sleep, toast } from '../ui.js';
import { attachVideo, onCameraState, stopCamera, trackMuted } from '../vision/camera.js';
import { SimFaceTracker, SimPoseTracker } from '../vision/sim.js';
import { bodyCheck, FaceTracker, headOffset, headTurnSide, PoseTracker, raisedHandSide } from '../vision/trackers.js';
import { cameraMirrored, cameraPicker, saveMirrored, setupAdvice, trackerOptions } from './camera_setup.js';
import { pending } from './train.js';

const FACE_STIM_S = 2.4;

export async function sessionView(modality) {
  const prof = await refreshProfile();
  const s = prof.settings;
  setSound(s.sound);
  const cfg = pending.config && pending.config.modality === modality ? pending.config : { modality, n: null, overrides: null };
  pending.config = null;
  const simulate = state.simulate;
  if (!simulate && !state.assets.ready) {
    mount(h('div', { class: 'card stack' }, h('h2', {}, 'Computer-vision files missing'),
      h('p', {}, 'Run ', h('code', {}, 'mfnb fetch-assets'), ' once while online, then reload this page.'),
      h('a', { class: 'btn', href: `/?simulate#/train/${modality}` }, 'Try the demo mode instead')));
    return {};
  }

  // ---- shared state & teardown ---------------------------------------------------
  const ctl = { aborted: false, paused: false, tracker: null, renderer: null, unsub: [], cancelCheck: null };
  const destroy = () => {
    if (ctl.destroyed) return;
    ctl.destroyed = true;
    ctl.aborted = true;
    ctl.renderer?.stop?.();
    ctl.tracker?.stop?.();
    ctl.unsub.forEach((u) => u());
    if (ctl.cancelCheck) ctl.cancelCheck();
    if (!simulate) stopCamera();
    document.removeEventListener('keydown', onKey);
    onKeyRef.handler = null;
  };
  const onKey = (e) => {
    if (!onKeyRef.handler) return;
    if (e.code === 'Space') { e.preventDefault(); onKeyRef.handler('pause'); }
    if (e.code === 'Escape') onKeyRef.handler('end');
  };
  document.addEventListener('keydown', onKey);
  run(modality, s, cfg, simulate, ctl, prof, onKeyRef).catch((err) => {
    console.error(err);
    if (!ctl.aborted) toast(String(err.message || err), 'error');
  });
  return { destroy };
}

const onKeyRef = { handler: null };

async function run(modality, s, cfg, simulate, ctl, prof, keyRef) {
  // ---- tracker -------------------------------------------------------------------
  const video = h('video', { class: 'mirror', playsinline: true, muted: true });
  const overlay = h('canvas', { class: 'mirror' });
  try {
    if (simulate) {
      if (modality === 'motor') {
        const rest = (await api.motorItem('pose.t_pose')).frames[0];
        ctl.tracker = new SimPoseTracker(rest);
      } else {
        ctl.tracker = new SimFaceTracker(state.meta.face_names, { typicalMax: state.meta.face_typical_max, rest: state.meta.face_rest });
      }
    } else {
      await attachVideo(video, modality);
      const opts = trackerOptions(modality);
      ctl.tracker = modality === 'motor' ? new PoseTracker(video, opts) : new FaceTracker(video, opts);
    }
    if (ctl.aborted) { if (!simulate) stopCamera(); return; }
    mount(h('div', { class: 'center' }, h('div', { class: 'spinner' }), h('p', { class: 'muted' }, 'Loading the tracker…')));
    await ctl.tracker.start();
    if (ctl.aborted) { ctl.tracker.stop(); if (!simulate) stopCamera(); return; }
  } catch (err) {
    console.error(err);
    if (ctl.aborted) return;
    mount(h('div', { class: 'card stack' }, h('h2', {}, 'Camera or tracker unavailable'), h('p', { class: 'muted' }, String(err.message || err)),
      h('p', {}, 'Allow camera access in your browser (the app runs on localhost, nothing leaves this computer), then retry. You can choose another camera here:'),
      cameraPicker(modality, () => navigate(`#/session/${modality}`)),
      h('div', { class: 'row' }, h('button', { class: 'btn primary', onclick: () => navigate(`#/session/${modality}`) }, 'Retry'),
        h('a', { class: 'btn', href: '#/help/camera' }, 'Phone as a camera'),
        h('a', { class: 'btn', href: `/?simulate#/train/${modality}` }, 'Demo mode'))));
    return;
  }
  const display = simulate ? overlay : ctl.tracker.display;
  const framing = modality === 'motor' ? ((cfg.overrides && cfg.overrides.framing) || s.motor.framing || 'full') : null;

  // ---- camera check, resting reference, block ----------------------------------------
  let block;
  let problem = null;
  for (;;) {
    const ready = await cameraCheck(modality, ctl, display, overlay, simulate, prof, framing, problem);
    if (!ready || ctl.aborted) return;
    // facial: the resting face of today (light, camera and posture change between sessions)
    const faceNeutral = modality === 'facial' ? await captureNeutral(ctl) : null;
    // motor: where the camera sees you from while you face the screen
    const viewRest = modality === 'motor' && !simulate ? await captureView(ctl, framing) : null;
    if (ctl.aborted) return;
    try {
      block = await api.startBlock({ profile_id: prof.id, modality, n: cfg.n, overrides: cfg.overrides,
        face_neutral: faceNeutral, view_rest: viewRest, simulated: simulate });
      if (ctl.aborted) return;
      break;
    } catch (err) {
      if (/Fewer than 2 items/.test(err.message)) { toast(err.message, 'error'); navigate(`#/train/${modality}`); return; }
      problem = err.message;
    }
  }
  if (block.view_warning) toast(block.view_warning);

  const figureCanvas = h('canvas', { class: modality === 'motor' ? 'figure' : 'face' });
  const phase = h('div', { class: 'phase' }, '');
  const instr = h('div', { class: 'instruction' });
  const timebar = h('div', { class: 'timebar', hidden: true }, h('div', { style: { width: '0%' } }));
  const flash = h('div', { class: 'flash' });
  const nameTag = h('div', { class: 'item-name' });
  const counter = h('span', { class: 'muted' });
  const progress = h('div', { class: 'progress' }, h('div', { style: { width: '0%' } }));
  const pauseBtn = h('button', { class: 'btn', onclick: () => togglePause() }, 'Pause');
  const selfview = h('div', { class: 'selfview', hidden: true });
  if (!simulate) selfview.append(display, overlay);
  else selfview.append(overlay);
  const legend = modality === 'motor' ? h('div', { class: 'legend' },
    h('span', {}, h('i', { style: { background: 'var(--left)' } }), 'left side'),
    h('span', {}, h('i', { style: { background: 'var(--right)' } }), 'right side'),
    h('span', { class: 'muted' }, s.view === 'mirror' ? '(mirror view)' : s.view === 'back' ? '(seen from behind)' : '(facing you)')) : null;
  // the camera stopped (unplugged, phone app closed): pause until it is back
  const lostBox = h('div', { class: 'card stack lost', hidden: true },
    h('h3', {}, 'Camera stopped'),
    h('p', { class: 'muted' }, 'Reconnect it (for a phone: restart scrcpy or DroidCam), then resume.'),
    h('button', { class: 'btn primary', onclick: async () => {
      try {
        await attachVideo(video, modality);
        if (trackMuted()) { toast('Still no picture from the camera.', 'error'); return; }
        lostBox.hidden = true; ctl.cameraLost = false;
        if (ctl.paused) togglePause();
      } catch (err) { toast(err.message, 'error'); }
    } }, 'Resume'));
  mount(h('div', { class: 'stage' },
    h('div', { class: 'stage-top' },
      h('strong', {}, `${modality === 'motor' ? 'Motor' : 'Facial'} · N = ${block.n}`), counter, progress,
      pauseBtn, h('button', { class: 'btn danger', onclick: () => endBlock() }, 'End block')),
    h('div', { class: 'stage-main' }, figureCanvas, phase, instr, nameTag, timebar, selfview, legend, flash, lostBox),
    h('div', { class: 'stage-bottom small muted' }, h('span', {}, h('kbd', {}, 'Space'), ' pause · ', h('kbd', {}, 'Esc'), ' end block'))));

  if (modality === 'motor') {
    ctl.renderer = new StickFigure(figureCanvas, { view: s.view, yaw: s.camera_yaw, sideInset: s.side_view });
  } else {
    ctl.renderer = new FaceAvatar(figureCanvas, { view: s.view === 'facing' ? 'facing' : 'mirror' });
  }
  ctl.renderer.clear?.();
  if (modality === 'facial') ctl.renderer.draw({});

  // self-view overlay drawing
  ctl.unsub.push(ctl.tracker.onFrame((sample) => {
    if (selfview.hidden) return;
    if (modality === 'motor') {
      if (simulate) {
        if (!ctl.simFig) ctl.simFig = new StickFigure(overlay, { view: 'mirror', yaw: 0, grid: false });
        if (sample.joints) ctl.simFig.draw(sample.joints);
      } else drawPoseOverlay(overlay, display, sample.image);
    } else if (!simulate) drawFaceOverlay(overlay, display, sample.landmarks);
  }));

  if (!simulate) {
    ctl.unsub.push(onCameraState((what) => {
      if (what === 'unmuted') {
        // the picture is back by itself (stalled Wi-Fi stream): the user resumes when ready
        if (ctl.cameraLost) { lostBox.hidden = true; ctl.cameraLost = false; }
        return;
      }
      if (what === 'ended' || what === 'muted') {
        ctl.cameraLost = true; lostBox.hidden = false;
        if (!ctl.paused) togglePause();
      }
    }));
  }

  keyRef.handler = (what) => (what === 'pause' ? togglePause() : endBlock());
  function togglePause() {
    ctl.paused = !ctl.paused;
    pauseBtn.textContent = ctl.paused ? 'Resume' : 'Pause';
    phase.textContent = ctl.paused ? 'paused' : phase.textContent;
  }
  async function waitIfPaused() { while (ctl.paused && !ctl.aborted) await sleep(150); }
  let ending = false;
  async function endBlock() {
    if (ending) return;
    ending = true;
    ctl.aborted = true;
    ctl.renderer?.stop?.();
    try {
      await api.finish(block.block_id);
      navigate(`#/report/${block.block_id}`);
    } catch (err) { toast(err.message, 'error'); }
  }

  const items = block.items;
  const speed = s.playback_speed || 1;
  const stimDuration = (itemId) => (modality === 'motor' ? items[itemId].duration_s : FACE_STIM_S) / speed;
  const showItem = async (itemId, mirrored) => {
    if (modality === 'motor') {
      const frames = displayFrames(items[itemId].frames, mirrored);
      for (let r = 0; r < (s.stimulus_repeats || 1) && !ctl.aborted; r++) {
        await ctl.renderer.play(frames, { fps: 30, speed });
      }
    } else {
      const target = mirrored ? mirrorShapes(items[itemId].target) : items[itemId].target;
      for (let r = 0; r < (s.stimulus_repeats || 1) && !ctl.aborted; r++) await ctl.renderer.play(target, FACE_STIM_S / speed);
    }
  };
  const setInstr = (main, sub) => {
    instr.replaceChildren(main ? h('div', { class: 'text' }, main, sub ? h('span', { class: 'sub' }, sub) : null) : '');
  };

  const total = block.trials.length;
  for (const trial of block.trials) {
    if (ctl.aborted) break;
    await waitIfPaused();
    counter.textContent = `Trial ${trial.index + 1}/${total}`;
    progress.firstChild.style.width = `${(100 * trial.index) / total}%`;
    // 1. watch
    phase.textContent = 'watch';
    setInstr('');
    selfview.hidden = true;
    nameTag.textContent = s.show_names ? itemLabel(items[trial.item_id].name, trial.shown_mirrored, modality) : '';
    await showItem(trial.item_id, trial.shown_mirrored);
    if (ctl.aborted) break;
    nameTag.textContent = '';
    if (modality === 'motor') ctl.renderer.clear(); else ctl.renderer.draw({});
    if (trial.watch_only) {
      phase.textContent = 'remember it';
      await sleep(700);
      continue;
    }
    await waitIfPaused();
    // 2. instruction + countdown
    const switchSides = trial.targets.some((t) => t.mirror);
    phase.textContent = 'get ready';
    setInstr(trial.instruction.replace(/ · switch sides/g, ''), switchSides ? '⇄ switch sides' : null);
    await sleep(1300);
    for (const k of ['3', '2', '1']) {
      if (ctl.aborted) break;
      setInstr(k, switchSides ? '⇄ switch sides' : null); cue.tick(); await sleep(420);
    }
    if (ctl.aborted) break;
    // 3. perform
    const respS = (() => {
      const base = trial.targets.reduce((sum, t) => sum + stimDuration(t.item_id), 0);
      return Math.max(base * (s.response_multiplier || 2.5), base + (s.response_min_extra_s ?? 3));
    })();
    phase.textContent = 'perform';
    cue.go();
    setInstr('GO');
    setTimeout(() => {
      if (phase.textContent === 'perform') {
        instr.classList.add('dim');
        setInstr(trial.instruction.replace(/ · switch sides/g, ''), switchSides ? '⇄ switch sides' : null);
      }
    }, 500);
    if (legend) legend.hidden = true;
    selfview.hidden = !s.show_self_view;
    timebar.hidden = false;
    if (simulate) {
      if (modality === 'motor') {
        const seq = trial.targets.flatMap((t) => (t.effective_mirror ? mirrorFrames(items[t.item_id].frames) : items[t.item_id].frames));
        ctl.tracker.expect(seq);
      } else {
        const t = trial.targets[0];
        ctl.tracker.expect(t.effective_mirror ? mirrorShapes(items[t.item_id].target) : items[t.item_id].target);
      }
    }
    const rec = await ctl.tracker.record(respS, (p) => { timebar.firstChild.style.width = `${p * 100}%`; });
    if (simulate) ctl.tracker.expect(null);
    timebar.hidden = true;
    selfview.hidden = true;
    instr.classList.remove('dim');
    setInstr('');
    if (legend) legend.hidden = false;
    if (ctl.aborted) break;
    // 4. score + discreet cue
    phase.textContent = '';
    let res;
    try {
      res = await api.submit(block.block_id, trial.index, rec);
    } catch (err) { toast(err.message, 'error'); res = { valid: false }; }
    const kind = !res.valid ? 'invalid' : res.correct ? 'good' : (res.score >= (res.threshold || 0.5) - 0.15 ? 'close' : 'bad');
    flash.className = `flash ${kind}`;
    if (res.valid) (res.correct ? cue.good : cue.bad)();
    if (!res.valid) phase.textContent = res.reason || 'not tracked';
    await sleep(600);
    flash.className = 'flash';
    await sleep(Math.max(200, (s.iti_s ?? 1.5) * 1000 - 600));
  }
  if (!ending && !ctl.aborted) {
    progress.firstChild.style.width = '100%';
    await endBlock();
  }
}

// A 2-s capture is usable when the person was tracked in most of the analysed frames. Counted relative to the
// frames analysed, not as a fixed number: a slow computer analyses fewer frames per second.
function enoughTracked(rec) { return rec.frames.length >= 8 && rec.tracked >= 0.6; }

// ~2 s standing (or sitting) relaxed, facing the screen: the server measures the camera's angle from it.
async function captureView(ctl, framing) {
  const msg = h('h2', {}, 'Face the screen, arms relaxed by your sides');
  const sub = h('p', { class: 'muted' }, framing === 'upper'
    ? 'Sit or stand still, shoulders square to the screen. This measures where the camera sees you from.'
    : 'Stand still, feet together, facing the screen (not the camera). This measures where the camera sees you from.');
  mount(h('div', { class: 'center stack', style: { padding: '40px', textAlign: 'center' } }, msg, sub));
  for (let attempt = 0; attempt < 2 && !ctl.aborted; attempt++) {
    for (const k of ['3', '2', '1']) { if (ctl.aborted) return null; sub.textContent = `Hold still… ${k}`; await sleep(700); }
    sub.textContent = 'Measuring… keep still';
    const rec = await ctl.tracker.record(2);
    if (enoughTracked(rec)) return { frames: rec.frames, visibility: rec.visibility };
    msg.textContent = 'You were not tracked — step back into view';
    await sleep(1500);
  }
  return null;
}

// 2 s of the relaxed face; returns the frames or null when the face was not tracked.
async function captureNeutral(ctl) {
  const avatarCanvas = h('canvas', { class: 'face', style: { width: '200px', height: '200px' } });
  const msg = h('h2', {}, 'Relax your face and look at the screen');
  const sub = h('p', { class: 'muted' }, 'This records your resting face so each expression is judged from it.');
  mount(h('div', { class: 'center stack', style: { padding: '40px', textAlign: 'center' } }, avatarCanvas, msg, sub));
  new FaceAvatar(avatarCanvas, { view: 'mirror' }).draw({});
  for (let attempt = 0; attempt < 2 && !ctl.aborted; attempt++) {
    for (const k of ['3', '2', '1']) { if (ctl.aborted) return null; sub.textContent = `Hold a neutral face… ${k}`; await sleep(600); }
    sub.textContent = 'Recording… keep still';
    const rec = await ctl.tracker.record(2);
    if (enoughTracked(rec)) return rec.frames;
    msg.textContent = 'Your face was not tracked — move closer to the camera, light on your face';
    await sleep(1500);
  }
  return null;
}

// Returns true when the user is in frame and clicked start. Also checks once per camera whether its picture is
// mirrored (left and right swapped), with a movement of known side.
function cameraCheck(modality, ctl, display, overlay, simulate, prof, framing, problem) {
  return new Promise((resolve) => {
    const s = prof.settings;
    const items = modality === 'motor'
      ? [['person', 'Person detected'],
        ['full', framing === 'upper' ? 'Head, shoulders, arms and hands visible' : 'Whole body visible (head to feet)'],
        ['centered', framing === 'upper' ? 'Room above your head for raised hands' : 'Inside the frame']]
      : [['face', 'Face detected'], ['still', 'Face steady and well lit']];
    const needSide = !simulate && typeof cameraMirrored(modality) !== 'boolean';
    if (needSide) items.push(['side', 'Left/right check']);
    const dots = Object.fromEntries(items.map(([k]) => [k, h('span', { class: 'dot' })]));
    const startBtn = h('button', { class: 'btn primary big', disabled: !simulate, onclick: () => done(true) }, 'Start the block');
    const SIDE_ASK = modality === 'motor' ? '✋ Raise your RIGHT hand above your head for a moment.' : '↩ Now turn your head to your LEFT for a moment, then back.';
    const sidePrompt = h('p', { class: 'notice', hidden: !needSide },
      modality === 'motor' ? SIDE_ASK : 'Look straight at the screen for a moment…');
    const view = h('div', { class: 'camview' });
    if (!simulate) view.append(display, overlay);
    else view.append(overlay);
    // how many pictures per second the tracker analyses: shown so a slow computer is visible before the block
    const speed = h('p', { class: 'small muted' });
    let speedAt = 0;
    const showSpeed = () => {
      const r = ctl.tracker.rate?.() || 0;
      if (simulate || !r || performance.now() - speedAt < 1000) return;
      speedAt = performance.now();
      const where = ctl.tracker.model?.delegate === 'CPU' ? ' (on the processor: the graphics card could not be used)' : '';
      speed.textContent = `Tracking: ${Math.round(r)} pictures per second${where}.`
        + (r < 10 ? ' That is slow: close other tabs and apps, and check that hardware acceleration is on in the browser settings.' : '');
      speed.classList.toggle('notice', r < 10);
      speed.classList.toggle('warn', r < 10);
    };
    let okSince = null;
    let sideVotes = [];
    let sideDone = !needSide;
    let restOffs = [];
    let rest = null;     // facial: where the head points at rest
    const unsub = ctl.tracker.onFrame((sample) => {
      let st;
      if (modality === 'motor') {
        st = bodyCheck(sample, framing);
        if (simulate) {
          if (!ctl.checkFig) ctl.checkFig = new StickFigure(overlay, { view: 'mirror', yaw: 0 });
          if (sample.joints) ctl.checkFig.draw(sample.joints);
        } else drawPoseOverlay(overlay, display, sample.image);
      } else {
        st = { face: !!sample.shapes, still: !!sample.shapes };
        if (!simulate) drawFaceOverlay(overlay, display, sample.landmarks);
      }
      if (!sideDone) {
        let m = null;
        if (modality === 'motor') m = raisedHandSide(sample);
        else if (rest === null) {
          const o = headOffset(sample);
          if (o !== null) restOffs = [...restOffs, o].slice(-15);
          if (restOffs.length === 15 && Math.max(...restOffs) - Math.min(...restOffs) < 0.06) {
            rest = [...restOffs].sort((a, b) => a - b)[7];
            sidePrompt.textContent = SIDE_ASK;
          }
        } else m = headTurnSide(sample, rest);
        sideVotes = m === null ? sideVotes.slice(-3) : [...sideVotes, m].slice(-12);
        if (sideVotes.length >= 8 && sideVotes.every((v) => v === sideVotes[0])) {
          sideDone = true;
          const mirrored = sideVotes[0];
          ctl.tracker.mirrored = mirrored;
          sidePrompt.textContent = mirrored
            ? 'This camera sends a mirror image: left and right are now swapped back for scoring.'
            : 'Left and right are the right way round.';
          sidePrompt.classList.toggle('warn', mirrored);
          saveMirrored(modality, mirrored).catch((err) => toast(err.message, 'error'));
        }
      }
      st.side = sideDone;
      showSpeed();
      for (const [k] of items) dots[k].classList.toggle('ok', !!st[k]);
      const ok = items.every(([k]) => st[k]);
      okSince = ok ? (okSince ?? performance.now()) : null;
      startBtn.disabled = !(okSince && performance.now() - okSince > 800);
    });
    const done = (v) => { unsub(); picker.cleanup?.(); ctl.cancelCheck = null; resolve(v); };
    ctl.cancelCheck = () => done(false);
    // a different camera or rotation: restart the session page with it
    const picker = cameraPicker(modality, () => { done(false); navigate(`#/session/${modality}`); });
    const framingSwitch = modality === 'motor' ? h('div', { class: 'field' }, h('label', {}, 'Framing'),
      h('div', { class: 'row' }, h('span', {}, framing === 'upper' ? 'Upper body (head to mid-thigh)' : 'Whole body (head to feet)'),
        h('button', { class: 'btn ghost', onclick: async () => {
          const next = framing === 'upper' ? 'full' : 'upper';
          try {
            await api.patchProfile(prof.id, { settings: { motor: { framing: next } } });
            if (pending) pending.config = { modality, n: null, overrides: null };
            done(false); navigate(`#/session/${modality}`);
          } catch (err) { toast(err.message, 'error'); }
        } }, framing === 'upper' ? 'Switch to whole body' : 'Camera too close? Switch to upper body'))) : null;
    mount(h('div', { class: 'stack', style: { padding: '22px', maxWidth: '1280px', margin: '0 auto' } },
      h('h1', {}, 'Camera check'),
      problem ? h('p', { class: 'notice warn' }, problem) : null,
      h('div', { class: 'camcheck' }, view,
        h('div', { class: 'card stack' },
          h('ul', { class: 'checklist' }, items.map(([k, label]) => h('li', {}, dots[k], label))),
          sidePrompt, speed,
          h('p', { class: 'muted small' }, setupAdvice(modality, framing, s.stance)),
          modality === 'facial'
            ? h('p', { class: 'muted small' }, 'After Start you will hold a relaxed face for 2 seconds.')
            : h('p', { class: 'muted small' }, 'After Start you will stand (or sit) still for 2 seconds, facing the screen, so the app can measure the camera angle.'),
          modality === 'facial' && !(prof.calibration || {}).face
            ? h('p', { class: 'small notice' }, 'Tip: the face calibration (about a minute, in Settings) fits the scoring to your face and unlocks the mouth movements (jaw and mouth sideways, pressed or rolled lips, O lips, corners down). ',
              h('a', { href: '#/calibrate/face' }, 'Calibrate now'))
            : null,
          h('div', { class: 'row' }, startBtn, h('button', { class: 'btn ghost', onclick: () => done(true) }, 'Start anyway')),
          simulate ? null : h('details', {}, h('summary', {}, 'Camera'), picker,
            h('p', { class: 'small muted' }, h('a', { href: '#/help/camera' }, 'Using your phone as the camera'))),
          framingSwitch,
          h('a', { class: 'btn ghost', href: `#/train/${modality}` }, '← Back')))));
  });
}
