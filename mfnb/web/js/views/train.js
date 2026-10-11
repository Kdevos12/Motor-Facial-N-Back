// Block setup: N, categories, complexity and (motor) twists.
import { api } from '../api.js';
import { refreshProfile, state } from '../state.js';
import { chips, h, mount, segmented, toast } from '../ui.js';

export const pending = { config: null };

const LABELS = {
  'static postures': 'Static postures', boxing: 'Boxing', evasion: 'Evasion & defense', kicks: 'Kicks & knees',
  taekwondo: 'Taekwondo', karate: 'Karate', grappling: 'Shadow grappling', 'tai chi & qigong': 'Tai chi & qigong',
  dance: 'Dance', fitness: 'Fitness', 'everyday & sports': 'Everyday & sports',
  emotions: 'Emotions', 'upper face': 'Upper face', 'lower face': 'Lower face', gaze: 'Gaze', asymmetric: 'Asymmetric', combinations: 'Combinations',
};
export const label = (c) => LABELS[c] || c;

export async function trainView(modality) {
  const prof = await refreshProfile();
  const s = prof.settings;
  const ms = { ...s[modality] };
  const cats = modality === 'motor' ? state.meta.motor_categories : state.meta.face_categories;
  let n = ms.n;
  let selCats = ms.categories || [];
  let cx = [...(ms.complexity || [1, 3])];
  const nVal = h('div', { class: 'n' }, n);
  const setN = (v) => { n = Math.max(0, Math.min(12, v)); nVal.textContent = n; };
  const manual = s.n_mode === 'manual';

  const minSel = h('select', {}, [1, 2, 3, 4, 5].map((v) => h('option', { value: v, selected: v === cx[0] }, v)));
  const maxSel = h('select', {}, [1, 2, 3, 4, 5].map((v) => h('option', { value: v, selected: v === cx[1] }, v)));
  minSel.onchange = () => { cx[0] = Number(minSel.value); if (cx[0] > cx[1]) { cx[1] = cx[0]; maxSel.value = cx[1]; } };
  maxSel.onchange = () => { cx[1] = Number(maxSel.value); if (cx[1] < cx[0]) { cx[0] = cx[1]; minSel.value = cx[0]; } };
  const blockLen = h('input', { type: 'number', min: 8, max: 60, value: ms.block_base, style: { width: '90px' } });

  const twists = {};
  let twistCard = null;
  let framing = ms.framing || 'full';
  if (modality === 'motor') {
    twists.variable_n = h('input', { type: 'checkbox', checked: !!ms.variable_n });
    twists.chirality = h('input', { type: 'range', min: 0, max: 0.6, step: 0.05, value: ms.chirality_p || 0 });
    twists.sequence = h('input', { type: 'checkbox', checked: (ms.sequence_p || 0) > 0 });
    const chirLabel = h('span', { class: 'small muted' }, `${Math.round((ms.chirality_p || 0) * 100)}% of trials`);
    twists.chirality.oninput = () => { chirLabel.textContent = `${Math.round(twists.chirality.value * 100)}% of trials`; };
    twistCard = h('div', { class: 'card stack' }, h('h3', {}, 'Twists'),
      h('label', { class: 'switch' }, h('span', {}, 'Variable N', h('div', { class: 'small muted' }, 'Some trials ask for N−1 or N+1.')), twists.variable_n),
      h('div', { class: 'field' }, h('label', {}, 'Switch sides (chirality) instructions'), twists.chirality, chirLabel),
      h('label', { class: 'switch' }, h('span', {}, 'Sequence mode (experimental)', h('div', { class: 'small muted' }, '“Do N−2 then N”: two moves in a row.')), twists.sequence),
      h('div', { class: 'field' }, h('label', {}, 'Framing'),
        segmented([['full', 'Whole body'], ['upper', 'Upper body (close camera / seated)']], framing, (v) => { framing = v; })),
      h('p', { class: 'small muted' }, 'Upper body uses only arm and trunk moves and does not score the legs. ',
        h('a', { href: '#/help/camera' }, 'Or use your phone as the camera'), '.'));
  }

  const start = async () => {
    if (n === 0 && !manual) setN(1);
    const overrides = { categories: selCats, complexity: cx, block_base: Number(blockLen.value) || 20 };
    if (modality === 'motor') {
      overrides.variable_n = twists.variable_n.checked;
      overrides.chirality_p = Number(twists.chirality.value);
      overrides.sequence_p = twists.sequence.checked ? 0.3 : 0;
      overrides.framing = framing;
    }
    try {
      await api.patchProfile(prof.id, { settings: { [modality]: { ...overrides, ...(manual ? { n } : {}) } } });
      await refreshProfile();
    } catch (err) { toast(err.message, 'error'); return; }
    pending.config = { modality, n: manual ? n : null, overrides };
    location.hash = `#/session/${modality}`;
  };

  mount(h('div', { class: 'stack' },
    h('div', { class: 'row between' },
      h('div', {}, h('h1', {}, modality === 'motor' ? 'Motor N-Back' : 'Facial N-Back'),
        h('p', { class: 'muted' }, modality === 'motor'
          ? 'Watch each move. When prompted, perform the move shown N trials earlier.'
          : 'Watch each expression. When prompted, make the expression shown N trials earlier.')),
      h('button', { class: 'btn primary big', onclick: start }, 'Start block')),
    h('div', { class: 'grid cols-2' },
      h('div', { class: 'card stack' }, h('h3', {}, 'N'),
        manual
          ? h('div', { class: 'n-picker' }, h('button', { class: 'btn', onclick: () => setN(n - 1) }, '−'), nVal,
            h('button', { class: 'btn', onclick: () => setN(n + 1) }, '+'),
            h('span', { class: 'muted small' }, 'N = 0 is pure imitation practice.'))
          : h('div', {}, h('div', { class: 'n-picker' }, nVal, h('span', { class: 'muted' }, 'Adaptive: ≥ 85% correct → N+1, < 60% → N−1.'))),
        h('div', { class: 'field' }, h('label', {}, 'Mode'), segmented([['adaptive', 'Adaptive'], ['manual', 'Manual']], s.n_mode, async (v) => {
          await api.patchProfile(prof.id, { settings: { n_mode: v } });
          await refreshProfile(); trainView(modality);
        })),
        h('div', { class: 'row' }, h('div', { class: 'field' }, h('label', {}, 'Trials per block (+ N)'), blockLen))),
      h('div', { class: 'card stack' }, h('h3', {}, 'Complexity'),
        h('p', { class: 'muted small' }, modality === 'motor'
          ? '1 = static posture · 2 = single move · 3 = two-part combo or arm + leg · 4–5 = longer combos.'
          : '1 = single action · 2 = one-sided · 3 = two regions · 4–5 = asymmetric or three regions.'),
        h('div', { class: 'row' }, h('span', {}, 'From'), minSel, h('span', {}, 'to'), maxSel))),
    h('div', { class: 'card stack' }, h('h3', {}, 'Categories'), h('p', { class: 'muted small' }, 'None selected = everything. Variety helps transfer.'),
      chips(cats.map((c) => [c, label(c)]), selCats, (v) => { selCats = v; })),
    twistCard,
    modality === 'motor' ? h('p', { class: 'muted small' }, `Filters from your profile: flexibility ${s.flexibility}, space ${s.space}, stance ${s.stance}. Change them in `, h('a', { href: '#/settings' }, 'Settings'), '.') : null));
  return {};
}
