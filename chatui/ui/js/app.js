/* ════════════════════════════════════════════════════════════════════════════
   ChatUI — app.js
   Core application: WebSocket, message handler, rendering, input, conversations,
   themes, settings, export/import, mobile sidebar, init.
   Depends on: esc(), renderMarkdown() from markdown.js
               renderWidgetGroup(), showToast() from widgets.js
   ════════════════════════════════════════════════════════════════════════════ */

marked.setOptions({ breaks: true, gfm: true });

const now = () => new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
const scr = () => { const c = document.getElementById('mwrap'); c.scrollTop = c.scrollHeight; };
const mlist = () => document.getElementById('mlist');
const addEl = h => {
  const t = document.createElement('template');
  t.innerHTML = h.trim();
  mlist().appendChild(t.content);
};

/* ── State ─────────────────────────────────────────────────── */
const S = {
  ws: null, connected: false, streaming: false, retries: 0,
  streamEl: null, raw: '', thinkId: null, tbEl: null,
  currentAiMsg: null,
  convs: (() => { try { return JSON.parse(localStorage.getItem('cui3') || '[]'); } catch (_) { return []; } })(),
  msgHistory: [],
  aid: null, ascroll: true,
  session: {},
};

/* ── WebSocket ─────────────────────────────────────────────── */
function connect() {
  if (S.ws && (S.ws.readyState === 0 || S.ws.readyState === 1)) return;
  S.ws = new WebSocket(WS_URL);
  S.ws.onopen = () => { S.connected = true; S.retries = 0; setStatus(true); };
  S.ws.onmessage = e => { try { handle(JSON.parse(e.data)); } catch(err) { console.error('Parse error:', err); } };
  S.ws.onclose = (ev) => {
    S.connected = false;
    setStatus(false);
    if (ev && ev.code === 4001) {
      document.getElementById('st').textContent = 'Unauthorized';
      return;
    }
    if (S.retries < 10) {
      S.retries++;
      setTimeout(connect, Math.min(1000 * Math.pow(1.5, S.retries), 15000));
    }
  };
  S.ws.onerror = () => { S.connected = false; setStatus(false); };
}

function ws(o) { if (S.ws && S.ws.readyState === 1) S.ws.send(JSON.stringify(o)); }

function setStatus(on) {
  const badge = document.getElementById('modelBadge');
  const banner = document.getElementById('connBanner');
  badge.classList.toggle('off', !on);
  document.getElementById('st').textContent = on ? 'Connected' : 'Reconnecting...';
  banner.classList.toggle('show', !on);
}

/* ── Message handler ───────────────────────────────────────── */
function handle(d) {
  switch (d.type) {
    case 'config':
      document.getElementById('st').textContent = `${d.provider} \u00b7 ${d.model}`;
      if (d.session) S.session._id = d.session;
      if (d.lite) { document.body.classList.add('lite-mode'); }
      break;
    case 'session_state':
    case 'session_updated':
      S.session = { ...S.session, ...(d.data || {}) };
      if (d.key) S.session[d.key] = d.value;
      break;
    case 'start':
    case 'start_again':
      if (d.type === 'start') S.raw = '';
      showThink(); S.streaming = true; setInput(false);
      break;
    case 'token':
      rmThink(); S.raw += d.content; renderStream(S.raw);
      if (S.ascroll) scr();
      break;
    case 'tool_call':
      rmThink(); showToolCard(d.id, d.name, d.inputs);
      break;
    case 'tool_result':
      updateToolCard(d.id, d.result, d.name);
      break;
    case 'widgets':
      if (d.widgets) renderWidgetGroup(d.widgets);
      break;
    case 'end':
      finalise(S.raw, d.usage);
      S.streaming = false; S.streamEl = null; S.raw = ''; S.tbEl = null;
      setInput(true); focusI(); saveConv();
      break;
    case 'stopped':
      rmThink(); finalise(S.raw, null);
      S.streaming = false; S.streamEl = null; S.raw = ''; S.tbEl = null;
      S.currentAiMsg = null;
      setInput(true); focusI();
      break;
    case 'error':
      if (S.thinkId) {
        const el = document.getElementById(S.thinkId);
        if (el) {
          const b = el.querySelector('.bub');
          b.style.cssText += ';background:color-mix(in oklch, var(--error) 8%, var(--bg-surface));border-color:color-mix(in oklch, var(--error) 30%, var(--border));';
          b.innerHTML = `<div class="prose" style="color:var(--error)" role="alert">\u26a0\ufe0f ${esc(d.content)}</div>`;
        }
        S.thinkId = null;
      } else if (S.streamEl) {
        S.streamEl.innerHTML = `<span style="color:var(--error)" role="alert">\u26a0\ufe0f ${esc(d.content)}</span>`;
        S.streamEl = null;
      } else {
        showErr(d.content);
      }
      S.currentAiMsg = null;
      S.streaming = false; setInput(true);
      break;
    case 'cleared':
    case 'system_updated':
      S.msgHistory = [];
      break;
    case 'tools_ready':
      showToolsPanel(d.tools);
      break;
    case 'components_ready':
      showComponentsPanel(d.components);
      break;
    case 'component':
      rmThink();
      if (S.streamEl) {
        const msgEl = S.streamEl.closest('.msg.ai');
        if (msgEl) msgEl.remove();
        S.streamEl = null; S.currentAiMsg = null;
      }
      showComponent(d.name, d.html);
      break;
  }
}

/* ── Message rendering ─────────────────────────────────────── */
function appendUser(t) {
  addEl(`<div class="msg user"><div class="av user" aria-label="You"><span aria-hidden="true">You</span></div><div class="mb"><div class="bub"><div class="prose">${esc(t)}</div></div><div class="mmeta"><span class="mt">${now()}</span></div></div></div>`);
  if (S.ascroll) scr();
}

function showThink() {
  const id = 'tk' + Date.now(); S.thinkId = id;
  addEl(`<div class="msg ai" id="${id}"><div class="av ai" aria-label="AI"><span aria-hidden="true">\u25c6</span></div><div class="mb"><div class="bub bub-ghost"><div class="think" aria-label="Thinking"><span class="think-pulse"></span><span class="think-label">Thinking</span></div></div></div></div>`);
  if (S.ascroll) scr();
}

function rmThink() {
  if (!S.thinkId) return;
  const el = document.getElementById(S.thinkId);
  if (!el) return;
  const tid = S.thinkId;
  const b = el.querySelector('.bub');
  b.innerHTML = '<div class="prose"></div>';
  S.streamEl = b.querySelector('.prose');
  S.currentAiMsg = el;
  el.querySelector('.mb').insertAdjacentHTML('beforeend', `
    <div class="mmeta"><span class="mt">${now()}</span><span class="tbadge" id="tb${tid}"></span></div>
    <div class="msg-actions" id="ma${tid}">
      <button class="ma-btn" onclick="copyMsg('${tid}')" aria-label="Copy message">Copy</button>
    </div>
  `);
  const bub = el.querySelector('.bub');
  if (bub) bub.classList.remove('bub-ghost');
  S.tbEl = document.getElementById('tb' + tid);
  S.thinkId = null;
}

function renderStream(r) {
  if (!S.streamEl) return;
  S.streamEl.innerHTML = renderMarkdown(r) + '<span class="scur" aria-hidden="true"></span>';
  S.streamEl.querySelectorAll('pre code').forEach(b => { hljs.highlightElement(b); addCodeHeader(b); });
}

function finalise(r, usage) {
  if (S.streamEl && r) {
    S.streamEl.innerHTML = renderMarkdown(r);
    S.streamEl.querySelectorAll('pre code').forEach(b => { hljs.highlightElement(b); addCodeHeader(b); });
    S.msgHistory.push({ role: 'assistant', content: r });
  }
  if (usage && S.tbEl) S.tbEl.textContent = `${usage.input + usage.output} tok`;
  document.querySelectorAll('.ma-btn.regen').forEach(b => b.remove());
  if (S.currentAiMsg) {
    const actions = S.currentAiMsg.querySelector('.msg-actions');
    if (actions) {
      actions.insertAdjacentHTML('beforeend', `<button class="ma-btn regen" onclick="regenerate()" aria-label="Regenerate response">Regenerate</button>`);
    }
    S.currentAiMsg.querySelectorAll('.prose a').forEach(a => { a.setAttribute('target', '_blank'); a.setAttribute('rel', 'noopener noreferrer'); });
    S.currentAiMsg = null;
  }
}

function showErr(t) {
  addEl(`<div class="msg ai"><div class="av ai" aria-label="AI"><span aria-hidden="true">\u25c6</span></div><div class="mb"><div class="bub bub-error"><div class="prose" role="alert">${esc(t)}</div></div></div></div>`);
  if (S.ascroll) scr();
}

/* ── Tool cards ────────────────────────────────────────────── */
function showToolCard(id, name, inputs) {
  const args = Object.entries(inputs || {}).map(([k, v]) =>
    `<div class="tar"><span class="tak">${esc(k)}</span><span class="tav">${esc(JSON.stringify(v))}</span></div>`
  ).join('');
  addEl(`<div class="tc" id="tc${id}"><div class="tch"><span class="tfn">${esc(name)}</span><span class="tbg run" id="tbg${id}">Running</span></div><div class="tcb" id="tcb${id}">${args || '<div class="tar muted">No arguments</div>'}</div></div>`);
  if (S.ascroll) scr();
}

function updateToolCard(id, res, name) {
  const bg = document.getElementById('tbg' + id);
  if (bg) { bg.textContent = 'Done'; bg.classList.remove('run'); bg.classList.add('done'); }
  const cb = document.getElementById('tcb' + id);
  if (!cb) return;
  let disp = res;
  try { const p = JSON.parse(res); disp = JSON.stringify(p, null, 0); if (disp.length > 200) disp = disp.slice(0, 200) + '\u2026'; } catch (_) {}
  cb.insertAdjacentHTML('beforeend', `<div class="tdiv"></div><div class="trr"><span class="tra">result</span><span class="trv">${esc(disp)}</span></div>`);
  if (S.ascroll) scr();
}

/* ── Components ─────────────────────────────────────────────── */
function showComponent(name, html) {
  const wrapper = document.createElement('div');
  wrapper.className = 'comp-card';
  const bodyId = 'cb-' + Date.now();
  wrapper.innerHTML = `<div class="comp-head"><span class="comp-name">${esc(name)}</span><span class="comp-badge">Component</span></div><div class="comp-body" id="${bodyId}"></div>`;
  mlist().appendChild(wrapper);
  const body = document.getElementById(bodyId);
  try { body.appendChild(document.createRange().createContextualFragment(html)); } catch (_) { body.innerHTML = html; }
  if (S.ascroll) scr();
}

function showToolsPanel(tools) {
  if (!tools || !tools.length) return;
  document.getElementById('sbTools').style.display = 'block';
  document.getElementById('toolsCount').textContent = tools.length;
  document.getElementById('toolsList').innerHTML = tools.map(t =>
    `<div class="tool-item"><div class="tool-item-dot" aria-hidden="true"></div><div><div class="tool-item-name">${esc(t.name)}</div>${t.description ? `<div class="tool-item-desc">${esc(t.description.slice(0, 70))}${t.description.length > 70 ? '\u2026' : ''}</div>` : ''}</div></div>`
  ).join('');
}

function showComponentsPanel(components) {
  if (!components || !components.length) return;
  const panel = document.getElementById('sbTools');
  panel.style.display = 'block';
  const div = document.createElement('div');
  div.innerHTML = `<div style="padding:.375rem 1.25rem .1rem;border-top:1px solid var(--border);margin-top:.25rem"><div class="sb-section-label" style="margin-bottom:.25rem">Components</div>` + components.map(c => `<div class="tool-item"><span class="tool-item-icon" style="color:var(--accent)" aria-hidden="true">\u25C8</span><div><div class="tool-item-name" style="color:var(--accent)">${esc(c)}</div></div></div>`).join('') + '</div>';
  panel.appendChild(div);
}

/* ── Toasts ─────────────────────────────────────────────────── */
function showToast(message, icon) {
  const container = document.getElementById('toastContainer');
  const icons = { info: '\u2139\ufe0f', success: '\u2705', warning: '\u26a0\ufe0f', error: '\u274c' };
  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.innerHTML = `<span class="toast-icon ${icon}">${icons[icon] || icons.info}</span><span>${esc(message)}</span>`;
  container.appendChild(toast);
  setTimeout(() => { if (toast.parentNode) toast.remove(); }, 4000);
}

/* ── Message actions ───────────────────────────────────────── */
function copyMsg(tid) {
  const el = document.getElementById(tid);
  if (!el) return;
  const prose = el.querySelector('.prose');
  if (!prose) return;
  navigator.clipboard.writeText(prose.innerText).then(() => {
    const btn = el.querySelector('.ma-btn:first-child');
    if (btn) { btn.textContent = 'Copied'; setTimeout(() => btn.textContent = 'Copy', 1800); }
  }).catch(() => {});
}

function regenerate() {
  if (S.streaming || !S.connected) return;
  const list = mlist();
  let child = list.lastElementChild;
  while (child) {
    const prev = child.previousElementSibling;
    if (child.classList.contains('msg') && child.classList.contains('user')) break;
    child.remove();
    child = prev;
  }
  if (S.msgHistory.length && S.msgHistory[S.msgHistory.length - 1].role === 'assistant') S.msgHistory.pop();
  ws({ action: 'regenerate' });
}

/* ── Input ─────────────────────────────────────────────────── */
function sendMsg() {
  const inp = document.getElementById('ci');
  const t = inp.value.trim();
  if (!t || S.streaming || !S.connected) return;
  if (t.length > 12000) {
    showToast('Message too long (max 12,000 characters)', 'warning');
    return;
  }
  document.getElementById('welcome').style.display = 'none';
  appendUser(t);
  S.msgHistory.push({ role: 'user', content: t });
  inp.value = ''; inp.style.height = 'auto';
  ws({ action: 'chat', message: t });
}

function chip(t) { document.getElementById('ci').value = t; sendMsg(); }

function setInput(on) {
  const i = document.getElementById('ci');
  const b = document.getElementById('sb2');
  const s = document.getElementById('stb');
  i.disabled = !on;
  b.disabled = !on;
  s.classList.toggle('vis', !on);
}

function focusI() { document.getElementById('ci').focus(); }

function stopGen() { ws({ action: 'stop' }); S.streaming = false; setInput(true); }

/* ── Conversations ─────────────────────────────────────────── */
function saveConv() {
  if (!S.msgHistory.length) return;
  const id = S.aid || String(Date.now()); S.aid = id;
  const first = S.msgHistory.find(m => m.role === 'user');
  const title = ((first && first.content) || 'New conversation').slice(0, 50);
  const idx = S.convs.findIndex(c => c.id === id);
  const cv = { id, title, updatedAt: Date.now() };
  if (idx >= 0) S.convs[idx] = cv; else S.convs.unshift(cv);
  if (S.convs.length > 50) {
    S.convs.slice(50).forEach(old => localStorage.removeItem('cui_msgs_' + old.id));
    S.convs = S.convs.slice(0, 50);
  }
  try {
    localStorage.setItem('cui3', JSON.stringify(S.convs));
    localStorage.setItem('cui_msgs_' + id, JSON.stringify(S.msgHistory));
  } catch (_) {}
  renderConvs();
}

function renderConvs() {
  const el = document.getElementById('convList');
  if (!S.convs.length) {
    el.innerHTML = '<div class="sb-empty"><div class="sb-empty-title">No chats yet</div><div class="sb-empty-sub">Start a conversation \u2014 it will show up here so you can return later.</div></div>';
    return;
  }
  el.innerHTML = S.convs.map(c =>
    `<div class="cv${c.id === S.aid ? ' active' : ''}" onclick="loadConv('${c.id}')">${esc(c.title)}<button class="cv-del-btn" onclick="event.stopPropagation();deleteConv('${c.id}')" aria-label="Delete conversation">&times;</button></div>`
  ).join('');
}

function loadConv(id) {
  if (S.streaming) return;
  let msgs = [];
  try { msgs = JSON.parse(localStorage.getItem('cui_msgs_' + id) || '[]'); } catch (_) { msgs = []; }
  S.aid = id;
  S.msgHistory = Array.isArray(msgs) ? msgs : [];
  mlist().innerHTML = '';
  document.getElementById('welcome').style.display = S.msgHistory.length ? 'none' : 'flex';
  S.msgHistory.forEach(m => {
    if (m.role === 'user') appendUser(m.content || '');
    else if (m.role === 'assistant') {
      const tid = 'hist' + Math.random().toString(36).slice(2, 9);
      addEl(`<div class="msg ai" id="${tid}"><div class="av ai" aria-label="AI"><span aria-hidden="true">\u25c6</span></div><div class="mb"><div class="bub"><div class="prose"></div></div><div class="mmeta"><span class="mt"></span></div></div></div>`);
      const prose = document.getElementById(tid).querySelector('.prose');
      prose.innerHTML = renderMarkdown(m.content || '');
      prose.querySelectorAll('pre code').forEach(b => { hljs.highlightElement(b); addCodeHeader(b); });
    }
  });
  ws({ action: 'clear' });
  renderConvs();
  if (S.ascroll) scr();
  focusI();
}

function deleteConv(id) {
  S.convs = S.convs.filter(c => c.id !== id);
  localStorage.setItem('cui3', JSON.stringify(S.convs));
  localStorage.removeItem('cui_msgs_' + id);
  if (S.aid === id) newChat();
  renderConvs();
}

function newChat() {
  if (S.streaming) stopGen();
  S.aid = null; S.msgHistory = [];
  mlist().innerHTML = '';
  document.getElementById('welcome').style.display = 'flex';
  ws({ action: 'clear' }); renderConvs(); focusI();
}

/* ── Themes & settings ─────────────────────────────────────── */
function applyTheme(name) {
  const theme = THEME_DATA[name];
  if (!theme) return;
  const root = document.documentElement;
  Object.entries(theme).forEach(([k, v]) => {
    if (k !== 'mode') root.style.setProperty(k, v);
  });
  document.body.classList.toggle('mode-light', theme.mode === 'light');
  document.body.classList.toggle('mode-dark', theme.mode === 'dark');
  const sel = document.getElementById('themeSelect');
  if (sel) sel.value = name;
  localStorage.setItem('cui_theme', name);
}

function initThemeDots() {
  const sel = document.getElementById('themeSelect');
  if (!sel) return;
  sel.innerHTML = '';
  Object.keys(THEME_DATA).forEach(name => {
    const opt = document.createElement('option');
    opt.value = name;
    opt.textContent = THEME_LABELS[name] || name;
    if (name === ACTIVE_THEME) opt.selected = true;
    sel.appendChild(opt);
  });
  sel.addEventListener('change', () => applyTheme(sel.value));
  const saved = localStorage.getItem('cui_theme');
  if (saved && THEME_DATA[saved]) applyTheme(saved);
  else applyTheme(ACTIVE_THEME);
}

function setFont(type) {
  const FONTS = {
    sans:  { sans: "'Sora', system-ui, sans-serif",           mono: "'JetBrains Mono', monospace" },
    serif: { sans: "'Cormorant Garamond', Georgia, serif",     mono: "'JetBrains Mono', monospace" },
    mono:  { sans: "'JetBrains Mono', monospace",              mono: "'JetBrains Mono', monospace" },
  };
  const picked = FONTS[type] || FONTS.sans;
  document.documentElement.style.setProperty('--font-sans', picked.sans);
  document.documentElement.style.setProperty('--font-mono', picked.mono);
  document.querySelectorAll('.font-opt').forEach(b => {
    const active = b.dataset.font === type;
    b.classList.toggle('active', active);
    b.setAttribute('aria-pressed', String(active));
  });
  localStorage.setItem('cui_font', type);
}

function setSize(size) {
  const SIZES = { sm: '14px', md: '15.5px', lg: '17px' };
  document.documentElement.style.setProperty('--font-size-base', SIZES[size] || '15.5px');
  document.querySelectorAll('.size-opt').forEach(b => {
    const active = b.dataset.size === size;
    b.classList.toggle('active', active);
    b.setAttribute('aria-pressed', String(active));
  });
  localStorage.setItem('cui_size', size);
}

/* ── Init welcome ──────────────────────────────────────────── */
function initWelcome() {
  const sub = document.getElementById('welcomeSub');
  if (sub) {
    const txt = SUBTITLE_TEXT;
    if (txt) sub.textContent = txt;
    else sub.style.display = 'none';
  }
  const chipsData = CHIPS_DATA;
  const row = document.getElementById('chipsRow');
  if (row && chipsData && chipsData.length) {
    row.innerHTML = chipsData.map(c =>
      `<button class="chip" onclick="chip(${JSON.stringify(c)})">${esc(c)}</button>`
    ).join('');
  } else if (row) {
    row.style.display = 'none';
  }
}

/* ── System prompt ─────────────────────────────────────────── */
function toggleSys() {
  const panel = document.getElementById('sysPanel');
  const btn = document.getElementById('sysBtn');
  const open = !panel.classList.contains('open');
  panel.classList.toggle('open', open);
  panel.setAttribute('aria-hidden', String(!open));
  if (btn) {
    btn.setAttribute('aria-expanded', String(open));
    btn.setAttribute('aria-label', open ? 'Close settings' : 'Open settings');
  }
  if (open) {
    const sel = document.getElementById('themeSelect');
    if (sel) sel.focus();
  }
}

function saveSystem() {
  const p = document.getElementById('sysTa').value.trim();
  if (!p) {
    showToast('Enter a system prompt before applying', 'warning');
    return;
  }
  ws({ action: 'update_system', prompt: p });
  const panel = document.getElementById('sysPanel');
  const btn = document.getElementById('sysBtn');
  panel.classList.remove('open');
  panel.setAttribute('aria-hidden', 'true');
  if (btn) {
    btn.setAttribute('aria-expanded', 'false');
    btn.setAttribute('aria-label', 'Open settings');
  }
  showToast('System prompt applied \u2014 starting a fresh chat', 'success');
  newChat();
}

/* ── Export / import ───────────────────────────────────────── */
function exportConv() {
  if (!S.msgHistory.length) return;
  const md = `# ChatUI Export\n${new Date().toLocaleString()}\n\n---\n\n` +
    S.msgHistory.map(m => `## ${m.role === 'user' ? 'You' : 'AI'}\n\n${m.content}`).join('\n\n---\n\n');
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([md], { type: 'text/markdown' }));
  a.download = `chatui-${Date.now()}.md`;
  a.click();
  URL.revokeObjectURL(a.href);
}

function importConv() {
  const input = document.createElement('input');
  input.type = 'file';
  input.accept = '.md,.txt';
  input.onchange = e => {
    const file = e.target.files[0];
    if (!file) return;
    if (file.size > 2 * 1024 * 1024) {
      showToast('Import file too large (max 2 MB)', 'error');
      return;
    }
    const reader = new FileReader();
    reader.onload = ev => {
      const text = String(ev.target.result || '');
      const msgs = parseExportedMarkdown(text);
      if (!msgs.length) {
        showToast('Could not parse conversation from file', 'warning');
        return;
      }
      newChat();
      S.msgHistory = msgs;
      document.getElementById('welcome').style.display = 'none';
      mlist().innerHTML = '';
      msgs.forEach(m => {
        if (m.role === 'user') appendUser(m.content);
        else {
          const tid = 'imp' + Math.random().toString(36).slice(2, 9);
          addEl(`<div class="msg ai" id="${tid}"><div class="av ai" aria-label="AI"><span aria-hidden="true">\u25c6</span></div><div class="mb"><div class="bub"><div class="prose"></div></div></div></div>`);
          const prose = document.getElementById(tid).querySelector('.prose');
          prose.innerHTML = renderMarkdown(m.content || '');
        }
      });
      saveConv();
      showToast('Imported ' + msgs.length + ' messages', 'success');
    };
    reader.readAsText(file);
  };
  input.click();
}

function parseExportedMarkdown(text) {
  const parts = text.split(/\n---\n/).map(s => s.trim()).filter(Boolean);
  const msgs = [];
  for (const part of parts) {
    const m = part.match(/^##\s+(You|AI)\s*\n+([\s\S]*)$/i);
    if (!m) continue;
    msgs.push({
      role: m[1].toLowerCase() === 'you' ? 'user' : 'assistant',
      content: m[2].trim(),
    });
  }
  return msgs;
}

/* ── Mobile sidebar ────────────────────────────────────────── */
function toggleSidebar(force) {
  const sidebar = document.getElementById('sidebar');
  const backdrop = document.getElementById('sbBackdrop');
  const menuBtn = document.getElementById('menuBtn');
  const open = typeof force === 'boolean' ? force : !sidebar.classList.contains('open');
  sidebar.classList.toggle('open', open);
  backdrop.classList.toggle('open', open);
  if (open) backdrop.removeAttribute('hidden');
  else backdrop.setAttribute('hidden', '');
  if (menuBtn) {
    menuBtn.setAttribute('aria-expanded', String(open));
    menuBtn.setAttribute('aria-label', open ? 'Close sidebar menu' : 'Open sidebar menu');
  }
  document.body.classList.toggle('sidebar-open', open);
}

/* ── Init ───────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  connect();
  renderConvs();
  initThemeDots();
  initWelcome();
  const foot = document.getElementById('sbFootText');
  if (foot) foot.textContent = 'ChatUI';

  document.querySelectorAll('.font-opt').forEach(btn =>
    btn.addEventListener('click', () => setFont(btn.dataset.font))
  );
  document.querySelectorAll('.size-opt').forEach(btn =>
    btn.addEventListener('click', () => setSize(btn.dataset.size))
  );

  const savedFont = localStorage.getItem('cui_font');
  const savedSize = localStorage.getItem('cui_size');
  if (savedFont) setFont(savedFont);
  if (savedSize) setSize(savedSize);

  const inp = document.getElementById('ci');
  inp.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMsg(); }
    if (e.key === 'Escape' && S.streaming) { e.preventDefault(); stopGen(); }
  });
  inp.addEventListener('input', e => {
    e.target.style.height = 'auto';
    e.target.style.height = Math.min(e.target.scrollHeight, 160) + 'px';
  });

  document.getElementById('sb2').addEventListener('click', sendMsg);
  document.getElementById('stb').addEventListener('click', stopGen);
  document.getElementById('newBtn').addEventListener('click', newChat);
  document.getElementById('sysBtn').addEventListener('click', toggleSys);
  document.getElementById('sysSave').addEventListener('click', saveSystem);
  document.getElementById('expBtn').addEventListener('click', exportConv);
  document.getElementById('impBtn').addEventListener('click', importConv);
  document.getElementById('menuBtn').addEventListener('click', toggleSidebar);
  document.getElementById('sbBackdrop').addEventListener('click', toggleSidebar);
  document.getElementById('mwrap').addEventListener('scroll', () => {
    const c = document.getElementById('mwrap');
    S.ascroll = (c.scrollHeight - c.scrollTop - c.clientHeight < 80);
  });

  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') {
      const sidebar = document.getElementById('sidebar');
      if (sidebar && sidebar.classList.contains('open')) {
        e.preventDefault();
        toggleSidebar(false);
        return;
      }
      const panel = document.getElementById('sysPanel');
      if (panel && panel.classList.contains('open')) {
        e.preventDefault();
        toggleSys();
        return;
      }
    }
    if (e.ctrlKey || e.metaKey) {
      if (e.key === 'k') { e.preventDefault(); toggleSidebar(); }
      if (e.key === 'n' && !S.streaming) { e.preventDefault(); newChat(); }
    }
  });

  focusI();
});
