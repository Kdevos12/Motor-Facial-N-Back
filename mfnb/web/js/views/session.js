// The training session: camera check, then the block (watch -> instruction -> perform -> cue).
import { api } from '../api.js';
import { cue, setSound } from '../audio.js';
import { navigate } from '../main.js';
import { FaceAvatar, mirrorShapes } from '../render/face.js';
import { drawFaceOverlay, drawPoseOverlay } from '../render/overlay.js';
import { displayFrames } from '../render/retarget.js';
import { mirrorFrames, StickFigure } from '../render/stickman.js';
import { refreshProfile, state } from '../state.js';
import { h, mount, sleep, toast } from '../ui.js';
import { attachVideo, stopCamera } from '../vision/camera.js';
import { SimFaceTracker, SimPoseTracker } from '../vision/sim.js';
import { bodyCheck, FaceTracker, PoseTracker } from '../vision/trackers.js';
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
        ctl.tracker = new SimFaceTracker(state.meta.face_names);
      }
    } else {
      await attachVideo(video);
      ctl.tracker = modality === 'motor' ? new PoseTracker(video) : new FaceTracker(video);
    }
    if (ctl.aborted) { if (!simulate) stopCamera(); return; }
    mount(h('div', { class: 'center' }, h('div', { class: 'spinner' }), h('p', { class: 'muted' }, 'Loading the tracker…')));
    await ctl.tracker.start();
    if (ctl.aborted) { ctl.tracker.stop(); if (!simulate) stopCamera(); return; }
  } catch (err) {
    console.error(err);
    if (ctl.aborted) return;
    mount(h('div', { class: 'card stack' }, h('h2', {}, 'Camera or tracker unavailable'), h('p', { class: 'muted' }, String(err.message || err)),
      h('p', {}, 'Allow camera access in your browser (the app runs on localhost, nothing leaves this computer), then retry.'),
      h('div', { class: 'row' }, h('button', { class: 'btn primary', onclick: () => navigate(`#/session/${modality}`) }, 'Retry'),
        h('a', { class: 'btn', href: `/?simulate#/train/${modality}` }, 'Demo mode'))));
    return;
  }

  // ---- camera check --------------------------------------------------------------
  const ready = await cameraCheck(modality, ctl, video, overlay, simulate);
  if (!ready || ctl.aborted) return;

  // ---- block ---------------------------------------------------------------------
  let block;
  try {
    block = await api.startBlock({ profile_id: prof.id, modality, n: cfg.n, overrides: cfg.overrides });
    if (ctl.aborted) return;
  } catch (err) {
    toast(err.message, 'error');
    navigate(`#/train/${modality}`);
    return;
  }

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
  if (!simulate) selfview.append(video, overlay);
  else selfview.append(overlay);
  const legend = modality === 'motor' ? h('div', { class: 'legend' },
    h('span', {}, h('i', { style: { background: 'var(--left)' } }), 'left side'),
    h('span', {}, h('i', { style: { background: 'var(--right)' } }), 'right side'),
    h('span', { class: 'muted' }, s.view === 'mirror' ? '(mirror view)' : s.view === 'back' ? '(seen from behind)' : '(facing you)')) : null;
  mount(h('div', { class: 'stage' },
    h('div', { class: 'stage-top' },
      h('strong', {}, `${modality === 'motor' ? 'Motor' : 'Facial'} · N = ${block.n}`), counter, progress,
      pauseBtn, h('button', { class: 'btn danger', onclick: () => endBlock() }, 'End block')),
    h('div', { class: 'stage-main' }, figureCanvas, phase, instr, nameTag, timebar, selfview, legend, flash),
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
      } else drawPoseOverlay(overlay, video, sample.image);
    } else if (!simulate) drawFaceOverlay(overlay, video, sample.landmarks);
  }));

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
    nameTag.textContent = s.show_names ? `${items[trial.item_id].name}${trial.shown_mirrored && modality === 'motor' ? ' (other side)' : ''}` : '';
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

// Returns true when the user is in frame and clicked start.
function cameraCheck(modality, ctl, video, overlay, simulate) {
  return new Promise((resolve) => {
    const items = modality === 'motor'
      ? [['person', 'Person detected'], ['full', 'Whole body visible (head to feet)'], ['centered', 'Inside the frame']]
      : [['face', 'Face detected'], ['still', 'Face steady and well lit']];
    const dots = Object.fromEntries(items.map(([k]) => [k, h('span', { class: 'dot' })]));
    const startBtn = h('button', { class: 'btn primary big', disabled: !simulate, onclick: () => done(true) }, 'Start the block');
    const view = h('div', { class: 'camview' });
    if (!simulate) view.append(video, overlay);
    else view.append(overlay);
    let okSince = null;
    const unsub = ctl.tracker.onFrame((sample) => {
      let st;
      if (modality === 'motor') {
        st = bodyCheck(sample);
        if (simulate) {
          if (!ctl.checkFig) ctl.checkFig = new StickFigure(overlay, { view: 'mirror', yaw: 0 });
          if (sample.joints) ctl.checkFig.draw(sample.joints);
        } else drawPoseOverlay(overlay, video, sample.image);
      } else {
        st = { face: !!sample.shapes, still: !!sample.shapes };
        if (!simulate) drawFaceOverlay(overlay, video, sample.landmarks);
      }
      for (const [k] of items) dots[k].classList.toggle('ok', !!st[k]);
      const ok = items.every(([k]) => st[k]);
      okSince = ok ? (okSince ?? performance.now()) : null;
      startBtn.disabled = !(okSince && performance.now() - okSince > 800);
    });
    const done = (v) => { unsub(); ctl.cancelCheck = null; resolve(v); };
    ctl.cancelCheck = () => done(false);
    mount(h('div', { class: 'stack', style: { padding: '22px', maxWidth: '1280px', margin: '0 auto' } },
      h('h1', {}, 'Camera check'),
      h('div', { class: 'camcheck' }, view,
        h('div', { class: 'card stack' },
          h('ul', { class: 'checklist' }, items.map(([k, label]) => h('li', {}, dots[k], label))),
          modality === 'motor'
            ? h('p', { class: 'muted small' }, 'Stand 2–3 m from the camera, camera around hip height, feet visible. Clear about 1.5 × 1.5 m around you.')
            : h('p', { class: 'muted small' }, 'Sit close to the camera, face the screen, light on your face (not behind you).'),
          h('div', { class: 'row' }, startBtn, h('button', { class: 'btn ghost', onclick: () => done(true) }, 'Start anyway')),
          h('a', { class: 'btn ghost', href: `#/train/${modality}` }, '← Back')))));
  });
}
