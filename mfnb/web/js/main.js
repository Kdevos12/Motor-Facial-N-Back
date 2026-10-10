// Boot, routing and the profile switcher.
import { api } from './api.js';
import { setSound } from './audio.js';
import { loadState, setProfile, state } from './state.js';
import { h, mount, spinner, toast } from './ui.js';
import { dashboardView } from './views/dashboard.js';
import { homeView, welcomeView } from './views/home.js';
import { libraryView } from './views/library.js';
import { reportView } from './views/report.js';
import { sessionView } from './views/session.js';
import { calibrateView, settingsView } from './views/settings.js';
import { trainView } from './views/train.js';

let current = null;

const routes = [
  [/^home$/, () => homeView()],
  [/^train\/(motor|facial)$/, (m) => trainView(m[1])],
  [/^session\/(motor|facial)$/, (m) => sessionView(m[1])],
  [/^report\/(\d+)$/, (m) => reportView(Number(m[1]))],
  [/^library(?:\/(motor|facial))?$/, (m) => libraryView(m[1] || 'motor')],
  [/^dashboard$/, () => dashboardView()],
  [/^settings$/, () => settingsView()],
  [/^calibrate\/(body|face)$/, (m) => calibrateView(m[1])],
];

async function route() {
  if (current && current.destroy) { try { current.destroy(); } catch (e) { console.error(e); } }
  current = null;
  const path = (location.hash || '#/home').replace(/^#\/?/, '') || 'home';
  document.querySelectorAll('#nav a').forEach((a) => a.classList.toggle('active', path.startsWith(a.dataset.route)));
  document.getElementById('app').classList.toggle('fullscreen', path.startsWith('session/'));
  if (!state.profile) { current = welcomeView(); return; }
  for (const [re, view] of routes) {
    const m = path.match(re);
    if (m) {
      mount(spinner());
      try { current = await view(m); } catch (err) {
        console.error(err);
        mount(h('div', { class: 'card' }, h('h2', {}, 'Something went wrong'), h('p', { class: 'muted' }, String(err.message || err)),
          h('a', { class: 'btn', href: '#/home' }, 'Back home')));
      }
      return;
    }
  }
  location.hash = '#/home';
}

export function renderProfileSwitch() {
  const box = document.getElementById('profile-switch');
  if (!state.profile) { box.replaceChildren(); return; }
  const sel = h('select', {
    'aria-label': 'Profile',
    onchange: async (e) => {
      if (e.target.value === '__new') {
        const name = prompt('Name of the new profile');
        if (name && name.trim()) { setProfile(await api.createProfile(name.trim())); toast(`Profile “${name}” created`); }
      } else {
        setProfile(state.profiles.find((p) => p.id === Number(e.target.value)));
      }
      renderProfileSwitch(); setSound(state.profile.settings.sound); route();
    },
  }, state.profiles.map((p) => h('option', { value: p.id, selected: p.id === state.profile.id }, p.name)),
  h('option', { value: '__new' }, '+ New profile…'));
  box.replaceChildren(sel);
}

export function renderBanner() {
  const b = document.getElementById('banner');
  if (state.simulate) {
    b.hidden = false;
    b.replaceChildren(h('span', {}, 'Demo mode: no camera, a simulated user performs the moves. ',
      h('a', { href: '/' }, 'Leave demo mode')));
  } else if (state.assets && !state.assets.ready) {
    b.hidden = false;
    b.replaceChildren(h('span', {}, 'The computer-vision files are not downloaded yet. Run ', h('code', {}, 'mfnb fetch-assets'),
      ' once while online, then reload. Meanwhile you can browse the library or try the ', h('a', { href: '/?simulate#/home' }, 'demo mode'), '.'));
  } else { b.hidden = true; }
}

async function boot() {
  mount(spinner('Starting…'));
  try { await loadState(); } catch (err) {
    mount(h('div', { class: 'card' }, h('h2', {}, 'Cannot reach the local server'), h('p', {}, String(err))));
    return;
  }
  if (state.profile) setSound(state.profile.settings.sound);
  renderProfileSwitch();
  renderBanner();
  window.addEventListener('hashchange', route);
  route();
}

export function navigate(hash) { if (location.hash === hash) route(); else location.hash = hash; }

boot();
