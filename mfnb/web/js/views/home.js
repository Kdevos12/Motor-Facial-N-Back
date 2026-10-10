import { api } from '../api.js';
import { navigate, renderProfileSwitch } from '../main.js';
import { setProfile, state } from '../state.js';
import { h, mount, segmented, toast } from '../ui.js';

export function welcomeView() {
  let flex = 'medium';
  let stance = 'orthodox';
  const name = h('input', { type: 'text', placeholder: 'Your name', maxlength: 60, autofocus: true });
  const create = async () => {
    if (!name.value.trim()) { name.focus(); return; }
    const p = await api.createProfile(name.value.trim(), { flexibility: flex, stance });
    state.profiles.push(p);
    setProfile(p);
    renderProfileSwitch();
    toast('Profile created. Calibrate your body in Settings whenever you like.');
    navigate('#/home');
  };
  mount(h('div', { class: 'grid', style: { maxWidth: '720px', margin: '30px auto' } },
    h('div', { class: 'card hero stack' },
      h('h1', {}, 'Welcome'),
      h('p', { class: 'muted' }, 'Train your motor and facial working memory: watch a move or an expression, then reproduce the one shown N turns earlier. Your webcam tracks you, everything stays on this computer.'),
      h('div', { class: 'field' }, h('label', {}, 'Profile name'), name),
      h('div', { class: 'field' }, h('label', {}, 'Lower-body flexibility (filters kicks and deep stances)'),
        segmented([['low', 'Low'], ['medium', 'Medium'], ['high', 'High']], flex, (v) => { flex = v; })),
      h('div', { class: 'field' }, h('label', {}, 'Fighting stance (mirrors stance-based moves)'),
        segmented([['orthodox', 'Orthodox (left foot forward)'], ['southpaw', 'Southpaw (right foot forward)']], stance, (v) => { stance = v; })),
      h('div', { class: 'row' }, h('button', { class: 'btn primary big', onclick: create }, 'Create profile')))));
  name.addEventListener('keydown', (e) => { if (e.key === 'Enter') create(); });
  return {};
}

export async function homeView() {
  const p = state.profile;
  const s = p.settings;
  const lib = state.meta.library;
  const card = (modality, title, desc, emoji) => h('div', { class: 'card hero stack' },
    h('div', { class: 'row between' }, h('h2', {}, `${emoji} ${title}`),
      h('span', { class: 'tag' }, s.n_mode === 'adaptive' ? 'adaptive N' : 'manual N')),
    h('p', { class: 'muted' }, desc),
    h('div', { class: 'row' },
      h('div', { class: 'kpi' }, h('span', { class: 'value' }, `N = ${s[modality].n}`), h('span', { class: 'label' }, 'next block')),
      h('div', { class: 'kpi', style: { marginLeft: '24px' } }, h('span', { class: 'value' }, lib[modality].total),
        h('span', { class: 'label' }, modality === 'motor' ? 'moves in the library' : 'expressions'))),
    h('div', { class: 'row' },
      h('a', { class: 'btn primary big', href: `#/train/${modality}` }, 'Train'),
      h('a', { class: 'btn ghost', href: `#/library/${modality}` }, 'Browse')));
  mount(h('div', { class: 'stack' },
    h('div', {}, h('h1', {}, `Hi ${p.name}`), h('p', { class: 'muted' }, 'Pick a game. Each block adapts N to your accuracy.')),
    h('div', { class: 'grid cols-2' },
      card('motor', 'Motor N-Back', 'A stick figure shows a move. Perform the move shown N trials earlier: boxing, kicks, taekwondo, grappling, tai chi, dance, yoga…', '🥋'),
      card('facial', 'Facial N-Back', 'A face shows an expression. Reproduce the expression shown N trials earlier.', '🙂')),
    h('div', { class: 'grid cols-3' },
      h('div', { class: 'card' }, h('h3', {}, '1. Set up'), h('p', { class: 'muted small' },
        'Place the camera at hip height, 2–3 m away, so your whole body (feet included) is visible. Good, even lighting helps.')),
      h('div', { class: 'card' }, h('h3', {}, '2. Watch, then perform'), h('p', { class: 'muted small' },
        'Each trial shows a new item. When prompted, perform the item from N trials back. You get 2–3× the move\'s duration.')),
      h('div', { class: 'card' }, h('h3', {}, '3. Track progress'), h('p', { class: 'muted small' },
        'See which moves and expressions you have mastered and how your N evolves in Progress.')))));
  return {};
}
