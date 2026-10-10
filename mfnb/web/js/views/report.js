// End-of-block report with per-trial replay.
import { api } from '../api.js';
import { FaceAvatar, mirrorShapes } from '../render/face.js';
import { displayFrames } from '../render/retarget.js';
import { StickFigure } from '../render/stickman.js';
import { state } from '../state.js';
import { fmtPct, h, modal, mount } from '../ui.js';

function groundFrames(frames) {
  let low = Infinity;
  for (const f of frames) for (const k of [15, 16, 17, 18]) low = Math.min(low, f[k][1]);
  if (!Number.isFinite(low)) return frames;
  return frames.map((f) => f.map(([x, y, z]) => [x, y - low + 0.02, z]));
}

function scoreBar(score, threshold, ok) {
  const color = ok === null ? 'var(--muted)' : ok ? 'var(--good)' : 'var(--bad)';
  return h('div', { class: 'scorebar', title: `score ${Math.round(score * 100)} / needed ${Math.round((threshold || 0) * 100)}` },
    h('div', { style: { width: `${Math.round(score * 100)}%`, background: color } }),
    threshold ? h('i', { style: { left: `${threshold * 100}%` } }) : null);
}

export async function reportView(bid) {
  const rep = await api.block(bid, true);
  const s = state.profile.settings;
  const motor = rep.modality === 'motor';
  const items = rep.items;
  const results = Object.fromEntries(rep.trials_results.map((t) => [t.idx, t]));
  const sum = rep.summary;
  const name = (id) => (items[id] ? items[id].name : id);
  const targetDesc = (tr) => tr.targets.map((t) => `${name(t.item_id)}${t.effective_mirror ? ' (mirrored)' : ''}`).join(' → ');

  const openReplay = (tr) => {
    const res = results[tr.index];
    const left = h('canvas', {});
    const right = h('canvas', {});
    const info = h('div', { class: 'stack' });
    const r = res && res.result;
    if (r) {
      info.replaceChildren(...[
        h('p', {}, `Score ${Math.round(res.score * 100)} (needed ${Math.round((r.threshold || 0) * 100)}) — `,
          res.valid ? (res.correct ? h('strong', { style: { color: 'var(--good)' } }, 'correct') : h('strong', { style: { color: 'var(--bad)' } }, 'not quite'))
            : h('strong', {}, `not scored: ${r.reason}`)),
        res.confused_with ? h('p', { class: 'muted' }, `Your movement matched “${name(res.confused_with)}” better (another recent item).`) : null,
        r.worst_bones && r.worst_bones.length ? h('p', { class: 'muted' }, `Largest differences: ${r.worst_bones.map((b) => `${b} (${Math.round(r.per_bone_deg[b])}°)`).join(', ')}.`) : null,
        r.keyposes && r.keyposes.length ? h('p', { class: 'muted' }, `Key poses reproduced: ${r.keyposes.filter((k) => k.hit).length}/${r.keyposes.length}.`) : null,
        r.missing && r.missing.length ? h('p', { class: 'muted' }, `Missing: ${r.missing.join(', ')}.`) : null,
        r.extra && r.extra.length ? h('p', { class: 'muted' }, `Extra: ${r.extra.join(', ')}.`) : null].filter(Boolean));
    }
    const close = modal(h('div', { class: 'stack' },
      h('h2', {}, `Trial ${tr.index + 1}: ${targetDesc(tr)}`),
      h('div', { class: 'replay' }, h('div', {}, h('div', { class: 'label' }, 'Target'), left), h('div', {}, h('div', { class: 'label' }, 'You'), right)),
      info, h('div', { class: 'row' }, h('button', { class: 'btn', onclick: () => close() }, 'Close'))), { onClose: () => stopAll() });
    const players = [];
    const stopAll = () => players.forEach((p) => p.stop());
    if (motor) {
      const target = tr.targets.flatMap((t) => displayFrames(items[t.item_id].frames, t.effective_mirror));
      const a = new StickFigure(left, { view: s.view, yaw: s.camera_yaw });
      players.push(a); a.play(target, { loop: true });
      if (res && res.response && res.response.frames && res.response.frames.length) {
        const b = new StickFigure(right, { view: s.view, yaw: s.camera_yaw });
        players.push(b); b.play(groundFrames(res.response.frames), { loop: true });
      }
    } else {
      const t = tr.targets[0];
      const target = t.effective_mirror ? mirrorShapes(items[t.item_id].target) : items[t.item_id].target;
      const view = s.view === 'facing' ? 'facing' : 'mirror';
      new FaceAvatar(left, { view }).draw(target);
      if (res && res.response && res.response.frames && res.response.frames.length) {
        const names = state.meta.face_names;
        const frames = res.response.frames;
        let best = frames[0]; let bestSum = -1;
        for (const f of frames) { const sm = f.reduce((a, b) => a + b, 0); if (sm > bestSum) { bestSum = sm; best = f; } }
        const shapes = {};
        (best.length === 52 ? names : names.slice(1)).forEach((n, i) => { shapes[n] = best[i]; });
        new FaceAvatar(right, { view }).draw(shapes);
      }
    }
  };

  const rows = rep.trials.map((tr) => {
    const res = results[tr.index];
    const scored = res && !tr.watch_only;
    return h('tr', { class: scored ? 'clickable' : '', onclick: scored ? () => openReplay(tr) : null },
      h('td', {}, tr.index + 1),
      h('td', {}, name(tr.item_id), tr.shown_mirrored ? h('span', { class: 'tag', style: { marginLeft: '6px' } }, 'mirrored') : null),
      h('td', {}, tr.watch_only ? h('span', { class: 'muted' }, 'watch') : h('span', {}, h('span', { class: 'tag' }, tr.instruction), ' ', targetDesc(tr))),
      h('td', {}, scored ? scoreBar(res.score || 0, res.result?.threshold, res.valid ? !!res.correct : null) : ''),
      h('td', {}, !scored ? '' : !res.valid ? h('span', { class: 'muted' }, res.result?.reason || 'not scored') : res.correct ? '✓' : '✗'),
      h('td', { class: 'muted small' }, scored && res.confused_with ? `matched ${name(res.confused_with)}` : ''));
  });

  const nextN = sum.next_n;
  const nMsg = nextN === null || nextN === undefined ? '' : nextN > rep.n ? `Great block: next N = ${nextN} ↑` : nextN < rep.n ? `Next N = ${nextN} ↓ (consolidate)` : `Next N stays at ${nextN}`;
  mount(h('div', { class: 'stack' },
    h('div', { class: 'row between' }, h('h1', {}, `${motor ? 'Motor' : 'Facial'} block report`),
      h('div', { class: 'row' }, h('a', { class: 'btn primary', href: `#/train/${rep.modality}` }, 'Next block'), h('a', { class: 'btn', href: '#/dashboard' }, 'Progress'))),
    h('div', { class: 'grid cols-4' },
      h('div', { class: 'card kpi' }, h('span', { class: 'value' }, `N = ${rep.n}`), h('span', { class: 'label' }, 'this block')),
      h('div', { class: 'card kpi' }, h('span', { class: 'value' }, fmtPct(sum.accuracy)), h('span', { class: 'label' }, 'correct')),
      h('div', { class: 'card kpi' }, h('span', { class: 'value' }, sum.mean_score === null ? '–' : Math.round(sum.mean_score * 100)), h('span', { class: 'label' }, 'mean score')),
      h('div', { class: 'card kpi' }, h('span', { class: 'value' }, nextN ?? '–'), h('span', { class: 'label' }, nMsg || 'next N'))),
    h('div', { class: 'card' }, h('p', { class: 'muted small' }, 'Click a trial to replay the target next to what you did.'),
      h('table', {}, h('thead', {}, h('tr', {}, ['#', 'Shown', 'To perform', 'Score', '', ''].map((t) => h('th', {}, t)))), h('tbody', {}, rows)))));
  return {};
}
