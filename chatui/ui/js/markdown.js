/* ════════════════════════════════════════════════════════════════════════════
   ChatUI — markdown.js
   Markdown rendering + code block utilities.
   Depends on: marked (global), DOMPurify (global), hljs (global)
   ════════════════════════════════════════════════════════════════════════════ */

/* ── Utilities shared across all JS modules ─────────────────── */
function esc(t) { const d = document.createElement('div'); d.textContent = String(t); return d.innerHTML; }

function renderMarkdown(t) {
  if (typeof marked === 'undefined' || typeof DOMPurify === 'undefined') return esc(t);
  return DOMPurify.sanitize(marked.parse(t || ''), {
    ALLOWED_TAGS: ['p','br','strong','em','code','pre','ul','ol','li','blockquote','a','table','thead','tbody','tr','th','td','h1','h2','h3','h4','h5','h6','hr','del','ins','sub','sup','span','img'],
    ALLOWED_ATTR: ['href','src','alt','title','class']
  });
}

/* ── Code block headers ─────────────────────────────────────── */
function addCodeHeader(b) {
  const pre = b.parentElement;
  if (pre.querySelector('.chdr')) return;
  const lang = (b.className.match(/language-(\w+)/) || [])[1] || 'code';
  const h = document.createElement('div');
  h.className = 'chdr';
  h.innerHTML = `<span>${lang}</span><button class="cbtn" onclick="copyCode(this)" aria-label="Copy code">Copy</button>`;
  pre.insertBefore(h, b);
}

function copyCode(btn) {
  const code = btn.closest('pre').querySelector('code');
  if (!code) return;
  navigator.clipboard.writeText(code.textContent).then(() => {
    btn.textContent = 'Copied!';
    setTimeout(() => btn.textContent = 'Copy', 1800);
  }).catch(() => {});
}
