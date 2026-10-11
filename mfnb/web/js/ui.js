// Tiny DOM helpers, modal and toast.
export function h(tag, attrs = {}, ...children) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === null || v === undefined || v === false) continue;
    if (k === 'class') el.className = v;
    else if (k === 'style' && typeof v === 'object') Object.assign(el.style, v);
    else if (k.startsWith('on') && typeof v === 'function') el.addEventListener(k.slice(2).toLowerCase(), v);
    else if (k === 'html') el.innerHTML = v;
    else if (v === true) el.setAttribute(k, '');
    else el.setAttribute(k, v);
  }
  for (const c of children.flat(Infinity)) {
    if (c === null || c === undefined || c === false) continue;
    el.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  return el;
}

// A camera <video> taken out of the page is paused by the browser and stays paused when it is put back, which
// froze the camera after the camera check. Screen changes park it, still in the page, until a view takes it back.
function parkVideos(app) {
  const live = [...app.querySelectorAll('video')].filter((v) => v.srcObject?.active);
  let park = document.getElementById('video-park');
  if (!park) {
    if (!live.length) return;
    park = h('div', { id: 'video-park', 'aria-hidden': 'true', style: { position: 'fixed', left: '0', top: '0', width: '2px',
      height: '2px', overflow: 'hidden', opacity: '0.01', pointerEvents: 'none', zIndex: '-1' } });
    document.body.append(park);
  }
  for (const v of park.querySelectorAll('video')) if (!v.srcObject?.active) v.remove();
  park.append(...live);
}

export function mount(el) {
  const app = document.getElementById('app');
  parkVideos(app);
  app.replaceChildren(el);
  return app;
}

export function toast(msg, kind = '') {
  const root = document.getElementById('toast-root');
  const t = h('div', { class: `toast ${kind}` }, msg);
  root.append(t);
  setTimeout(() => t.remove(), kind === 'error' ? 6000 : 3200);
}

export function modal(content, { onClose } = {}) {
  const root = document.getElementById('modal-root');
  const close = () => { back.remove(); document.removeEventListener('keydown', esc); onClose && onClose(); };
  const esc = (e) => { if (e.key === 'Escape') close(); };
  const back = h('div', { class: 'modal-backdrop', onclick: (e) => { if (e.target === back) close(); } },
    h('div', { class: 'modal', role: 'dialog' }, content));
  document.addEventListener('keydown', esc);
  root.append(back);
  return close;
}

export function spinner(text = 'Loading…') {
  return h('div', { class: 'center' }, h('div', {}, h('div', { class: 'spinner', style: { margin: '0 auto 12px' } }), h('div', { class: 'muted' }, text)));
}

export function chips(options, selected, onChange, { multi = true } = {}) {
  const sel = new Set(selected);
  const wrap = h('div', { class: 'chips' });
  const render = () => {
    wrap.replaceChildren(...options.map(([value, label]) => h('span', {
      class: `chip ${sel.has(value) ? 'on' : ''}`, role: 'button', tabindex: 0,
      onclick: () => {
        if (multi) { sel.has(value) ? sel.delete(value) : sel.add(value); }
        else { sel.clear(); sel.add(value); }
        render(); onChange([...sel]);
      },
    }, label)));
  };
  render();
  return wrap;
}

export function segmented(options, value, onChange) {
  const wrap = h('div', { class: 'segmented' });
  const render = () => wrap.replaceChildren(...options.map(([v, label]) =>
    h('button', { class: v === value ? 'on' : '', type: 'button', onclick: () => { value = v; render(); onChange(v); } }, label)));
  render();
  return wrap;
}

export function fmtPct(x) { return x === null || x === undefined ? '–' : `${Math.round(x * 100)}%`; }
export function sleep(ms) { return new Promise((r) => setTimeout(r, ms)); }
export function titleCase(s) { return s.charAt(0).toUpperCase() + s.slice(1); }

// Item name as shown: a mirrored facial item names the other side ("left eye" -> "right eye").
export function itemLabel(name, mirrored, modality) {
  if (!mirrored) return name;
  if (modality === 'motor') return `${name} (other side)`;
  const swapped = name.replace(/\b(left|right|Left|Right)\b/g, (w) => ({ left: 'right', right: 'left', Left: 'Right', Right: 'Left' }[w]));
  return swapped === name ? `${name} (other side)` : swapped;
}
