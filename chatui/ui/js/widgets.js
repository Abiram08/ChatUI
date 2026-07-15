/* ════════════════════════════════════════════════════════════════════════════
   ChatUI — widgets.js
   Widget rendering pipeline: layout helpers, widget HTML builders, event binding.
   Depends on: esc() from markdown.js, ws() and S from app.js
   ════════════════════════════════════════════════════════════════════════════ */

const FLAT_WIDGETS = new Set(['button', 'divider', 'spinner']);

function renderWidgetGroup(widgets) {
  if (!widgets || !widgets.length) return;
  let i = 0;
  while (i < widgets.length) {
    const w = widgets[i];
    if (w.widget === 'columns') {
      const ratios = w.props.ratios || [1, 1];
      const n = ratios.length;
      const kids = [];
      i++;
      while (i < widgets.length && widgets[i].widget !== 'columns_end' && kids.length < n) {
        if (widgets[i].widget === 'columns' || widgets[i].widget === 'expander') break;
        kids.push(widgets[i]);
        i++;
      }
      if (i < widgets.length && widgets[i].widget === 'columns_end') i++;
      renderColumns(ratios, kids);
      continue;
    }
    if (w.widget === 'expander') {
      const body = [];
      i++;
      while (i < widgets.length && widgets[i].widget !== 'expander_end') {
        body.push(widgets[i]);
        i++;
      }
      if (i < widgets.length && widgets[i].widget === 'expander_end') i++;
      renderExpander(w, body);
      continue;
    }
    if (w.widget === 'columns_end' || w.widget === 'expander_end') {
      i++;
      continue;
    }
    if (w.widget === 'toast') {
      showToast(w.props.message, w.props.icon || 'info');
      i++;
      continue;
    }
    if (w.widget === 'button') {
      const btns = [];
      while (i < widgets.length && widgets[i].widget === 'button') {
        btns.push(widgets[i]);
        i++;
      }
      renderButtonGroup(btns);
      continue;
    }
    if (w.widget === 'metric') {
      const metrics = [];
      while (i < widgets.length && widgets[i].widget === 'metric') {
        metrics.push(widgets[i]);
        i++;
      }
      renderMetricGroup(metrics);
      continue;
    }
    /* Explicit layout containers */
    if (w.widget === 'actions') {
      const card = document.createElement('div');
      card.className = 'widget-card flat';
      const row = document.createElement('div');
      row.className = 'w-actions';
      row.setAttribute('role', 'group');
      row.setAttribute('aria-label', 'Actions');
      (w.props.children || []).forEach(cw => mountWidget(row, cw));
      card.appendChild(row);
      mlist().appendChild(card);
      if (S.ascroll) scr();
      i++;
      continue;
    }
    if (w.widget === 'row') {
      const card = document.createElement('div');
      card.className = 'widget-card';
      const grid = document.createElement('div');
      grid.className = 'w-metrics';
      (w.props.children || []).forEach(cw => {
        const cell = document.createElement('div');
        cell.innerHTML = buildWidgetHTML(cw);
        grid.appendChild(cell);
      });
      card.appendChild(grid);
      mlist().appendChild(card);
      if (S.ascroll) scr();
      i++;
      continue;
    }
    if (w.widget === 'stack') {
      const card = document.createElement('div');
      card.className = 'widget-card';
      (w.props.children || []).forEach(cw => {
        const wrap = document.createElement('div');
        mountWidget(wrap, cw);
        card.appendChild(wrap);
      });
      mlist().appendChild(card);
      if (S.ascroll) scr();
      i++;
      continue;
    }
    if (w.widget === 'card') {
      const card = document.createElement('div');
      card.className = 'widget-card';
      if (w.props.title) {
        const h = document.createElement('div');
        h.className = 'w-card-title';
        h.textContent = w.props.title;
        card.appendChild(h);
      }
      (w.props.children || []).forEach(cw => {
        const wrap = document.createElement('div');
        mountWidget(wrap, cw);
        card.appendChild(wrap);
      });
      mlist().appendChild(card);
      if (S.ascroll) scr();
      i++;
      continue;
    }
    if (w.widget === 'choice') {
      const card = document.createElement('div');
      card.className = 'widget-card flat';
      const wrap = document.createElement('div');
      wrap.className = 'w-choice';
      if (w.props.label) {
        const lbl = document.createElement('div');
        lbl.className = 'w-input-label';
        lbl.textContent = w.props.label;
        wrap.appendChild(lbl);
      }
      const chipsRow = document.createElement('div');
      chipsRow.className = 'w-choice-opts';
      (w.props.options || []).forEach(opt => {
        const btn = document.createElement('button');
        btn.className = 'w-btn secondary';
        btn.textContent = String(opt);
        btn.addEventListener('click', () => {
          ws({ action: 'widget_event', event: 'choice_select', widget_id: w.id, key: w.props.key, value: opt, data: { key: w.props.key, value: opt } });
        });
        chipsRow.appendChild(btn);
      });
      wrap.appendChild(chipsRow);
      card.appendChild(wrap);
      mlist().appendChild(card);
      if (S.ascroll) scr();
      i++;
      continue;
    }
    if (w.widget === 'form') {
      const card = document.createElement('div');
      card.className = 'widget-card';
      const form = document.createElement('div');
      form.className = 'w-form';
      const fieldValues = {};
      (w.props.fields || []).forEach(fw => {
        const fieldWrap = document.createElement('div');
        fieldWrap.innerHTML = buildWidgetHTML(fw);
        const input = fieldWrap.querySelector('[data-widget-key]');
        if (input) {
          input.addEventListener('change', () => { fieldValues[fw.props.key] = input.value; });
          fieldValues[fw.props.key] = input.value || '';
        }
        form.appendChild(fieldWrap.firstChild || fieldWrap);
      });
      const submitBtn = document.createElement('button');
      submitBtn.className = 'w-btn primary';
      submitBtn.textContent = 'Submit';
      submitBtn.addEventListener('click', () => {
        ws({ action: 'widget_event', event: 'form_submit', widget_id: w.id, key: w.props.submit_key, value: fieldValues, data: { key: w.props.submit_key, values: fieldValues } });
      });
      form.appendChild(submitBtn);
      card.appendChild(form);
      mlist().appendChild(card);
      if (S.ascroll) scr();
      i++;
      continue;
    }
    renderWidget(w);
    i++;
  }
}

function mountWidget(parent, w) {
  const wrap = document.createElement('div');
  wrap.innerHTML = buildWidgetHTML(w);
  bindWidgetEvents(wrap, w);
  while (wrap.firstChild) parent.appendChild(wrap.firstChild);
}

function renderButtonGroup(btns) {
  if (!btns.length) return;
  const card = document.createElement('div');
  card.className = 'widget-card flat';
  const row = document.createElement('div');
  row.className = 'w-actions';
  row.setAttribute('role', 'group');
  row.setAttribute('aria-label', 'Actions');
  btns.forEach(w => mountWidget(row, w));
  card.appendChild(row);
  mlist().appendChild(card);
  if (S.ascroll) scr();
}

function renderMetricGroup(metrics) {
  if (!metrics.length) return;
  if (metrics.length === 1) {
    renderWidget(metrics[0]);
    return;
  }
  const card = document.createElement('div');
  card.className = 'widget-card';
  const grid = document.createElement('div');
  grid.className = 'w-metrics';
  metrics.forEach(w => {
    const cell = document.createElement('div');
    cell.innerHTML = buildWidgetHTML(w);
    grid.appendChild(cell);
  });
  card.appendChild(grid);
  mlist().appendChild(card);
  if (S.ascroll) scr();
}

function renderColumns(ratios, kids) {
  const grid = document.createElement('div');
  grid.className = 'widget-card w-columns';
  grid.style.gridTemplateColumns = (ratios || [1, 1]).map(r => `${Number(r) || 1}fr`).join(' ');
  kids.forEach(w => {
    const cell = document.createElement('div');
    if (w.widget === 'button') {
      const row = document.createElement('div');
      row.className = 'w-actions';
      mountWidget(row, w);
      cell.appendChild(row);
    } else {
      mountWidget(cell, w);
    }
    grid.appendChild(cell);
  });
  mlist().appendChild(grid);
  if (S.ascroll) scr();
}

function renderExpander(w, kids) {
  const card = document.createElement('div');
  card.className = 'widget-card';
  card.innerHTML = buildWidgetHTML(w);
  const body = card.querySelector('.w-expander-body');
  kids.forEach(child => {
    const wrap = document.createElement('div');
    if (child.widget === 'button') {
      wrap.className = 'w-actions';
    }
    mountWidget(wrap, child);
    if (body) body.appendChild(wrap);
  });
  mlist().appendChild(card);
  if (S.ascroll) scr();
}

function renderWidget(wd) {
  if (!wd || wd.widget === 'toast') {
    if (wd && wd.widget === 'toast') showToast(wd.props.message, wd.props.icon || 'info');
    return;
  }
  const card = document.createElement('div');
  card.className = 'widget-card' + (FLAT_WIDGETS.has(wd.widget) ? ' flat' : '');
  card.dataset.widgetId = wd.id;
  if (wd.widget === 'button') {
    const row = document.createElement('div');
    row.className = 'w-actions';
    mountWidget(row, wd);
    card.appendChild(row);
  } else {
    card.innerHTML = buildWidgetHTML(wd);
    bindWidgetEvents(card, wd);
  }
  mlist().appendChild(card);
  if (S.ascroll) scr();
}

function buildWidgetHTML(w) {
  switch (w.widget) {
    case 'button':
      return `<button class="w-btn ${esc(w.props.variant || 'primary')}" data-widget-action="button_click" data-widget-key="${esc(w.props.key || '')}" ${w.props.disabled ? 'disabled' : ''}>${esc(w.props.label)}</button>`;
    case 'text_input':
      return `<div class="w-input-group"><label class="w-input-label">${esc(w.props.label)}</label><div class="w-input-field"><input type="text" class="w-input" data-widget-key="${esc(w.props.key)}" placeholder="${esc(w.props.placeholder || '')}" value="${esc(w.props.value || '')}" aria-label="${esc(w.props.label)}"><button class="w-input-submit" data-widget-action="text_input_submit" data-widget-key="${esc(w.props.key)}">Send</button></div></div>`;
    case 'selectbox':
      return `<div class="w-select"><label class="w-input-label">${esc(w.props.label)}</label><select data-widget-action="selectbox_change" data-widget-key="${esc(w.props.key)}">${(w.props.options || []).map((o, i) => `<option value="${esc(o)}" ${i === (w.props.index || 0) ? 'selected' : ''}>${esc(o)}</option>`).join('')}</select></div>`;
    case 'radio':
      return `<div class="w-radios"><label class="w-input-label">${esc(w.props.label)}</label>${(w.props.options || []).map((o, i) => `<label class="w-radio-opt"><input type="radio" name="${esc(w.props.key)}" value="${esc(o)}" ${i === (w.props.index || 0) ? 'checked' : ''} data-widget-action="radio_change" data-widget-key="${esc(w.props.key)}">${esc(o)}</label>`).join('')}</div>`;
    case 'checkbox':
      return `<div class="w-checkbox-group"><label class="w-checkbox-opt"><input type="checkbox" data-widget-action="checkbox_change" data-widget-key="${esc(w.props.key)}" ${w.props.value ? 'checked' : ''}>${esc(w.props.label)}</label></div>`;
    case 'slider':
      return `<div class="w-slider-group"><label class="w-input-label">${esc(w.props.label)} <span class="w-slider-val" id="sv_${w.id}" style="margin-left:8px">${w.props.value}</span></label><input type="range" min="${w.props.min}" max="${w.props.max}" step="${w.props.step}" value="${w.props.value}" data-widget-action="slider_change" data-widget-key="${esc(w.props.key)}" oninput="document.getElementById('sv_${w.id}').textContent = this.value"></div>`;
    case 'progress':
      const pct = Math.round((w.props.value || 0) * 100);
      return `<div class="w-progress">${w.props.label ? '<div class="w-progress-label"><span>' + esc(w.props.label) + '</span><span>' + pct + '%</span></div>' : ''}<div class="w-progress-bar"><div class="w-progress-fill" style="width:${pct}%"></div></div></div>`;
    case 'status':
      return `<div class="w-status ${w.props.expanded ? 'open' : ''}" data-widget-id="${w.id}"><button type="button" class="w-status-head" aria-expanded="${w.props.expanded ? 'true' : 'false'}" onclick="const p=this.parentElement;const o=!p.classList.contains('open');p.classList.toggle('open',o);this.setAttribute('aria-expanded',String(o))"><span class="w-status-dot ${esc(w.props.state)}" aria-hidden="true"></span><span>${esc(w.props.label)}</span><span class="w-status-state">${esc(w.props.state)}</span></button><div class="w-status-body"></div></div>`;
    case 'table':
      const cols = (w.props.columns || []).map(c => `<th>${esc(c)}</th>`).join('');
      const rows = (w.props.rows || []).map(r => `<tr>${r.map(c => `<td>${esc(String(c))}</td>`).join('')}</tr>`).join('');
      return `<div class="w-table-wrapper">${w.props.caption ? `<div class="w-table-caption">${esc(w.props.caption)}</div>` : ''}<table class="w-table"><thead><tr>${cols}</tr></thead><tbody>${rows}</tbody></table></div>`;
    case 'markdown':
      return `<div class="prose">${renderMarkdown(w.props.content || '')}</div>`;
    case 'html':
      return `<div class="widget-html-content">${w.props.content || ''}</div>`;
    case 'image':
      return `<figure style="margin:0.5rem 0">${w.props.src ? `<img src="${esc(w.props.src)}" alt="${esc(w.props.caption || '')}" style="max-width:${w.props.width ? w.props.width + 'px' : '100%'};border-radius:var(--radius-sm)">` : ''}${w.props.caption ? `<figcaption style="font-size:11px;color:var(--text-tertiary);margin-top:4px">${esc(w.props.caption)}</figcaption>` : ''}</figure>`;
    case 'divider':
      return '<hr class="w-divider">';
    case 'metric':
      return `<div class="w-metric"><div class="w-metric-label">${esc(w.props.label)}</div><div class="w-metric-val">${esc(String(w.props.value))}</div>${w.props.delta ? `<div class="w-metric-delta ${String(w.props.delta).startsWith('+') ? 'up' : String(w.props.delta).startsWith('-') ? 'down' : ''}">${esc(w.props.delta)}</div>` : ''}</div>`;
    case 'columns':
      const colFr = (w.props.ratios || [1, 1]).map(r => `${Number(r) || 1}fr`).join(' ');
      return `<div class="w-columns" style="grid-template-columns:${colFr}" data-cols="open"></div>`;
    case 'columns_end':
      return '';
    case 'expander':
      return `<div class="w-expander ${w.props.expanded ? 'open' : ''}"><button type="button" class="w-expander-head" aria-expanded="${w.props.expanded ? 'true' : 'false'}" onclick="const p=this.parentElement;const o=!p.classList.contains('open');p.classList.toggle('open',o);this.setAttribute('aria-expanded',String(o))"><span class="w-expander-arrow" aria-hidden="true">\u25B6</span><span>${esc(w.props.label)}</span></button><div class="w-expander-body"></div></div>`;
    case 'expander_end':
      return '';
    case 'toast':
      return '';
    case 'file_uploader':
      return `<div class="w-uploader" data-widget-action="file_upload" data-widget-key="${esc(w.props.key)}" data-accept="${esc(w.props.accept || '')}" data-multiple="${w.props.multiple ? 'true' : 'false'}"><div class="w-uploader-label">${esc(w.props.label)}</div><div class="w-uploader-hint">Drop a file here, or click to browse \u00b7 max ${MAX_FILE_MB} MB each</div><div class="w-uploader-files"></div><input type="file" accept="${esc(w.props.accept || '')}" ${w.props.multiple ? 'multiple' : ''}></div>`;
    case 'spinner':
      return `<div class="w-spinner" role="status" aria-live="polite"><div class="w-spinner-dot" aria-hidden="true"></div><span>${esc(w.props.label || 'Working on it\u2026')}</span></div>`;
    default:
      return '';
  }
}

function bindWidgetEvents(card, w) {
  if (!w) return;
  card.querySelectorAll('[data-widget-action]').forEach(el => {
    const action = el.dataset.widgetAction;
    const key = el.dataset.widgetKey || w.props.key || '';
    if (action === 'button_click') {
      el.addEventListener('click', () => {
        ws({ action: 'widget_event', event: 'button_click', widget_id: w.id, key, value: true, data: { key } });
      });
    } else if (action === 'text_input_submit') {
      el.addEventListener('click', () => {
        const input = card.querySelector('input[data-widget-key]');
        const val = input ? input.value : '';
        ws({ action: 'widget_event', event: 'text_input_submit', widget_id: w.id, key, value: val, data: { key, value: val } });
      });
    } else if (action === 'selectbox_change') {
      el.addEventListener('change', () => {
        ws({ action: 'widget_event', event: 'selectbox_change', widget_id: w.id, key, value: el.value, data: { key, value: el.value } });
      });
    } else if (action === 'radio_change') {
      el.addEventListener('change', () => {
        if (el.checked) {
          ws({ action: 'widget_event', event: 'radio_change', widget_id: w.id, key, value: el.value, data: { key, value: el.value } });
        }
      });
    } else if (action === 'checkbox_change') {
      el.addEventListener('change', () => {
        ws({ action: 'widget_event', event: 'checkbox_change', widget_id: w.id, key, value: el.checked, data: { key, value: el.checked } });
      });
    } else if (action === 'slider_change') {
      el.addEventListener('change', () => {
        ws({ action: 'widget_event', event: 'slider_change', widget_id: w.id, key, value: parseFloat(el.value), data: { key, value: parseFloat(el.value) } });
      });
    } else if (action === 'file_upload') {
      const uploader = el;
      const input = uploader.querySelector('input[type="file"]');
      uploader.addEventListener('click', () => input.click());
      uploader.addEventListener('dragover', e => { e.preventDefault(); uploader.classList.add('dragover'); });
      uploader.addEventListener('dragleave', () => uploader.classList.remove('dragover'));
      uploader.addEventListener('drop', e => {
        e.preventDefault(); uploader.classList.remove('dragover');
        handleFiles(e.dataTransfer.files, w, uploader);
      });
      input.addEventListener('change', () => {
        handleFiles(input.files, w, uploader);
      });
    }
  });
}

function handleFiles(files, w, uploader) {
  if (!files || !files.length) return;
  const maxBytes = MAX_FILE_MB * 1024 * 1024;
  const list = Array.from(files).slice(0, 10);
  const tooBig = list.filter(f => f.size > maxBytes);
  if (tooBig.length) {
    showToast(`File too large (max ${MAX_FILE_MB} MB): ${tooBig[0].name}`, 'error');
    return;
  }
  const names = list.map(f => f.name).join(', ');
  const filesDisplay = uploader.querySelector('.w-uploader-files');
  if (filesDisplay) filesDisplay.textContent = 'Selected: ' + names;
  const readers = list.map(file => new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = e => resolve({ name: file.name, type: file.type, size: file.size, content: e.target.result });
    reader.onerror = () => reject(new Error('Failed to read ' + file.name));
    reader.readAsDataURL(file);
  }));
  Promise.all(readers).then(results => {
    ws({ action: 'widget_event', event: 'file_upload', widget_id: w.id, key: w.props.key, value: names, data: { key: w.props.key, files: results } });
  }).catch(err => showToast(err.message || 'Upload failed', 'error'));
}
