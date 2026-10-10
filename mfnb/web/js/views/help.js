// Help pages, written in Markdown under web/help/ and rendered here (headings, paragraphs, lists, code).
import { h, mount } from '../ui.js';

function inline(text) {
  // `code`, **bold**, *italic*
  const out = [];
  const re = /(`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*)/g;
  let last = 0;
  for (const m of text.matchAll(re)) {
    if (m.index > last) out.push(text.slice(last, m.index));
    const t = m[0];
    if (t.startsWith('`')) out.push(h('code', {}, t.slice(1, -1)));
    else if (t.startsWith('**')) out.push(h('strong', {}, t.slice(2, -2)));
    else out.push(h('em', {}, t.slice(1, -1)));
    last = m.index + t.length;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}

export function renderMarkdown(md) {
  const blocks = [];
  const lines = md.replace(/\r/g, '').split('\n');
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    if (line.startsWith('```')) {
      const code = [];
      for (i++; i < lines.length && !lines[i].startsWith('```'); i++) code.push(lines[i]);
      blocks.push(h('pre', { class: 'code' }, code.join('\n')));
      i++;
    } else if (/^#{1,3} /.test(line)) {
      const level = line.match(/^#+/)[0].length;
      blocks.push(h(`h${level}`, {}, inline(line.replace(/^#+ /, ''))));
      i++;
    } else if (/^- /.test(line)) {
      const items = [];
      while (i < lines.length && (/^- /.test(lines[i]) || /^ {2}\S/.test(lines[i]))) {
        if (/^- /.test(lines[i])) items.push(lines[i].slice(2)); else items[items.length - 1] += ` ${lines[i].trim()}`;
        i++;
      }
      blocks.push(h('ul', {}, items.map((t) => h('li', {}, inline(t)))));
    } else if (line.trim() === '') {
      i++;
    } else {
      const para = [];
      while (i < lines.length && lines[i].trim() !== '' && !/^(#|- |```)/.test(lines[i])) para.push(lines[i++].trim());
      blocks.push(h('p', {}, inline(para.join(' '))));
    }
  }
  return blocks;
}

export async function helpView(page) {
  const res = await fetch(`/static/help/${page}.md`, { cache: 'no-cache' });
  if (!res.ok) throw new Error('Help page not found');
  mount(h('div', { class: 'card stack help' }, renderMarkdown(await res.text()),
    h('div', { class: 'row' }, h('a', { class: 'btn', href: '#/settings' }, 'Settings'), h('button', { class: 'btn ghost', onclick: () => history.back() }, '← Back'))));
  return {};
}
