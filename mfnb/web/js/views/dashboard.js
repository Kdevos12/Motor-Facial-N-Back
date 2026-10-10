// Progress dashboard.
import { api } from '../api.js';
import { lineChart, masteryBars } from '../charts.js';
import { FaceAvatar } from '../render/face.js';
import { peakFrame, StickFigure } from '../render/stickman.js';
import { state } from '../state.js';
import { fmtPct, h, mount } from '../ui.js';
import { label } from './train.js';

export async function dashboardView() {
  const d = await api.dashboard(state.profile.id);
  const s = state.profile.settings;
  const kpi = (value, lab) => h('div', { class: 'card kpi' }, h('span', { class: 'value' }, value), h('span', { class: 'label' }, lab));

  const section = (m) => {
    const md = d.modalities[m];
    const hist = md.history;
    const nChart = hist.length
      ? lineChart([{ name: 'N', color: m === 'motor' ? '#4ea8ff' : '#ff9a3c', points: hist.map((b) => ({ y: b.n, label: b.day })) }],
        { yMin: 0, yMax: Math.max(3, ...hist.map((b) => b.n)) + 1, xLabel: 'blocks' })
      : h('p', { class: 'muted' }, 'No block yet.');
    const accChart = hist.length
      ? lineChart([
        { name: 'Accuracy', color: '#3ecf8e', points: hist.map((b) => ({ y: b.accuracy ?? 0, label: b.day })) },
        { name: 'Mean score', color: '#7c8cff', points: hist.map((b) => ({ y: b.mean_score ?? 0, label: b.day })) }],
      { yMin: 0, yMax: 1, yFormat: (v) => `${Math.round(v * 100)}%`, xLabel: 'blocks' })
      : null;
    const rows = Object.entries(md.mastery).map(([cat, v]) => ({ label: label(cat), ...v }));
    const acc = Object.entries(md.category_accuracy);
    const gallery = h('div', { class: 'lib-grid' });
    const mastered = md.mastered.slice(0, 24);
    mastered.forEach(async (it) => {
      const canvas = h('canvas', { class: m === 'facial' ? 'face-thumb' : '' });
      gallery.append(h('div', { class: 'lib-card' }, canvas, h('div', { class: 'name' }, it.name),
        h('span', { class: 'small muted' }, `${it.successes}/${it.attempts} · best ${Math.round(it.best * 100)}`)));
      if (m === 'motor') {
        const data = await api.motorItem(it.item_id);
        new StickFigure(canvas, { view: s.view, yaw: s.camera_yaw, grid: false }).draw(peakFrame(data.frames));
      } else {
        const lib = await faceLib();
        const item = lib.find((x) => x.id === it.item_id);
        if (item) new FaceAvatar(canvas, { view: s.view === 'facing' ? 'facing' : 'mirror' }).draw(item.target);
      }
    });
    return h('div', { class: 'stack' },
      h('h2', {}, m === 'motor' ? 'Motor N-Back' : 'Facial N-Back'),
      h('div', { class: 'grid cols-4' },
        kpi(`N = ${md.current_n}`, 'next block'), kpi(md.best_n ?? '–', 'best N (≥ 60%)'),
        kpi(md.counts.mastered, `mastered of ${md.library_size}`), kpi(md.counts.learning, 'learning')),
      h('div', { class: 'grid cols-2' },
        h('div', { class: 'card' }, h('h3', {}, 'N over blocks'), nChart),
        h('div', { class: 'card' }, h('h3', {}, 'Accuracy'), accChart || h('p', { class: 'muted' }, '–'))),
      h('div', { class: 'grid cols-2' },
        h('div', { class: 'card stack' }, h('h3', {}, 'Mastery by category'),
          h('div', { class: 'row small muted' }, h('span', { class: 'tag mastered' }, 'mastered'), h('span', { class: 'tag learning' }, 'learning'), h('span', { class: 'tag' }, 'seen')),
          masteryBars(rows)),
        h('div', { class: 'card stack' }, h('h3', {}, 'Accuracy by category'),
          acc.length ? h('table', {}, h('tbody', {}, acc.map(([c, v]) => h('tr', {}, h('td', {}, label(c)), h('td', {}, fmtPct(v))))))
            : h('p', { class: 'muted' }, 'Play a block to see this.'))),
      h('div', { class: 'card stack' }, h('h3', {}, `Mastered ${m === 'motor' ? 'moves' : 'expressions'}`),
        mastered.length ? gallery : h('p', { class: 'muted' }, 'An item is mastered after 3 successes with a high average score, on at least 2 different days.')));
  };

  let faceCache = null;
  const faceLib = async () => { faceCache = faceCache || await api.faceLibrary(); return faceCache; };

  mount(h('div', { class: 'stack' },
    h('h1', {}, 'Progress'),
    h('div', { class: 'grid cols-4' },
      kpi(d.totals.blocks, 'blocks played'), kpi(`${Math.round(d.totals.minutes)} min`, 'training time'),
      kpi(d.totals.days, 'active days'), kpi(`${d.totals.streak} 🔥`, 'day streak')),
    section('motor'), section('facial'),
    h('div', { class: 'card' }, h('h3', {}, 'Recent blocks'),
      d.recent.length ? h('table', {}, h('thead', {}, h('tr', {}, ['Day', 'Game', 'N', 'Accuracy', 'Next N', ''].map((t) => h('th', {}, t)))),
        h('tbody', {}, d.recent.map((b) => h('tr', { class: 'clickable', onclick: () => { location.hash = `#/report/${b.block_id}`; } },
          h('td', {}, b.day), h('td', {}, b.modality), h('td', {}, b.n), h('td', {}, fmtPct(b.accuracy)), h('td', {}, b.next_n ?? '–'), h('td', { class: 'muted' }, 'report →')))))
        : h('p', { class: 'muted' }, 'No block yet. ', h('a', { href: '#/train/motor' }, 'Start one!')))));
  return {};
}
