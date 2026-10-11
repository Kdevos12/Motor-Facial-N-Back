// Thin JSON API client.
async function req(method, url, body) {
  const res = await fetch(url, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  let data = null;
  try { data = await res.json(); } catch { /* empty body */ }
  if (!res.ok) {
    const msg = (data && (typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail))) || res.statusText;
    throw new Error(msg);
  }
  return data;
}

export const api = {
  meta: () => req('GET', '/api/meta'),
  assets: () => req('GET', '/api/assets/status'),
  profiles: () => req('GET', '/api/profiles'),
  createProfile: (name, settings) => req('POST', '/api/profiles', { name, settings }),
  profile: (id) => req('GET', `/api/profiles/${id}`),
  patchProfile: (id, patch) => req('PATCH', `/api/profiles/${id}`, patch),
  deleteProfile: (id) => req('DELETE', `/api/profiles/${id}`),
  calibrateBody: (id, frames, framing = 'full') => req('PUT', `/api/profiles/${id}/calibration/body`, { frames, framing }),
  calibrateFace: (id, body) => req('PUT', `/api/profiles/${id}/calibration/face`, body),
  setExcluded: (id, modality, itemId, excluded) =>
    req('PUT', `/api/profiles/${id}/exclusions/${modality}/${encodeURIComponent(itemId)}`, { excluded }),
  motorLibrary: (pid) => req('GET', `/api/library/motor${pid ? `?profile_id=${pid}` : ''}`),
  motorItem: (id) => req('GET', `/api/library/motor/${encodeURIComponent(id)}`),
  faceLibrary: (pid) => req('GET', `/api/library/facial${pid ? `?profile_id=${pid}` : ''}`),
  startBlock: (body) => req('POST', '/api/blocks', body),
  block: (id, report = false) => req('GET', `/api/blocks/${id}${report ? '?report=true' : ''}`),
  submit: (bid, idx, body) => req('POST', `/api/blocks/${bid}/trials/${idx}/response`, body),
  finish: (bid) => req('POST', `/api/blocks/${bid}/finish`),
  dashboard: (pid) => req('GET', `/api/dashboard/${pid}`),
  progress: (pid, modality) => req('GET', `/api/progress/${pid}/${modality}`),
};
