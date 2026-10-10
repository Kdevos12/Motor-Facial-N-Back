// App-wide state: metadata, profiles and the active profile.
import { api } from './api.js';

const KEY = 'mfnb.profileId';
export const state = { meta: null, profiles: [], profile: null, assets: null, simulate: false };

function storedId() {
  try { return Number(localStorage.getItem(KEY)) || null; } catch { return null; }
}

export async function loadState() {
  const params = new URLSearchParams(location.search);
  state.simulate = params.has('simulate');
  [state.meta, state.profiles, state.assets] = await Promise.all([api.meta(), api.profiles(), api.assets()]);
  const id = storedId();
  state.profile = state.profiles.find((p) => p.id === id) || state.profiles[0] || null;
}

export function setProfile(p) {
  state.profile = p;
  const i = state.profiles.findIndex((x) => x.id === p.id);
  if (i >= 0) state.profiles[i] = p; else state.profiles.push(p);
  try { localStorage.setItem(KEY, String(p.id)); } catch { /* private mode */ }
}

export async function refreshProfile() {
  if (!state.profile) return null;
  const p = await api.profile(state.profile.id);
  setProfile(p);
  return p;
}

export function settings() { return state.profile ? state.profile.settings : state.meta.default_settings; }
