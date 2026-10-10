// Library browser: filter, preview, exclude.
import { api } from '../api.js';
import { FaceAvatar } from '../render/face.js';
import { peakFrame, StickFigure } from '../render/stickman.js';
import { state } from '../state.js';
import { chips, h, modal, mount, segmented, toast } from '../ui.js';
import { label } from './train.js';

const PAGE = 48;

export async function libraryView(modality) {
  const pid = state.profile.id;
  const s = state.profile.settings;
  const all = modality === 'motor' ? await api.motorLibrary(pid) : await api.faceLibrary(pid);
  const cats = modality === 'motor' ? state.meta.motor_categories : state.meta.face_categories;
  const f = { cats: [], q: '', cx: 0, status: 'all', page: 0 };
  const grid = h('div', { class: 'lib-grid' });
  const count = h('span', { class: 'muted small' });
  const more = h('button', { class: 'btn', onclick: () => { f.page += 1; render(false); } }, 'Show more');
  const observers = [];
  let thumbFrames = {};

  const filtered = () => all.filter((it) => (!f.cats.length || f.cats.includes(it.category))
    && (!f.q || it.name.toLowerCase().includes(f.q))
    && (!f.cx || it.complexity === f.cx)
    && (f.status === 'all' || (f.status === 'excluded' ? it.excluded : f.status === 'unavailable' ? it.available === false : it.status === f.status)));

  const io = new IntersectionObserver((entries) => {
    for (const e of entries) {
      if (!e.isIntersecting) continue;
      io.unobserve(e.target);
      drawThumb(e.target);
    }
  }, { rootMargin: '200px' });
  observers.push(io);

  async function drawThumb(canvas) {
    const id = canvas.dataset.id;
    if (modality === 'motor') {
      const it = all.find((x) => x.id === id);
      if (!thumbFrames[id]) thumbFrames[id] = it.thumb || peakFrame((await api.motorItem(id)).frames);
      new StickFigure(canvas, { view: s.view, yaw: s.camera_yaw, grid: false }).draw(thumbFrames[id]);
    } else {
      const it = all.find((x) => x.id === id);
      new FaceAvatar(canvas, { view: s.view === 'facing' ? 'facing' : 'mirror' }).draw(it.target);
    }
  }

  const card = (it) => {
    const canvas = h('canvas', { 'data-id': it.id, class: modality === 'facial' ? 'face-thumb' : '' });
    io.observe(canvas);
    return h('div', { class: `lib-card ${it.excluded ? 'excluded' : ''}`, onclick: () => open(it) },
      canvas, h('div', { class: 'name' }, it.name),
      h('div', { class: 'row', style: { gap: '6px' } },
        h('span', { class: 'tag' }, label(it.category)), h('span', { class: 'tag' }, `C${it.complexity}`),
        it.status === 'mastered' ? h('span', { class: 'tag mastered' }, 'mastered') : it.status === 'learning' ? h('span', { class: 'tag learning' }, 'learning') : null,
        it.available === false ? h('span', { class: 'tag' }, 'filtered') : null));
  };

  function render(reset = true) {
    if (reset) f.page = 0;
    const list = filtered();
    count.textContent = `${list.length} ${modality === 'motor' ? 'moves' : 'expressions'}`;
    const slice = list.slice(0, (f.page + 1) * PAGE);
    grid.replaceChildren(...slice.map(card));
    more.hidden = slice.length >= list.length;
  }

  async function open(it) {
    const canvas = h('canvas', { class: modality === 'motor' ? '' : 'face', style: { width: '100%', height: modality === 'motor' ? '380px' : 'auto', background: 'var(--bg-2)', borderRadius: '12px' } });
    const exclude = h('input', { type: 'checkbox', checked: it.excluded });
    exclude.onchange = async () => {
      await api.setExcluded(pid, modality, it.id, exclude.checked);
      it.excluded = exclude.checked; render(false); toast(exclude.checked ? 'Excluded from training' : 'Included in training');
    };
    let player = null;
    const facts = modality === 'motor' ? [
      ['Category', `${label(it.category)} · ${it.subcategory}`], ['Complexity', it.complexity], ['Flexibility', it.flexibility],
      ['Duration', `${it.duration_s.toFixed(1)} s`], ['Footprint', `${Math.round(it.footprint_m * 100)} cm`], ['Turns', `${Math.round(it.rotation_deg)}°`],
      ['Body', it.body_part], ['Source', it.source], ['Parts', it.segments.length],
    ] : [['Category', label(it.category)], ['Complexity', it.complexity], ['Regions', it.regions.join(', ')], ['One-sided', it.sided ? 'yes' : 'no']];
    const close = modal(h('div', { class: 'stack' },
      h('div', { class: 'row between' }, h('h2', {}, it.name), h('span', { class: `tag ${it.status}` }, it.status)),
      canvas,
      h('div', { class: 'grid cols-3' }, facts.map(([k, v]) => h('div', {}, h('div', { class: 'label' }, k), h('div', {}, String(v))))),
      it.description ? h('p', { class: 'muted' }, it.description) : null,
      h('label', { class: 'switch' }, h('span', {}, 'Exclude from training (injury, dislike, not possible here)'), exclude),
      h('div', { class: 'row' }, h('button', { class: 'btn', onclick: () => close() }, 'Close'))), { onClose: () => player && player.stop() });
    if (modality === 'motor') {
      const data = await api.motorItem(it.id);
      player = new StickFigure(canvas, { view: s.view, yaw: s.camera_yaw, sideInset: s.side_view });
      player.play(data.frames, { loop: true });
    } else {
      player = new FaceAvatar(canvas, { view: s.view === 'facing' ? 'facing' : 'mirror' });
      const loop = async () => { while (document.body.contains(canvas)) await player.play(it.target, 2.4); };
      loop();
    }
  }

  const search = h('input', { type: 'text', placeholder: 'Search…', oninput: (e) => { f.q = e.target.value.toLowerCase(); render(); } });
  mount(h('div', { class: 'stack' },
    h('div', { class: 'row between' }, h('h1', {}, 'Library'),
      segmented([['motor', 'Moves'], ['facial', 'Expressions']], modality, (v) => { location.hash = `#/library/${v}`; })),
    h('div', { class: 'toolbar' }, search,
      segmented([[0, 'All levels'], [1, '1'], [2, '2'], [3, '3'], [4, '4'], [5, '5']], 0, (v) => { f.cx = v; render(); }),
      segmented([['all', 'All'], ['mastered', 'Mastered'], ['learning', 'Learning'], ['excluded', 'Excluded']].concat(modality === 'motor' ? [['unavailable', 'Filtered out']] : []), 'all', (v) => { f.status = v; render(); }),
      count),
    chips(cats.map((c) => [c, label(c)]), [], (v) => { f.cats = v; render(); }),
    grid, h('div', { class: 'row', style: { justifyContent: 'center' } }, more)));
  render();
  return { destroy: () => observers.forEach((o) => o.disconnect()) };
}
