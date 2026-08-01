marked.setOptions({ breaks: true, gfm: true });

const ICONS = {
  copy: '<svg viewBox="0 0 24 24"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>',
  regen: '<svg viewBox="0 0 24 24"><path d="M3 12a9 9 0 0 1 15-6.7L21 8"/><path d="M21 12a9 9 0 0 1-15 6.7L3 16"/></svg>',
};

const S = {
  ws: null, connected: false, streaming: false, retries: 0, maxRetries: 10,
  streamEl: null, raw: '', msgHistory: [],
  aid: null, ascroll: true, convs: [],
  themeData: THEME_DATA, activeTheme: ACTIVE_THEME, layout: LAYOUT,
  providerLabel: '',
};

function esc(t) { const d = document.createElement('div'); d.textContent = String(t); return d.innerHTML; }

function renderMarkdown(t) {
  if (typeof marked === 'undefined' || typeof DOMPurify === 'undefined') return esc(t);
  return DOMPurify.sanitize(marked.parse(t || ''), {
    ALLOWED_TAGS: ['p','br','strong','em','code','pre','ul','ol','li','blockquote','a','table','thead','tbody','tr','th','td','h1','h2','h3','h4','h5','h6','hr','del','ins','sub','sup','span','img'],
    ALLOWED_ATTR: ['href','src','alt','title','class']
  });
}

const $ = id => document.getElementById(id);
const now = () => new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
const addEl = h => { const t = document.createElement('template'); t.innerHTML = h.trim(); $('messageList').appendChild(t.content); };

function relTime(ts) {
  const diff = Date.now() - (ts || Date.now());
  const m = Math.floor(diff / 60000);
  if (m < 1) return 'now';
  if (m < 60) return m + 'm';
  const h = Math.floor(m / 60);
  if (h < 24) return h + 'h';
  const d = Math.floor(h / 24);
  if (d < 7) return d + 'd';
  return new Date(ts).toLocaleDateString([], { month: 'short', day: 'numeric' });
}

function scr() { const c = $('messages'); if (c) { c.scrollTop = c.scrollHeight; S.ascroll = true; } updateScrollBtn(); }

function updateScrollBtn() {
  const c = $('messages'), btn = $('scrollBtn');
  if (!c || !btn) return;
  const atBottom = c.scrollHeight - c.scrollTop - c.clientHeight < 80;
  S.ascroll = atBottom;
  btn.hidden = atBottom || !S.msgHistory.length;
}

function showToast(msg, type) {
  const box = $('toastContainer');
  if (!box) return;
  const el = document.createElement('div');
  el.className = 'toast' + (type === 'error' ? ' error' : '');
  el.textContent = msg;
  box.appendChild(el);
  setTimeout(() => el.remove(), 3500);
}

function thinkingHtml() {
  return '<div class="thinking"><span class="thinking-label">Thinking</span>' +
    '<span class="thinking-dots"><span></span><span></span><span></span></span></div>';
}

function msgActionsHtml(includeRegen) {
  const regen = includeRegen
    ? `<button class="btn-msg-action btn-regen" onclick="regenerate()" title="Regenerate" aria-label="Regenerate">${ICONS.regen}</button>`
    : '';
  return `<div class="msg-actions">` +
    `<button class="btn-msg-action" onclick="copyMsg(this)" title="Copy" aria-label="Copy">${ICONS.copy}</button>` +
    regen + '</div>';
}

function connect(manual) {
  if (S.ws && (S.ws.readyState === 0 || S.ws.readyState === 1)) return;
  if (manual) { S.retries = 0; if (S._rt) { clearTimeout(S._rt); S._rt = null; } }
  try { S.ws = new WebSocket(WS_URL); } catch (_) { S.connected = false; setStatus(false); return; }
  S.ws.onopen = () => {
    S.connected = true; S.retries = 0; setStatus(true);
    if (S.msgHistory.length) syncHistory(S.msgHistory);
    updateComposerState();
  };
  S.ws.onmessage = e => { try { handle(JSON.parse(e.data)); } catch (_) {} };
  S.ws.onclose = () => {
    S.connected = false;
    if (S.retries < S.maxRetries) {
      S.retries++; setStatus(false);
      S._rt = setTimeout(connect, Math.min(1000 * Math.pow(1.5, S.retries), 15000));
    } else { setStatus(false); }
    updateComposerState();
  };
  S.ws.onerror = () => { S.connected = false; setStatus(false); updateComposerState(); };
}

function ws(o) { return S.ws && S.ws.readyState === 1 ? (S.ws.send(JSON.stringify(o)), true) : false; }

function setStatus(ok) {
  const badge = $('statusBadge'), banner = $('connBanner'), dot = $('statusDot');
  if (!badge) return;
  if (ok) {
    badge.textContent = S.providerLabel || 'Ready';
    if (dot) { dot.classList.add('online'); dot.classList.remove('offline'); }
    if (banner) banner.classList.remove('show');
    return;
  }
  badge.textContent = S.retries >= S.maxRetries ? 'Offline' : 'Reconnecting…';
  if (dot) { dot.classList.remove('online'); dot.classList.add('offline'); }
  if (banner) banner.classList.add('show');
}

function syncHistory(msgs) {
  const list = (msgs || []).filter(m => m && m.role && m.content).map(m => ({ role: m.role, content: m.content }));
  if (!list.length) { ws({ action: 'clear' }); return; }
  ws({ action: 'set_history', messages: list });
}

function handle(d) {
  switch (d.type) {
    case 'config':
      S.providerLabel = d.label || '';
      setStatus(true);
      break;
    case 'start': S.raw = ''; showThinking(); S.streaming = true; setInput(false); break;
    case 'token':
      hideThinking(); S.raw += d.content; renderStream(S.raw);
      if (S.ascroll) scr(); else updateScrollBtn();
      break;
    case 'end':
      hideThinking();
      finalizeMsg(S.raw);
      S.streaming = false; S.streamEl = null; S.raw = '';
      setInput(true); saveConv(); if (S.ascroll) scr(); else updateScrollBtn(); focusInput();
      break;
    case 'stopped':
      hideThinking();
      if (S.raw) finalizeMsg(S.raw);
      else if (S.streamEl) { const el = S.streamEl.closest('.msg'); if (el) el.remove(); }
      S.streaming = false; S.streamEl = null; S.raw = '';
      setInput(true); focusInput();
      break;
    case 'error':
      if (S.streamEl) {
        S.streamEl.innerHTML = `<span style="color:var(--error)">${esc(d.content)}</span>`;
      } else {
        showError(d.content);
      }
      showToast(d.content, 'error');
      S.streaming = false; S.streamEl = null; S.raw = '';
      setInput(true); focusInput();
      break;
  }
}

function appendUser(text) {
  addEl(`<div class="msg user"><div class="av user">U</div><div class="bub"><div class="bub-text"><div class="prose">${esc(text)}</div></div><div class="msg-meta"><span class="msg-time">${now()}</span></div></div></div>`);
  return $('messageList').lastElementChild;
}

function showThinking() {
  const id = 't' + Date.now();
  addEl(`<div class="msg ai" id="${id}"><div class="av ai">◆</div><div class="bub"><div class="bub-text">${thinkingHtml()}</div></div></div>`);
  S.streamEl = null;
  if (S.ascroll) scr();
}

function hideThinking() {
  const el = $('messageList').lastElementChild;
  if (!el || !el.id || !el.id.startsWith('t')) return;
  const bub = el.querySelector('.bub-text');
  if (!bub) return;
  bub.innerHTML = '<div class="prose"></div>';
  bub.closest('.bub').insertAdjacentHTML('beforeend',
    `<div class="msg-meta"><span class="msg-time">${now()}</span></div>` +
    msgActionsHtml(false)
  );
  S.streamEl = bub.querySelector('.prose');
  el.id = '';
}

function renderStream(text) {
  if (!S.streamEl) return;
  S.streamEl.innerHTML = renderMarkdown(text) + '<span class="streaming-cursor"></span>';
  S.streamEl.querySelectorAll('pre code').forEach(b => { hljs.highlightElement(b); addCodeHeader(b); });
}

function finalizeMsg(text) {
  if (!S.streamEl || !text) return;
  S.streamEl.innerHTML = renderMarkdown(text);
  S.streamEl.querySelectorAll('pre code').forEach(b => { hljs.highlightElement(b); addCodeHeader(b); });
  S.msgHistory.push({ role: 'assistant', content: text });
  const last = $('messageList').lastElementChild;
  if (last) {
    const actions = last.querySelector('.msg-actions');
    if (actions) {
      actions.insertAdjacentHTML('beforeend',
        `<button class="btn-msg-action btn-regen" onclick="regenerate()" title="Regenerate" aria-label="Regenerate">${ICONS.regen}</button>`
      );
    }
    last.querySelectorAll('.prose a').forEach(a => { a.target = '_blank'; a.rel = 'noopener'; });
  }
}

function showError(text) {
  addEl(`<div class="msg ai"><div class="av ai">◆</div><div class="bub"><div class="bub-text bub-error"><div class="prose">${esc(text)}</div></div></div></div>`);
  if (S.ascroll) scr(); else updateScrollBtn();
}

function addCodeHeader(b) {
  const pre = b.parentElement;
  if (pre.querySelector('.code-header')) return;
  const lang = (b.className.match(/language-(\w+)/) || [])[1] || 'code';
  const h = document.createElement('div');
  h.className = 'code-header';
  h.innerHTML = `<span>${lang}</span><button class="btn-copy-code" onclick="copyCode(this)">Copy</button>`;
  pre.insertBefore(h, b);
}

function copyCode(btn) {
  const code = btn.closest('pre').querySelector('code');
  if (!code) return;
  navigator.clipboard.writeText(code.textContent).then(() => {
    btn.textContent = 'Copied!';
    showToast('Code copied');
    setTimeout(() => btn.textContent = 'Copy', 1500);
  }).catch(() => {});
}

function copyMsg(btn) {
  const prose = btn.closest('.msg').querySelector('.prose');
  if (!prose) return;
  const text = prose.innerText;
  navigator.clipboard.writeText(text).then(() => {
    showToast('Copied to clipboard');
  }).catch(() => {});
}

function regenerate() {
  if (S.streaming) return;
  const list = $('messageList');
  let el = list.lastElementChild;
  while (el) {
    const prev = el.previousElementSibling;
    if (el.classList.contains('msg') && el.classList.contains('user')) break;
    el.remove();
    el = prev;
  }
  if (S.msgHistory.length && S.msgHistory[S.msgHistory.length - 1].role === 'assistant') S.msgHistory.pop();
  syncHistory(S.msgHistory);
  ws({ action: 'regenerate' });
}

function sendMsg() {
  const input = $('input');
  const text = input.value.trim();
  if (!text || S.streaming) return;
  if (!S.connected) {
    showToast("You're offline. Reconnect and try again.", 'error');
    return;
  }
  showWelcome(false);
  const userEl = appendUser(text);
  S.msgHistory.push({ role: 'user', content: text });
  input.value = ''; input.style.height = 'auto';
  updateComposerState();
  const sent = ws({ action: 'chat', message: text });
  if (!sent) {
    if (userEl) userEl.remove();
    S.msgHistory.pop();
    input.value = text;
    updateComposerState();
    showToast('Message could not be sent. Please try again.', 'error');
    focusInput();
    return;
  }
  updateScrollBtn();
}

function chipClick(text) {
  $('input').value = text;
  updateComposerState();
  sendMsg();
}

function updateComposerState() {
  const input = $('input'), sendBtn = $('sendBtn');
  if (!input || !sendBtn) return;
  const hasText = input.value.trim().length > 0;
  const canSend = !S.streaming && S.connected && hasText;
  sendBtn.disabled = !canSend;
  sendBtn.classList.toggle('ready', canSend);
}

function setInput(enabled) {
  $('input').disabled = !enabled;
  $('stopBtn').classList.toggle('visible', !enabled);
  updateComposerState();
}

function focusInput() { const i = $('input'); if (i && !i.disabled) i.focus(); }

function showWelcome(show) {
  $('welcome').style.display = show ? 'flex' : 'none';
}

function loadConvsFromStorage() {
  try {
    const raw = localStorage.getItem('convs');
    S.convs = raw ? JSON.parse(raw) : [];
    if (!Array.isArray(S.convs)) S.convs = [];
  } catch (_) { S.convs = []; }
}

function saveConv() {
  if (!S.msgHistory.length) return;
  const id = S.aid || String(Date.now()); S.aid = id;
  const first = S.msgHistory.find(m => m.role === 'user');
  const title = ((first && first.content) || 'New chat').slice(0, 50);
  const idx = S.convs.findIndex(c => c.id === id);
  const cv = { id, title, updatedAt: Date.now() };
  if (idx >= 0) S.convs[idx] = cv; else S.convs.unshift(cv);
  if (S.convs.length > 50) { S.convs.slice(50).forEach(o => localStorage.removeItem('msgs_' + o.id)); S.convs = S.convs.slice(0, 50); }
  try {
    localStorage.setItem('convs', JSON.stringify(S.convs));
    localStorage.setItem('msgs_' + id, JSON.stringify(S.msgHistory));
  } catch (_) {}
  renderConvs();
  renderTabs();
}

function renderConvs() {
  const el = $('convList');
  if (!S.convs.length) {
    el.innerHTML = '<div class="conv-empty">Start a conversation — it will appear here.</div>';
    return;
  }
  el.innerHTML = S.convs.map(c =>
    `<div class="conv-item${c.id === S.aid ? ' active' : ''}" onclick="loadConv('${c.id}')">` +
    `<span class="conv-item-title">${esc(c.title)}</span>` +
    `<span class="conv-item-time">${relTime(c.updatedAt)}</span>` +
    `<button class="conv-item-delete" onclick="deleteConv('${c.id}', event)" aria-label="Delete chat">&times;</button>` +
    `</div>`
  ).join('');
}

function loadConv(id) {
  if (S.streaming) return;
  let msgs = [];
  try { msgs = JSON.parse(localStorage.getItem('msgs_' + id) || '[]'); } catch (_) {}
  S.aid = id;
  S.msgHistory = Array.isArray(msgs) ? msgs : [];
  showWelcome(!S.msgHistory.length);
  renderHistory(S.msgHistory);
  syncHistory(S.msgHistory);
  renderConvs();
  renderTabs();
  scr();
  closeSidebar();
}

function renderHistory(msgs) {
  $('messageList').innerHTML = '';
  const list = msgs || [];
  list.forEach((m, i) => {
    if (m.role === 'user') appendUser(m.content || '');
    else if (m.role === 'assistant') {
      const isLast = i === list.length - 1;
      const id = 'h' + Math.random().toString(36).slice(2, 9);
      addEl(`<div class="msg ai" id="${id}"><div class="av ai">◆</div><div class="bub"><div class="bub-text"><div class="prose"></div></div><div class="msg-meta"><span class="msg-time"></span></div>${msgActionsHtml(isLast)}</div></div>`);
      const prose = $(id).querySelector('.prose');
      prose.innerHTML = renderMarkdown(m.content || '');
      prose.querySelectorAll('pre code').forEach(b => { hljs.highlightElement(b); addCodeHeader(b); });
      prose.querySelectorAll('a').forEach(a => { a.target = '_blank'; a.rel = 'noopener'; });
    }
  });
  updateScrollBtn();
}

function newChat() {
  if (S.streaming) stopGen();
  S.aid = null; S.msgHistory = [];
  $('messageList').innerHTML = '';
  showWelcome(true);
  syncHistory([]);
  renderConvs();
  renderTabs();
  updateScrollBtn();
  focusInput();
  closeSidebar();
}

function deleteConv(id, e) {
  if (e) e.stopPropagation();
  S.convs = S.convs.filter(c => c.id !== id);
  try {
    localStorage.setItem('convs', JSON.stringify(S.convs));
    localStorage.removeItem('msgs_' + id);
  } catch (_) {}
  if (S.aid === id) newChat();
  else { renderConvs(); renderTabs(); }
}

function renderTabs() {
  if (S.layout !== 'tabs') return;
  const list = $('tabList');
  if (!list) return;
  const items = S.convs.slice(0, 8).map(c => {
    const active = c.id === S.aid;
    return `<div class="tab-item${active ? ' active' : ''}" onclick="loadConv('${c.id}')">` +
      `<span class="tab-item-title">${esc(c.title)}</span>` +
      `<button class="tab-close" onclick="deleteConv('${c.id}', event)">&times;</button></div>`;
  });
  if (!S.aid && !S.msgHistory.length) {
    items.unshift('<div class="tab-item active"><span class="tab-item-title">New chat</span></div>');
  }
  list.innerHTML = items.join('');
}

function applyTheme(name) {
  const theme = S.themeData[name];
  if (!theme) return;
  Object.entries(theme).forEach(([k, v]) => { if (k !== 'mode') document.documentElement.style.setProperty(k, v); });
  document.body.classList.toggle('mode-light', theme.mode === 'light');
  document.body.classList.toggle('mode-dark', theme.mode === 'dark');
  $('themeSelect').value = name;
  localStorage.setItem('theme', name);
}

function setFont(type) {
  const f = {
    sans: { sans: '-apple-system, BlinkMacSystemFont, "Segoe UI", Inter, Roboto, "Helvetica Neue", Arial, sans-serif', mono: 'ui-monospace, "SF Mono", "Cascadia Code", "Fira Code", Consolas, "Liberation Mono", monospace' },
    serif: { sans: '"Iowan Old Style", "Palatino Linotype", Georgia, "Times New Roman", serif', mono: 'ui-monospace, "SF Mono", "Cascadia Code", "Fira Code", Consolas, "Liberation Mono", monospace' },
    mono: { sans: 'ui-monospace, "SF Mono", "Cascadia Code", "Fira Code", Consolas, "Liberation Mono", monospace', mono: 'ui-monospace, "SF Mono", "Cascadia Code", "Fira Code", Consolas, "Liberation Mono", monospace' },
  };
  const p = f[type] || f.sans;
  document.documentElement.style.setProperty('--font-sans', p.sans);
  document.documentElement.style.setProperty('--font-mono', p.mono);
  document.querySelectorAll('.font-opt').forEach(b => { b.classList.toggle('active', b.dataset.font === type); });
  localStorage.setItem('font', type);
}

function stopGen() { ws({ action: 'stop' }); }

function toggleSidebar(force) {
  const s = $('sidebar');
  const open = typeof force === 'boolean' ? force : !s.classList.contains('open');
  s.classList.toggle('open', open);
}

function closeSidebar() {
  if (window.innerWidth <= 768 || S.layout === 'tabs') toggleSidebar(false);
}

function openSettings() {
  $('settingsOverlay').hidden = false;
  $('settingsPanel').hidden = false;
}

function closeSettings() {
  $('settingsOverlay').hidden = true;
  $('settingsPanel').hidden = true;
}

function init() {
  loadConvsFromStorage();
  connect();
  renderConvs();
  renderTabs();
  showWelcome(true);

  $('themeSelect').innerHTML = Object.keys(S.themeData).map(n =>
    `<option value="${n}"${n === S.activeTheme ? ' selected' : ''}>${n.charAt(0).toUpperCase() + n.slice(1)}</option>`
  ).join('');
  const savedTheme = localStorage.getItem('theme');
  applyTheme(savedTheme && S.themeData[savedTheme] ? savedTheme : S.activeTheme);

  const savedFont = localStorage.getItem('font');
  if (savedFont) setFont(savedFont);

  $('sendBtn').addEventListener('click', sendMsg);
  $('stopBtn').addEventListener('click', stopGen);
  $('newBtn').addEventListener('click', newChat);
  $('settingsBtn').addEventListener('click', openSettings);
  $('settingsClose').addEventListener('click', closeSettings);
  $('settingsOverlay').addEventListener('click', closeSettings);
  $('menuBtn').addEventListener('click', () => toggleSidebar());
  $('tabNewBtn').addEventListener('click', newChat);
  $('tabMenuBtn').addEventListener('click', () => toggleSidebar());
  $('themeSelect').addEventListener('change', e => applyTheme(e.target.value));
  document.querySelectorAll('.font-opt').forEach(b => b.addEventListener('click', () => setFont(b.dataset.font)));

  const connRetry = $('connRetry');
  if (connRetry) connRetry.addEventListener('click', () => connect(true));

  const scrollBtn = $('scrollBtn');
  if (scrollBtn) scrollBtn.addEventListener('click', scr);

  const input = $('input');
  input.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMsg(); }
    if (e.key === 'Escape' && S.streaming) { e.preventDefault(); stopGen(); }
  });
  input.addEventListener('input', () => {
    input.style.height = 'auto';
    input.style.height = Math.min(input.scrollHeight, 150) + 'px';
    updateComposerState();
  });

  const chipsData = CHIPS_DATA;
  const chipsRow = $('chipsRow');
  if (chipsRow && chipsData && chipsData.length) {
    chipsRow.innerHTML = chipsData.map(c =>
      `<button class="chip" onclick="chipClick(${JSON.stringify(c)})">${esc(c)}</button>`
    ).join('');
  }

  $('messages').addEventListener('scroll', updateScrollBtn);

  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') {
      if (!$('settingsPanel').hidden) { closeSettings(); return; }
      if (window.innerWidth <= 768 || S.layout === 'tabs') { closeSidebar(); return; }
    }
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') { e.preventDefault(); toggleSidebar(); }
    if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'O') { e.preventDefault(); newChat(); }
  });

  if (SUBTITLE_TEXT) $('welcomeSub').textContent = SUBTITLE_TEXT;
  updateComposerState();
  focusInput();
}

document.addEventListener('DOMContentLoaded', init);
