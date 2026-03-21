const API = '';
let findings = [];
let activeTab = 'Users';
let activeOrg = null;

const CATEGORIES = ['Users', 'Flows', 'Fields', 'Permissions', 'Validation'];

// ---- Init ----
async function init() {
  await loadOrgs();
  const cached = await fetch(`${API}/findings`).then(r => r.json());
  if (cached.findings && cached.findings.length > 0) {
    findings = cached.findings;
    renderAll(cached.score);
  }
}

// ---- Orgs ----
async function loadOrgs() {
  const orgs = await fetch(`${API}/orgs`).then(r => r.json());
  const sel = document.getElementById('orgSelect');
  sel.innerHTML = '<option value="">— select org —</option>';
  orgs.forEach(o => {
    const opt = document.createElement('option');
    opt.value = o.org_id;
    opt.textContent = o.username || o.org_id;
    sel.appendChild(opt);
  });
  if (orgs.length > 0) {
    sel.value = orgs[0].org_id;
    activeOrg = orgs[0].org_id;
  }
}

async function connectOrg() {
  const r = await fetch(`${API}/orgs/connect`, { method: 'POST' }).then(r => r.json());
  window.open(r.auth_url, '_blank', 'width=600,height=700');
}

function onOrgChange(e) {
  activeOrg = e.target.value || null;
}

// ---- Scan ----
async function runScan() {
  if (!activeOrg) { showToast('Select an org first'); return; }
  showToast('Running scan…');
  const r = await fetch(`${API}/scan`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ org_id: activeOrg }),
  }).then(r => r.json());
  findings = r.findings || [];
  renderAll(r.score);
  showToast('Scan complete');
}

// ---- Render ----
function renderAll(score) {
  renderSummaryCards(score);
  renderTabs();
  renderFindings(activeTab);
}

function renderSummaryCards(score) {
  const counts = { Critical: 0, Warning: 0, Info: 0 };
  findings.forEach(f => { if (counts[f.severity] !== undefined) counts[f.severity]++; });
  document.getElementById('countCritical').textContent = counts.Critical;
  document.getElementById('countWarning').textContent = counts.Warning;
  document.getElementById('countInfo').textContent = counts.Info;
  document.getElementById('scoreNum').textContent = score;
}

function renderTabs() {
  const container = document.getElementById('tabs');
  container.innerHTML = '';
  CATEGORIES.forEach(cat => {
    const catFindings = findings.filter(f => f.category === cat);
    const hasCritical = catFindings.some(f => f.severity === 'Critical');
    const hasWarning = catFindings.some(f => f.severity === 'Warning');
    const badgeClass = hasCritical ? 'has-critical' : hasWarning ? 'has-warning' : '';
    const div = document.createElement('div');
    div.className = `tab${cat === activeTab ? ' active' : ''}`;
    div.onclick = () => switchTab(cat);
    div.innerHTML = `<span>${cat}</span><span class="badge ${badgeClass}">${catFindings.length}</span>`;
    container.appendChild(div);
  });
}

function switchTab(cat) {
  activeTab = cat;
  renderTabs();
  renderFindings(cat);
}

function renderFindings(cat) {
  const container = document.getElementById('findingsContainer');
  const catFindings = findings.filter(f => f.category === cat);
  document.getElementById('tabTitle').textContent = cat;

  if (catFindings.length === 0) {
    container.innerHTML = `<div class="empty-state">
      <div style="font-size:32px">✅</div>
      <p>No issues found in ${cat}</p>
    </div>`;
    return;
  }

  container.innerHTML = catFindings.map((f, i) => `
    <div class="finding-card ${f.severity}" id="finding-${f.category}-${i}">
      <span class="severity-badge ${f.severity}">${f.severity}</span>
      <span class="finding-title">${f.title}</span>
      <div class="finding-detail">${f.detail}</div>
      <div class="finding-rec">→ ${f.recommendation}</div>
      ${f.flow_api_name && f.severity !== 'Resolved' ? `
      <div class="finding-actions">
        <button class="btn btn-secondary btn-sm" onclick="generateDesc('${f.flow_api_name}', this)">✨ Generate Description</button>
      </div>
      <div class="desc-area" id="desc-${f.flow_api_name}" style="display:none">
        <textarea id="desc-text-${f.flow_api_name}" placeholder="AI-generated description will appear here…"></textarea>
        <div class="desc-actions">
          <button class="btn btn-primary btn-sm" onclick="writeDesc('${f.flow_api_name}')">Write to Org</button>
          <button class="btn btn-secondary btn-sm" onclick="cancelDesc('${f.flow_api_name}')">Cancel</button>
        </div>
      </div>` : ''}
    </div>
  `).join('');
}

// ---- AI Description ----
async function generateDesc(flowApiName, btn) {
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span>Generating…';
  try {
    const r = await fetch(`${API}/flows/${flowApiName}/describe`, { method: 'POST' }).then(r => r.json());
    if (r.detail) { showToast('Error: ' + r.detail); return; }
    document.getElementById(`desc-text-${flowApiName}`).value = r.description;
    document.getElementById(`desc-${flowApiName}`).style.display = 'block';
    btn.style.display = 'none';
  } catch (e) {
    showToast('Failed to generate description');
  } finally {
    btn.disabled = false;
    if (btn.innerHTML.includes('Generating')) btn.innerHTML = '✨ Generate Description';
  }
}

async function writeDesc(flowApiName) {
  const description = document.getElementById(`desc-text-${flowApiName}`).value.trim();
  if (!description) { showToast('Description cannot be empty'); return; }
  const r = await fetch(`${API}/flows/${flowApiName}/write-description`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ description }),
  }).then(r => r.json());
  if (r.status === 'ok') {
    const f = findings.find(f => f.flow_api_name === flowApiName && f.severity !== 'Resolved');
    if (f) f.severity = 'Resolved';
    renderFindings(activeTab);
    showToast('Description written to Salesforce ✓');
  } else {
    showToast('Error: ' + (r.detail || 'Unknown error'));
  }
}

function cancelDesc(flowApiName) {
  document.getElementById(`desc-${flowApiName}`).style.display = 'none';
}

// ---- Export PDF ----
async function exportPdf() {
  const clientName = prompt('Enter client name for the report:');
  if (!clientName) return;
  showToast('Generating PDF…');
  const resp = await fetch(`${API}/report`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ client_name: clientName }),
  });
  if (!resp.ok) { showToast('PDF generation failed'); return; }
  const blob = await resp.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `orgscan-${clientName}.pdf`;
  a.click();
  URL.revokeObjectURL(url);
}

// ---- Toast ----
function showToast(msg) {
  let toast = document.getElementById('toast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'toast';
    toast.className = 'toast';
    document.body.appendChild(toast);
  }
  toast.textContent = msg;
  toast.style.display = 'block';
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => { toast.style.display = 'none'; }, 3000);
}

init();
