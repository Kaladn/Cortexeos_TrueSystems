/* Wolf Engine — Command Center Dashboard JavaScript */

// =========================================================================
// Tab Navigation
// =========================================================================
document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
  });
});

// =========================================================================
// Chart.js Setup
// =========================================================================
const MAX_POINTS = 60;
const chartColors = {
  cyan:   'rgba(6,182,212,1)',
  green:  'rgba(16,185,129,1)',
  red:    'rgba(239,68,68,1)',
  amber:  'rgba(245,158,11,1)',
  purple: 'rgba(139,92,246,1)',
  blue:   'rgba(59,130,246,1)',
};

Chart.defaults.color = '#94a3b8';
Chart.defaults.borderColor = '#2d3748';
Chart.defaults.font.family = "'Segoe UI', 'Inter', sans-serif";

// CPU/RAM Chart
const cpuRamCtx = document.getElementById('chart-cpu-ram').getContext('2d');
const cpuRamChart = new Chart(cpuRamCtx, {
  type: 'line',
  data: {
    labels: [],
    datasets: [
      {
        label: 'CPU %',
        data: [],
        borderColor: chartColors.cyan,
        backgroundColor: 'rgba(6,182,212,0.1)',
        fill: true,
        tension: 0.4,
        borderWidth: 2,
        pointRadius: 0,
      },
      {
        label: 'RAM %',
        data: [],
        borderColor: chartColors.purple,
        backgroundColor: 'rgba(139,92,246,0.1)',
        fill: true,
        tension: 0.4,
        borderWidth: 2,
        pointRadius: 0,
      }
    ]
  },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 300 },
    scales: {
      x: { display: false },
      y: { min: 0, max: 100, ticks: { callback: v => v + '%' } }
    },
    plugins: {
      legend: { position: 'top', labels: { boxWidth: 12, padding: 16, font: {size: 11} } }
    }
  }
});

// Throughput Chart
const throughCtx = document.getElementById('chart-throughput').getContext('2d');
const throughChart = new Chart(throughCtx, {
  type: 'line',
  data: {
    labels: [],
    datasets: [
      {
        label: 'Requests OK',
        data: [],
        borderColor: chartColors.green,
        backgroundColor: 'rgba(16,185,129,0.1)',
        fill: true,
        tension: 0.4,
        borderWidth: 2,
        pointRadius: 0,
      },
      {
        label: 'Errors',
        data: [],
        borderColor: chartColors.red,
        backgroundColor: 'rgba(239,68,68,0.1)',
        fill: true,
        tension: 0.4,
        borderWidth: 2,
        pointRadius: 0,
      }
    ]
  },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 300 },
    scales: {
      x: { display: false },
      y: { min: 0, ticks: { stepSize: 1 } }
    },
    plugins: {
      legend: { position: 'top', labels: { boxWidth: 12, padding: 16, font: {size: 11} } }
    }
  }
});

// Verdict Doughnut
const verdictCtx = document.getElementById('chart-verdicts').getContext('2d');
const verdictChart = new Chart(verdictCtx, {
  type: 'doughnut',
  data: {
    labels: ['Approved', 'Adjusted', 'Quarantined', 'Penalized'],
    datasets: [{
      data: [0, 0, 0, 0],
      backgroundColor: [
        'rgba(16,185,129,0.8)',
        'rgba(245,158,11,0.8)',
        'rgba(239,68,68,0.8)',
        'rgba(139,92,246,0.8)',
      ],
      borderColor: '#1a2332',
      borderWidth: 2,
    }]
  },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    cutout: '65%',
    plugins: {
      legend: {
        position: 'right',
        labels: { boxWidth: 10, padding: 10, font: {size: 11} }
      }
    }
  }
});

// =========================================================================
// Helpers
// =========================================================================
let prevRequests = {};
let startTime = Date.now();

function timeLabel() {
  return new Date().toLocaleTimeString('en-US', {hour12: false});
}

function fmtUptime(sec) {
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = Math.floor(sec % 60);
  return `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
}

function barColor(pct) {
  if (pct < 60) return 'green';
  if (pct < 85) return 'amber';
  return 'red';
}

function statusPill(status) {
  return `<span class="status-pill status-${status}">${status}</span>`;
}

function escHtml(s) {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

function setStatus(text, cls) {
  const el = document.getElementById('analyze-status');
  el.textContent = text;
  el.className = 'analyze-status' + (cls ? ' ' + cls : '');
}

function setButtons(disabled) {
  document.getElementById('btn-analyze').disabled = disabled;
  document.getElementById('btn-ingest').disabled = disabled;
}

// =========================================================================
// COMMAND: Analyze & Ingest
// =========================================================================
async function doAnalyze() {
  const text = document.getElementById('analyze-input').value.trim();
  if (!text) { setStatus('Enter text first', 'error'); return; }

  setButtons(true);
  setStatus('Analyzing...', 'running');

  try {
    const body = { text };
    const sid = document.getElementById('session-id').value.trim();
    if (sid) body.session_id = sid;

    const resp = await fetch('/api/analyze', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(body),
    });

    const data = await resp.json();

    if (!resp.ok) {
      setStatus('Error: ' + (data.error || resp.statusText), 'error');
      showError(data.error || 'Analysis failed');
      return;
    }

    setStatus('Done', 'done');
    showAnalysisResult(data);
    refreshSnapshot();
  } catch (err) {
    setStatus('Network error', 'error');
    showError(err.message);
  } finally {
    setButtons(false);
  }
}

async function doIngest() {
  const text = document.getElementById('analyze-input').value.trim();
  if (!text) { setStatus('Enter text first', 'error'); return; }

  setButtons(true);
  setStatus('Ingesting...', 'running');

  try {
    const body = { text };
    const sid = document.getElementById('session-id').value.trim();
    if (sid) body.session_id = sid;

    const resp = await fetch('/api/ingest', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(body),
    });

    const data = await resp.json();

    if (!resp.ok) {
      setStatus('Error: ' + (data.error || resp.statusText), 'error');
      showError(data.error || 'Ingest failed');
      return;
    }

    setStatus('Done', 'done');
    showIngestResult(data);
    refreshSnapshot();
  } catch (err) {
    setStatus('Network error', 'error');
    showError(err.message);
  } finally {
    setButtons(false);
  }
}

function clearInput() {
  document.getElementById('analyze-input').value = '';
  document.getElementById('session-id').value = '';
  setStatus('');
}

function showAnalysisResult(data) {
  const body = document.getElementById('result-body');
  const badge = document.getElementById('result-badge');
  const v = data.verdict || {};
  const p = data.patterns || {};

  const status = v.status || 'unknown';
  badge.style.display = 'inline-block';
  badge.className = 'badge badge-live';
  badge.textContent = 'Session: ' + (data.session_id || '?');

  const conf = (v.adjusted_confidence || 0);
  const confPct = Math.min(100, Math.max(0, conf * 100));

  let flagsHtml = '';
  if (v.flags && v.flags.length > 0) {
    flagsHtml = '<div style="margin-top:8px; font-size:11px; color:var(--text-muted);">' +
      v.flags.map(f => `<span style="margin-right:8px;">${escHtml(f.code)}: ${escHtml(f.description || '')}</span>`).join('') +
      '</div>';
  }

  let detailHtml = '';
  if (p.break_details && p.break_details.length > 0) {
    detailHtml += '<div class="detail-list" style="margin-top:10px;"><strong style="color:var(--accent-red); font-size:10px; text-transform:uppercase;">Pattern Breaks</strong>';
    p.break_details.forEach(b => {
      detailHtml += `<div class="item">anchor=${b.anchor_id} severity=${b.severity} idx=${b.anchor_index} type=${b.break_type}</div>`;
    });
    detailHtml += '</div>';
  }
  if (p.chain_details && p.chain_details.length > 0) {
    detailHtml += '<div class="detail-list" style="margin-top:8px;"><strong style="color:var(--accent-amber); font-size:10px; text-transform:uppercase;">Causal Chains</strong>';
    p.chain_details.forEach(c => {
      detailHtml += `<div class="item">start=${c.start} len=${c.length} consistency=${c.avg_consistency}</div>`;
    });
    detailHtml += '</div>';
  }
  if (p.anomaly_details && p.anomaly_details.length > 0) {
    detailHtml += '<div class="detail-list" style="margin-top:8px;"><strong style="color:var(--accent-purple); font-size:10px; text-transform:uppercase;">Anomalies</strong>';
    p.anomaly_details.forEach(a => {
      detailHtml += `<div class="item">anchor=${a.anchor_id} ${escHtml(a.reason)} consistency=${a.consistency}</div>`;
    });
    detailHtml += '</div>';
  }

  let ingestHtml = '';
  if (data.ingest) {
    const ig = data.ingest;
    ingestHtml = `<div style="margin-top:12px; padding:10px; background:var(--bg-primary); border-radius:6px; border:1px solid var(--border); font-size:11px; color:var(--text-muted);">
      Ingested: ${ig.tokens} tokens &rarr; ${ig.anchors_ingested} symbols | Forge: ${ig.forge?.total_symbols || 0} symbols, ${ig.forge?.total_chains || 0} chains
    </div>`;
  }

  body.innerHTML = `
    <div class="verdict-display">
      <span class="verdict-badge verdict-${status}">${status}</span>
      <div class="verdict-meta">
        <div class="conf">${conf.toFixed(4)}</div>
        <div class="detail">confidence (orig: ${(v.original_confidence || 0).toFixed(4)})</div>
      </div>
      <div class="confidence-bar">
        <div class="confidence-fill" style="width:${confPct}%"></div>
      </div>
    </div>
    ${flagsHtml}
    <div class="pattern-grid">
      <div class="pattern-stat"><div class="num red">${p.breaks || 0}</div><div class="lbl">Pattern Breaks</div></div>
      <div class="pattern-stat"><div class="num amber">${p.chains || 0}</div><div class="lbl">Causal Chains</div></div>
      <div class="pattern-stat"><div class="num purple">${p.anomalies || 0}</div><div class="lbl">Anomalies</div></div>
    </div>
    ${detailHtml}
    ${ingestHtml}
  `;
}

function showIngestResult(data) {
  const body = document.getElementById('result-body');
  const badge = document.getElementById('result-badge');
  badge.style.display = 'inline-block';
  badge.className = 'badge badge-live';
  badge.textContent = 'Ingest: ' + (data.session_id || '?');

  const forge = data.forge || {};
  let errHtml = '';
  if (data.errors && data.errors.length > 0) {
    errHtml = '<div class="detail-list" style="margin-top:10px;"><strong style="color:var(--accent-red); font-size:10px;">ERRORS</strong>';
    data.errors.forEach(e => { errHtml += `<div class="item">${escHtml(e)}</div>`; });
    errHtml += '</div>';
  }

  body.innerHTML = `
    <div style="text-align:center; padding:20px;">
      <div style="font-size:36px; font-weight:800; color:var(--accent-cyan); font-family:'Cascadia Code','Fira Code',monospace;">${data.tokens || 0}</div>
      <div style="font-size:11px; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.08em; margin-top:4px;">Tokens Processed</div>
    </div>
    <div class="pattern-grid">
      <div class="pattern-stat"><div class="num" style="color:var(--accent-green);">${data.anchors_ingested || 0}</div><div class="lbl">Anchors Ingested</div></div>
      <div class="pattern-stat"><div class="num" style="color:var(--accent-cyan);">${forge.total_symbols || 0}</div><div class="lbl">Forge Symbols</div></div>
      <div class="pattern-stat"><div class="num" style="color:var(--accent-purple);">${forge.total_chains || 0}</div><div class="lbl">Chains Built</div></div>
    </div>
    ${errHtml}
  `;
}

function showError(msg) {
  const body = document.getElementById('result-body');
  body.innerHTML = `<div class="empty-state"><div class="icon" style="color:var(--accent-red);">&#x2716;</div><div style="color:var(--accent-red);">${escHtml(msg)}</div></div>`;
}

// =========================================================================
// SYMBOLS: Explorer & Query
// =========================================================================
async function loadTopSymbols() {
  try {
    const resp = await fetch('/api/symbols/top?limit=30');
    const data = await resp.json();
    if (!data || data.length === 0) {
      document.getElementById('symbol-empty').style.display = 'block';
      document.getElementById('symbol-table').style.display = 'none';
      return;
    }
    renderSymbolTable(data);
  } catch (err) {
    console.error('Top symbols error:', err);
  }
}

async function querySymbol() {
  const id = document.getElementById('symbol-search-id').value.trim();
  if (!id) return;

  try {
    const resp = await fetch('/api/query/' + encodeURIComponent(id));
    if (!resp.ok) {
      showSymbolDetail(null, id);
      return;
    }
    const data = await resp.json();
    showSymbolDetail(data, id);
  } catch (err) {
    console.error('Query symbol error:', err);
  }
}

function renderSymbolTable(symbols) {
  document.getElementById('symbol-empty').style.display = 'none';
  const table = document.getElementById('symbol-table');
  table.style.display = 'table';
  const tbody = document.getElementById('symbol-table-body');

  let html = '';
  for (const s of symbols) {
    const neighbors = (s.top_neighbors || []).map(n => n.id).slice(0, 3).join(', ');
    html += `<tr onclick="querySymbolById(${s.symbol_id})">
      <td>${s.symbol_id}</td>
      <td>${s.resonance}</td>
      <td>${s.co_occurrence_count}</td>
      <td style="font-size:11px; max-width:180px; overflow:hidden; text-overflow:ellipsis;">${neighbors || '-'}</td>
    </tr>`;
  }
  tbody.innerHTML = html;
}

function querySymbolById(id) {
  document.getElementById('symbol-search-id').value = id;
  querySymbol();
}

function showSymbolDetail(data, id) {
  const panel = document.getElementById('symbol-detail');
  const content = document.getElementById('symbol-detail-content');

  if (!data) {
    panel.classList.add('visible');
    content.innerHTML = `<div style="color:var(--accent-red);">Symbol ${escHtml(String(id))} not found in Forge memory</div>`;
    return;
  }

  let neighborsHtml = '';
  if (data.neighbors && Object.keys(data.neighbors).length > 0) {
    const sorted = Object.entries(data.neighbors).sort((a, b) => b[1] - a[1]).slice(0, 20);
    neighborsHtml = '<div style="margin-top:8px;"><strong style="font-size:10px; color:var(--text-muted); text-transform:uppercase;">Co-occurrence Neighbors</strong>';
    neighborsHtml += '<div class="neighbor-list">';
    for (const [nid, count] of sorted) {
      neighborsHtml += `<span class="neighbor-chip" onclick="querySymbolById(${nid})" title="count: ${count}">${nid} (${count})</span>`;
    }
    neighborsHtml += '</div></div>';
  }

  let chainsHtml = '';
  if (data.chains && data.chains.length > 0) {
    chainsHtml = '<div style="margin-top:10px;"><strong style="font-size:10px; color:var(--text-muted); text-transform:uppercase;">Chains</strong>';
    chainsHtml += '<div class="detail-list">';
    data.chains.slice(0, 5).forEach(c => {
      chainsHtml += `<div class="item">[${c.join(' &rarr; ')}]</div>`;
    });
    chainsHtml += '</div></div>';
  }

  panel.classList.add('visible');
  content.innerHTML = `
    <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:10px; margin-bottom:10px;">
      <div><span style="color:var(--text-muted); font-size:10px; text-transform:uppercase;">ID</span><br>
           <span style="font-family:'Cascadia Code','Fira Code',monospace; color:var(--accent-cyan); font-size:14px; font-weight:700;">${data.symbol_id}</span></div>
      <div><span style="color:var(--text-muted); font-size:10px; text-transform:uppercase;">Resonance</span><br>
           <span style="font-family:'Cascadia Code','Fira Code',monospace; color:var(--accent-amber); font-size:14px; font-weight:700;">${(data.resonance || 0).toFixed(2)}</span></div>
      <div><span style="color:var(--text-muted); font-size:10px; text-transform:uppercase;">Neighbors</span><br>
           <span style="font-family:'Cascadia Code','Fira Code',monospace; color:var(--accent-purple); font-size:14px; font-weight:700;">${Object.keys(data.neighbors || {}).length}</span></div>
    </div>
    <div style="margin-top:6px;">
      <button class="btn btn-accent btn-sm" onclick="startCascadeFrom(${data.symbol_id})">Cascade Trace &rarr;</button>
    </div>
    ${neighborsHtml}
    ${chainsHtml}
  `;
}

function startCascadeFrom(symbolId) {
  document.getElementById('cascade-id').value = symbolId;
  traceCascade();
}

// =========================================================================
// CASCADE TRACER
// =========================================================================
async function traceCascade() {
  const id = document.getElementById('cascade-id').value.trim();
  if (!id) return;

  const dir = document.getElementById('cascade-dir').value;
  const depth = parseInt(document.getElementById('cascade-depth').value) || 5;

  try {
    const resp = await fetch('/api/cascade', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ symbol_id: parseInt(id), direction: dir, max_depth: depth }),
    });

    const data = await resp.json();
    if (!resp.ok) {
      document.getElementById('cascade-empty').style.display = 'block';
      document.getElementById('cascade-summary').style.display = 'none';
      return;
    }

    showCascadeResult(data);
  } catch (err) {
    console.error('Cascade error:', err);
  }
}

function showCascadeResult(data) {
  document.getElementById('cascade-empty').style.display = 'none';

  const summary = document.getElementById('cascade-summary');
  summary.style.display = 'block';
  summary.innerHTML = `
    <div style="display:flex; gap:16px; padding:10px; background:var(--bg-primary); border-radius:6px; border:1px solid var(--border); font-size:12px;">
      <div><span style="color:var(--text-muted);">Root:</span> <span style="color:var(--accent-purple); font-weight:700;">${data.root}</span></div>
      <div><span style="color:var(--text-muted);">Direction:</span> <span style="color:var(--text-primary);">${data.direction}</span></div>
      <div><span style="color:var(--text-muted);">Depth:</span> <span style="color:var(--text-primary);">${data.depth}</span></div>
      <div><span style="color:var(--text-muted);">Nodes:</span> <span style="color:var(--accent-cyan); font-weight:700;">${data.total_nodes}</span></div>
    </div>
  `;

  const container = document.getElementById('cascade-nodes');
  if (!data.nodes || data.nodes.length === 0) {
    container.innerHTML = '<div style="padding:16px; color:var(--text-muted); font-size:12px;">No connected nodes found</div>';
    return;
  }

  const maxStrength = Math.max(...data.nodes.map(n => n.strength), 0.001);
  let html = '';
  for (const node of data.nodes) {
    const pct = (node.strength / maxStrength * 100).toFixed(0);
    const indent = node.depth * 16;
    html += `
      <div class="cascade-node" style="padding-left:${10 + indent}px;">
        <span class="cascade-depth">d${node.depth}</span>
        <span class="cascade-id" onclick="querySymbolById(${node.symbol_id})">${node.symbol_id}</span>
        <div class="cascade-bar"><div class="cascade-bar-fill" style="width:${pct}%"></div></div>
        <span class="cascade-strength">${node.strength.toFixed(3)}</span>
      </div>`;
  }
  container.innerHTML = html;
}

// =========================================================================
// ACTIVITY LOG
// =========================================================================
function updateActivityLog(activities) {
  const log = document.getElementById('activity-log');
  if (!activities || activities.length === 0) return;

  let html = '';
  for (const a of activities) {
    html += `
      <div class="activity-entry">
        <span class="activity-time">${escHtml(a.time || '')}</span>
        <span class="activity-action ${a.action || ''}">${escHtml(a.action || '')}</span>
        <span class="activity-detail">${escHtml(a.detail || '')}</span>
        <span class="activity-session">${escHtml(a.session_id || '')}</span>
      </div>`;
  }
  log.innerHTML = html;
}

async function refreshSnapshot() {
  try {
    const resp = await fetch('/api/snapshot');
    if (!resp.ok) return;
    const data = await resp.json();

    // Update summary bar from snapshot
    const c = data.counters || {};
    document.getElementById('sum-ingested').textContent = (c.total_ingested || 0).toLocaleString();
    document.getElementById('sum-analyses').textContent = (c.total_analyses || 0).toLocaleString();
    document.getElementById('sum-tokens').textContent = (c.total_tokens || 0).toLocaleString();

    const forge = data.forge || {};
    document.getElementById('sum-symbols').textContent = (forge.total_symbols || 0).toLocaleString();
    document.getElementById('sum-resonance').textContent = (forge.avg_resonance || 0).toFixed(2);

    // Verdict count
    const vd = data.verdicts || {};
    const totalVerdicts = Object.values(vd).reduce((s, v) => s + v, 0);
    document.getElementById('sum-verdicts').textContent = totalVerdicts.toLocaleString();

    // Activity log
    if (data.activity) {
      updateActivityLog(data.activity);
    }
  } catch (err) {
    // silent
  }
}

// =========================================================================
// SSE Connection
// =========================================================================
function connectSSE() {
  const evtSource = new EventSource('/api/stream');

  evtSource.addEventListener('metrics', function(e) {
    const data = JSON.parse(e.data);
    updateMonitor(data);
  });

  evtSource.addEventListener('verdicts', function(e) {
    const data = JSON.parse(e.data);
    updateVerdicts(data);
  });

  evtSource.addEventListener('activity', function(e) {
    const data = JSON.parse(e.data);
    // Update summary bar
    const c = data.counters || {};
    document.getElementById('sum-ingested').textContent = (c.total_ingested || 0).toLocaleString();
    document.getElementById('sum-analyses').textContent = (c.total_analyses || 0).toLocaleString();
    document.getElementById('sum-tokens').textContent = (c.total_tokens || 0).toLocaleString();

    const forge = data.forge || {};
    document.getElementById('sum-symbols').textContent = (forge.total_symbols || 0).toLocaleString();
    document.getElementById('sum-resonance').textContent = (forge.avg_resonance || 0).toFixed(2);

    const vd = data.verdicts || {};
    const totalVerdicts = Object.values(vd).reduce((s, v) => s + v, 0);
    document.getElementById('sum-verdicts').textContent = totalVerdicts.toLocaleString();

    if (data.activity) {
      updateActivityLog(data.activity);
    }
  });

  evtSource.onerror = function() {
    document.getElementById('conn-status').textContent = 'RECONNECTING';
    evtSource.close();
    setTimeout(() => {
      document.getElementById('conn-status').textContent = 'LIVE';
      connectSSE();
    }, 3000);
  };
}

// =========================================================================
// Monitor Tab Updates
// =========================================================================
function updateMonitor(data) {
  const nodes = data.nodes || {};
  const summary = data.summary || {};
  const now = Date.now();

  // Error rate
  const errRate = summary.error_rate || 0;
  const errEl = document.getElementById('sum-error-rate');
  errEl.textContent = errRate.toFixed(1) + '%';
  errEl.className = 'value ' + (errRate > 5 ? 'red' : errRate > 1 ? 'amber' : 'green');

  // Node health
  const grid = document.getElementById('node-grid');
  let nodeHTML = '';
  const nodeIds = Object.keys(nodes).sort();

  for (const nid of nodeIds) {
    const n = nodes[nid];
    const age = (now / 1000) - (n.timestamp || 0);
    const status = age < 30 ? 'healthy' : age < 60 ? 'stale' : 'down';

    nodeHTML += `
      <div class="node-box ${status}">
        <div class="node-name">
          <span class="node-status-dot ${status}"></span>
          ${escHtml(nid)}
        </div>
        <div class="node-metrics">
          <div class="node-metric"><span>CPU</span><span>${(n.cpu_percent||0).toFixed(1)}%</span></div>
          <div class="node-metric"><span>RAM</span><span>${(n.ram_percent||0).toFixed(1)}%</span></div>
          <div class="node-metric"><span>Reqs</span><span>${(n.requests_total||0)}</span></div>
          <div class="node-metric"><span>Errs</span><span>${(n.requests_error||0)}</span></div>
          ${n.gpu_available ? `<div class="node-metric"><span>GPU</span><span>${(n.gpu_util_percent||0).toFixed(0)}%</span></div>` : ''}
          ${n.gpu_available ? `<div class="node-metric"><span>VRAM</span><span>${(n.gpu_mem_used_mb||0).toFixed(0)}MB</span></div>` : ''}
        </div>
      </div>`;
  }
  grid.innerHTML = nodeHTML || '<div class="node-box stale"><div class="node-name"><span class="node-status-dot stale"></span>No nodes reporting</div></div>';

  // CPU/RAM chart
  const firstNode = nodes[nodeIds[0]];
  if (firstNode) {
    const label = timeLabel();
    cpuRamChart.data.labels.push(label);
    cpuRamChart.data.datasets[0].data.push(firstNode.cpu_percent || 0);
    cpuRamChart.data.datasets[1].data.push(firstNode.ram_percent || 0);
    if (cpuRamChart.data.labels.length > MAX_POINTS) {
      cpuRamChart.data.labels.shift();
      cpuRamChart.data.datasets[0].data.shift();
      cpuRamChart.data.datasets[1].data.shift();
    }
    cpuRamChart.update('none');
  }

  // Throughput chart
  let totalOk = 0, totalErr = 0;
  for (const nid of nodeIds) {
    const n = nodes[nid];
    const prevOk = (prevRequests[nid] || {}).ok || 0;
    const prevEr = (prevRequests[nid] || {}).err || 0;
    totalOk  += (n.requests_ok || 0) - prevOk;
    totalErr += (n.requests_error || 0) - prevEr;
    prevRequests[nid] = { ok: n.requests_ok || 0, err: n.requests_error || 0 };
  }
  throughChart.data.labels.push(timeLabel());
  throughChart.data.datasets[0].data.push(Math.max(0, totalOk));
  throughChart.data.datasets[1].data.push(Math.max(0, totalErr));
  if (throughChart.data.labels.length > MAX_POINTS) {
    throughChart.data.labels.shift();
    throughChart.data.datasets[0].data.shift();
    throughChart.data.datasets[1].data.shift();
  }
  throughChart.update('none');

  // GPU panel
  const gpuNode = Object.values(nodes).find(n => n.gpu_available);
  const gpuPanel = document.getElementById('gpu-panel');
  if (gpuNode) {
    const memPct = gpuNode.gpu_mem_total_mb > 0
      ? (gpuNode.gpu_mem_used_mb / gpuNode.gpu_mem_total_mb * 100).toFixed(1) : 0;
    gpuPanel.innerHTML = `
      <div style="font-size:14px; font-weight:700; color:var(--accent-cyan); margin-bottom:12px;">
        ${escHtml(gpuNode.gpu_name || 'CUDA GPU')}
      </div>
      <div class="bar-container">
        <div class="bar-label"><span>GPU Utilization</span><span>${(gpuNode.gpu_util_percent||0).toFixed(0)}%</span></div>
        <div class="bar-track"><div class="bar-fill ${barColor(gpuNode.gpu_util_percent||0)}" style="width:${gpuNode.gpu_util_percent||0}%"></div></div>
      </div>
      <div class="bar-container">
        <div class="bar-label"><span>VRAM (${(gpuNode.gpu_mem_used_mb||0).toFixed(0)} / ${(gpuNode.gpu_mem_total_mb||0).toFixed(0)} MB)</span><span>${memPct}%</span></div>
        <div class="bar-track"><div class="bar-fill cyan" style="width:${memPct}%"></div></div>
      </div>
      <div class="bar-container">
        <div class="bar-label"><span>Temperature</span><span>${(gpuNode.gpu_temp_c||0).toFixed(0)}C</span></div>
        <div class="bar-track"><div class="bar-fill ${gpuNode.gpu_temp_c > 80 ? 'red' : gpuNode.gpu_temp_c > 65 ? 'amber' : 'green'}" style="width:${Math.min(100, (gpuNode.gpu_temp_c||0)/100*100)}%"></div></div>
      </div>
    `;
  } else {
    gpuPanel.innerHTML = '<div style="color:var(--text-muted); font-size:13px;">No GPU node detected</div>';
  }

  // Forge stats
  const fs = summary;
  document.getElementById('forge-symbols').textContent = (fs.forge_symbols || 0).toLocaleString();
  document.getElementById('forge-resonance').textContent = (fs.forge_resonance || 0).toFixed(2);

  // Also update from nodes if available
  const forgeNode = Object.values(nodes).find(n => n.forge_total_symbols > 0) || {};
  if (forgeNode.forge_total_symbols) {
    document.getElementById('forge-symbols').textContent = forgeNode.forge_total_symbols.toLocaleString();
    document.getElementById('forge-chains').textContent = (forgeNode.forge_total_chains || 0).toLocaleString();
    document.getElementById('forge-resonance').textContent = (forgeNode.forge_avg_resonance || 0).toFixed(2);
    document.getElementById('forge-window').textContent = (forgeNode.forge_window_size || 0).toLocaleString();
    document.getElementById('forge-current').textContent = (forgeNode.forge_current_size || 0).toLocaleString();
  }

  // Verdict doughnut
  const approved = summary.verdicts_approved || 0;
  const adjusted = summary.verdicts_adjusted || 0;
  const quarantined = summary.verdicts_quarantined || 0;
  const penalized = summary.verdicts_penalized || 0;
  verdictChart.data.datasets[0].data = [approved, adjusted, quarantined, penalized];
  verdictChart.update('none');
}

function updateVerdicts(verdicts) {
  const tbody = document.getElementById('verdict-table-body');
  if (!verdicts || verdicts.length === 0) return;

  let rows = '';
  for (const v of verdicts.slice(0, 20)) {
    const t = v.timestamp ? new Date(v.timestamp * 1000).toLocaleTimeString('en-US', {hour12:false}) : '-';
    const flagCount = (v.flags || []).length;
    const flagCodes = (v.flags || []).map(f => f.code || '').join(', ');
    rows += `<tr>
      <td>${t}</td>
      <td>${escHtml(v.session_id || '-')}</td>
      <td>${statusPill(v.status || 'unknown')}</td>
      <td>${(v.original_confidence||0).toFixed(3)}</td>
      <td>${(v.adjusted_confidence||0).toFixed(3)}</td>
      <td title="${escHtml(flagCodes)}">${flagCount} flag${flagCount !== 1 ? 's' : ''}</td>
    </tr>`;
  }
  tbody.innerHTML = rows;
}

// =========================================================================
// Polling fallback
// =========================================================================
async function pollAll() {
  try {
    const [metricsRes, verdictsRes] = await Promise.all([
      fetch('/api/metrics'),
      fetch('/api/verdicts/recent'),
    ]);
    if (metricsRes.ok) updateMonitor(await metricsRes.json());
    if (verdictsRes.ok) updateVerdicts(await verdictsRes.json());
  } catch (e) {
    // silent
  }
  refreshSnapshot();
}

// =========================================================================
// Init
// =========================================================================
if (typeof EventSource !== 'undefined') {
  connectSSE();
} else {
  setInterval(pollAll, 5000);
}

// Initial data load — populate everything immediately
pollAll();
refreshSnapshot();
loadTopSymbols();

// Uptime ticker
setInterval(() => {
  document.getElementById('uptime').textContent = fmtUptime((Date.now() - startTime) / 1000);
}, 1000);

// Keyboard shortcut: Ctrl+Enter to analyze
document.getElementById('analyze-input').addEventListener('keydown', (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
    e.preventDefault();
    doAnalyze();
  }
});

// =========================================================================
// Round 1: Debug Push
// =========================================================================
async function debugPush() {
  const status = document.getElementById('debug-status');
  const result = document.getElementById('debug-result');
  status.textContent = 'Pushing...';
  status.style.color = 'var(--accent-amber)';
  try {
    const resp = await fetch('/api/debug/push', {method: 'POST'});
    const data = await resp.json();
    if (resp.ok) {
      status.textContent = 'Done';
      status.style.color = 'var(--accent-green)';
      result.innerHTML = `<div style="background:var(--bg-input); border:1px solid var(--border); border-radius:8px; padding:12px; font-size:12px; font-family:monospace; color:var(--accent-green);">
        Verdict injected: <strong>${escHtml(data.verdict_id||'')}</strong><br>
        Session: ${escHtml(data.session_id||'')}<br>
        Check Monitor tab for updated charts and verdict table.
      </div>`;
    } else {
      status.textContent = 'Error';
      status.style.color = 'var(--accent-red)';
      result.textContent = data.error || 'Unknown error';
    }
  } catch (err) {
    status.textContent = 'Failed';
    status.style.color = 'var(--accent-red)';
    result.textContent = err.message;
  }
}

// =========================================================================
// Round 2: Session Recording
// =========================================================================
async function startRecording() {
  const label = document.getElementById('rec-label').value;
  const status = document.getElementById('rec-status');
  try {
    const resp = await fetch('/api/session/start', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({label})
    });
    const data = await resp.json();
    if (resp.ok) {
      updateRecordingUI(true, data.session);
      status.textContent = 'Recording started';
      status.style.color = 'var(--accent-green)';
    } else {
      status.textContent = data.error || 'Error';
      status.style.color = 'var(--accent-red)';
    }
  } catch (err) {
    status.textContent = err.message;
    status.style.color = 'var(--accent-red)';
  }
}

async function stopRecording() {
  const status = document.getElementById('rec-status');
  try {
    const resp = await fetch('/api/session/stop', {method: 'POST'});
    const data = await resp.json();
    if (resp.ok) {
      updateRecordingUI(false, data.session);
      status.textContent = `Stopped. ${data.session.event_count} events captured.`;
      status.style.color = 'var(--text-muted)';
    } else {
      status.textContent = data.error || 'Error';
      status.style.color = 'var(--accent-red)';
    }
  } catch (err) {
    status.textContent = err.message;
    status.style.color = 'var(--accent-red)';
  }
}

function updateRecordingUI(active, session) {
  const badge = document.getElementById('rec-badge');
  const startBtn = document.getElementById('btn-rec-start');
  const stopBtn = document.getElementById('btn-rec-stop');
  const info = document.getElementById('rec-info');
  if (active) {
    badge.style.display = '';
    badge.className = 'badge badge-live';
    badge.textContent = 'REC';
    startBtn.disabled = true;
    stopBtn.disabled = false;
    info.innerHTML = `<div style="font-size:12px; color:var(--text-secondary);">
      Session: <code>${escHtml(session.session_id||'')}</code><br>
      Label: ${escHtml(session.label||'')}<br>
      Dir: <code>${escHtml(session.session_dir||'')}</code>
    </div>`;
  } else {
    badge.style.display = 'none';
    startBtn.disabled = false;
    stopBtn.disabled = true;
    if (session) {
      info.innerHTML = `<div style="font-size:12px; color:var(--text-muted);">
        Last session: ${escHtml(session.session_id||'')} (${session.event_count||0} events)
      </div>`;
    }
  }
}

// Check recording status on load
(async function checkRecStatus() {
  try {
    const resp = await fetch('/api/session/status');
    const data = await resp.json();
    if (data.recording) updateRecordingUI(true, data.session);
  } catch(e) {}
})();

// =========================================================================
// Round 4: Export + Reset
// =========================================================================
async function exportData(what) {
  const es = document.getElementById('export-status');
  es.textContent = 'Exporting...';
  try {
    const resp = await fetch(`/api/export?what=${what}`);
    const data = await resp.json();
    if (resp.ok) {
      const blob = new Blob([JSON.stringify(data, null, 2)], {type: 'application/json'});
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `wolf_${what}_${new Date().toISOString().slice(0,10)}.json`;
      a.click();
      URL.revokeObjectURL(url);
      const count = Array.isArray(data) ? data.length : Object.keys(data).length;
      es.textContent = `Exported ${count} ${what} records.`;
      es.style.color = 'var(--accent-green)';
    } else {
      es.textContent = data.error || 'Export failed';
      es.style.color = 'var(--accent-red)';
    }
  } catch (err) {
    es.textContent = err.message;
    es.style.color = 'var(--accent-red)';
  }
}

async function resetState() {
  if (!confirm('Reset Forge memory and counters? Verdict audit trail will be preserved.')) return;
  const es = document.getElementById('export-status');
  try {
    const resp = await fetch('/api/reset', {method: 'POST'});
    const data = await resp.json();
    if (resp.ok) {
      es.textContent = data.message || 'Reset complete.';
      es.style.color = 'var(--accent-green)';
      refreshSnapshot();
    } else {
      es.textContent = data.error || 'Reset failed';
      es.style.color = 'var(--accent-red)';
    }
  } catch (err) {
    es.textContent = err.message;
    es.style.color = 'var(--accent-red)';
  }
}
