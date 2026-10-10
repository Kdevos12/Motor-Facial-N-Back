// Minimal SVG charts.
import { h } from './ui.js';

const NS = 'http://www.w3.org/2000/svg';
function s(tag, attrs = {}, ...kids) {
  const el = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
  kids.flat().forEach((k) => k && el.append(k instanceof Node ? k : document.createTextNode(k)));
  return el;
}

// series: [{name, color, points: [{x: index, y}]}]
export function lineChart(series, { height = 220, yMin = 0, yMax = null, yFormat = (v) => v, xLabel = '' } = {}) {
  const W = 640; const H = height; const pad = { l: 40, r: 14, t: 12, b: 28 };
  const all = series.flatMap((se) => se.points);
  const n = Math.max(1, ...series.map((se) => se.points.length));
  const top = yMax ?? Math.max(1, ...all.map((p) => p.y));
  const x = (i) => pad.l + (n <= 1 ? (W - pad.l - pad.r) / 2 : (i * (W - pad.l - pad.r)) / (n - 1));
  const y = (v) => H - pad.b - ((v - yMin) / (top - yMin || 1)) * (H - pad.t - pad.b);
  const svg = s('svg', { viewBox: `0 0 ${W} ${H}`, role: 'img' });
  const ticks = 4;
  for (let k = 0; k <= ticks; k++) {
    const v = yMin + ((top - yMin) * k) / ticks;
    svg.append(s('line', { class: 'grid-line', x1: pad.l, x2: W - pad.r, y1: y(v), y2: y(v) }));
    svg.append(s('text', { x: pad.l - 6, y: y(v) + 4, 'text-anchor': 'end' }, String(yFormat(Math.round(v * 100) / 100))));
  }
  svg.append(s('text', { x: W - pad.r, y: H - 6, 'text-anchor': 'end' }, xLabel));
  for (const se of series) {
    if (!se.points.length) continue;
    const d = se.points.map((p, i) => `${i ? 'L' : 'M'}${x(i)},${y(p.y)}`).join(' ');
    svg.append(s('path', { d, fill: 'none', stroke: se.color, 'stroke-width': 2.5, 'stroke-linejoin': 'round' }));
    se.points.forEach((p, i) => svg.append(s('circle', { cx: x(i), cy: y(p.y), r: 3.5, fill: se.color },
      s('title', {}, `${se.name}: ${yFormat(p.y)}${p.label ? ` (${p.label})` : ''}`))));
  }
  const legend = h('div', { class: 'row small muted' }, series.map((se) =>
    h('span', { class: 'row', style: { gap: '6px' } }, h('i', { style: { width: '14px', height: '4px', background: se.color, display: 'inline-block', borderRadius: '2px' } }), se.name)));
  return h('div', { class: 'chart' }, svg, series.length > 1 ? legend : null);
}

// rows: [{label, mastered, learning, seen, total}]
export function masteryBars(rows) {
  return h('div', { class: 'bars' }, rows.map((r) => {
    const pct = (v) => `${(100 * v) / Math.max(1, r.total)}%`;
    return h('div', { class: 'bar-row' },
      h('span', {}, r.label),
      h('div', { class: 'track' },
        h('div', { class: 'seg-m', style: { width: pct(r.mastered) }, title: `${r.mastered} mastered` }),
        h('div', { class: 'seg-l', style: { width: pct(r.learning) }, title: `${r.learning} learning` }),
        h('div', { class: 'seg-s', style: { width: pct(r.seen) }, title: `${r.seen} seen` })),
      h('span', { class: 'small muted' }, `${r.mastered}/${r.total}`));
  }));
}
