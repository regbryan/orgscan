/**
 * OrgScan — DashStack UI
 * IIFE module pattern. State object drives all rendering.
 * innerHTML is used intentionally for SPA templating.
 * All user-supplied data passes through esc() before insertion.
 */
(function () {
  'use strict';

  const API = '';
  const CATEGORIES = ['Users', 'Flows', 'Fields', 'Permissions', 'Validation'];

  // ================================================================
  // STATE
  // ================================================================
  const state = {
    activeOrg: null,
    orgs: [],
    findings: [],
    score: null,
    activeView: 'dashboard',
    activityLog: [],
    error: null,
  };

  // ================================================================
  // ICONS — inline SVG strings
  // ================================================================
  const I = {
    grid:     '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>',
    users:    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>',
    flow:     '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>',
    fields:   '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg>',
    lock:     '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>',
    check:    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>',
    clock:    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>',
    cog:      '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.07 4.93l-1.41 1.41M4.93 4.93l1.41 1.41M4.93 19.07l1.41-1.41M19.07 19.07l-1.41-1.41M1 12h2M21 12h2M12 1v2M12 21v2"/></svg>',
    logout:   '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>',
    shieldSm: '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>',
    shieldWh: '<svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>',
    alertSm:  '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
    infoSm:   '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>',
    menu:     '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/></svg>',
    sparkle:  '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>',
    pen:      '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>',
    filePdf:  '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>',
  };

  // ================================================================
  // UTILITY
  // ================================================================
  function esc(s) {
    if (s == null) return '';
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function severityBadge(sev) {
    const map = { Critical: 'badge-critical', Warning: 'badge-warning', Info: 'badge-info', Resolved: 'badge-resolved' };
    return '<span class="badge ' + (map[sev] || 'badge-info') + '">' + esc(sev) + '</span>';
  }

  function showToast(msg, type) {
    const t = document.getElementById('toast');
    if (!t) return;
    t.textContent = msg;
    t.className = 'toast show' + (type ? ' ' + type : '');
    clearTimeout(t._timer);
    t._timer = setTimeout(function () { t.className = 'toast'; }, 3200);
  }

  function navigate(view) {
    state.activeView = view;
    state.error = null;
    if (view === 'activity') { loadActivity(); return; }
    render();
  }

  function catCounts() {
    const out = {};
    CATEGORIES.forEach(c => { out[c] = { total: 0, critical: false, warning: false }; });
    state.findings.forEach(f => {
      if (out[f.category]) {
        out[f.category].total++;
        if (f.severity === 'Critical') out[f.category].critical = true;
        if (f.severity === 'Warning')  out[f.category].warning  = true;
      }
    });
    return out;
  }

  // ================================================================
  // SIDEBAR
  // ================================================================
  function navItem(view, icon, label, badge) {
    const active = state.activeView === view ? ' active' : '';
    return '<div class="nav-item' + active + '" data-view="' + view + '">' +
      icon + '<span class="nav-item-label">' + label + '</span>' + (badge || '') + '</div>';
  }

  function renderSidebar() {
    const cc = catCounts();
    const catIcons = { Users: I.users, Flows: I.flow, Fields: I.fields, Permissions: I.lock, Validation: I.check };

    let nav = navItem('dashboard', I.grid, 'Dashboard', '');
    nav += '<div class="nav-section-label">CHECKS</div>';
    CATEGORIES.forEach(cat => {
      const info = cc[cat];
      const bcls = info.critical ? 'has-critical' : (info.warning ? 'has-warning' : '');
      const badge = '<span class="nav-badge ' + bcls + '">' + info.total + '</span>';
      nav += navItem(cat, catIcons[cat], cat, badge);
    });
    nav += '<div class="nav-section-label">TOOLS</div>';
    nav += navItem('activity', I.clock, 'Activity Log', '');
    nav += '<div class="nav-divider"></div>';

    let bottom = navItem('settings', I.cog, 'Settings', '');
    if (state.activeOrg) {
      bottom += '<div class="nav-item danger" id="disconnectBtn">' +
        I.logout + '<span class="nav-item-label">Disconnect Org</span></div>';
    }

    return '<aside class="sidebar">' +
      '<div class="sidebar-logo">' +
        '<div class="sidebar-logo-icon">' + I.shieldWh + '</div>' +
        '<span class="sidebar-logo-text">OrgScan</span>' +
      '</div>' +
      '<nav class="sidebar-nav">' + nav + '</nav>' +
      '<div class="sidebar-bottom">' + bottom + '</div>' +
      '</aside>';
  }

  // ================================================================
  // TOPBAR
  // ================================================================
  function renderTopbar() {
    const orgBadge = state.activeOrg
      ? '<div class="org-badge"><span class="org-badge-dot"></span><span>' +
          esc(state.activeOrg.username || state.activeOrg.org_id) + '</span></div>'
      : '';

    const right = state.activeOrg
      ? '<button class="btn btn-primary btn-sm" id="scanNowBtn">Run Scan</button>' +
        '<button class="btn btn-secondary btn-sm" id="exportPdfBtn">' + I.filePdf + ' PDF</button>'
      : '<button class="btn btn-primary" id="connectOrgBtn">Connect Org</button>';

    return '<div class="topbar">' +
      '<div class="topbar-left">' +
        '<button class="hamburger">' + I.menu + '</button>' +
        '<span class="topbar-app-name">OrgScan</span>' +
      '</div>' +
      '<div class="topbar-center">' + orgBadge + '</div>' +
      '<div class="topbar-right">' + right + '</div>' +
      '</div>';
  }

  // ================================================================
  // DASHBOARD
  // ================================================================
  function metricCard(icon, iconCls, numCls, val, label, trend) {
    return '<div class="metric-card">' +
      '<div class="metric-icon ' + iconCls + '">' + icon + '</div>' +
      '<div class="metric-body">' +
        '<div class="metric-num ' + numCls + '">' + val + '</div>' +
        '<div class="metric-label">' + label + '</div>' +
        (trend || '') +
      '</div></div>';
  }

  function barRow(label, pct, fillCls, count, labelStyle) {
    return '<div class="bar-row">' +
      '<div class="bar-label"' + (labelStyle ? ' style="' + labelStyle + '"' : '') + '>' + label + '</div>' +
      '<div class="bar-track"><div class="bar-fill ' + fillCls + '" style="width:' + pct + '%"></div></div>' +
      '<div class="bar-count">' + count + '</div></div>';
  }

  function renderDashboard() {
    const { findings, score } = state;
    const cnt = { Critical: 0, Warning: 0, Info: 0 };
    findings.forEach(f => { if (cnt[f.severity] !== undefined) cnt[f.severity]++; });
    const total = findings.length;
    const errHtml = state.error ? '<div class="inline-error">' + esc(state.error) + '</div>' : '';

    const hdr = '<div class="page-header">' +
      '<div><div class="page-title">Dashboard</div><div class="page-subtitle">Org health overview</div></div>' +
      (!state.activeOrg ? '<button class="btn btn-primary" id="connectOrgBtn2">Connect Salesforce Org</button>' : '') +
      '</div>';

    if (total === 0 && score == null) {
      return '<div class="content">' + errHtml + hdr +
        '<div class="card"><div class="card-body"><div class="empty-state">' +
        '<div class="empty-state-icon">' + I.shieldSm + '</div>' +
        '<p>Connect an org and run a scan to see your health dashboard.</p>' +
        '</div></div></div></div>';
    }

    const scoreTrend = score != null
      ? '<div class="metric-trend ' + (score >= 70 ? 'up' : 'down') + '">' +
          (score >= 70 ? '&#9650; Good' : '&#9660; Needs attention') + '</div>'
      : '';

    const metrics = '<div class="metric-cards">' +
      metricCard(I.shieldSm, 'score-icon',    'score-color',    score != null ? score : '&mdash;', 'Org Health Score',   scoreTrend) +
      metricCard(I.alertSm,  'critical-icon', 'critical-color', cnt.Critical,  'Critical Findings', '') +
      metricCard(I.alertSm,  'warning-icon',  'warning-color',  cnt.Warning,   'Warnings',          '') +
      metricCard(I.infoSm,   'info-icon',     'info-color',     cnt.Info,      'Informational',     '') +
      '</div>';

    const cc = catCounts();
    const maxV = Math.max(1, ...Object.values(cc).map(c => c.total));
    const catBars = CATEGORIES.map(cat => {
      const info = cc[cat];
      const pct  = Math.round(info.total / maxV * 100);
      const fc   = info.critical ? 'critical' : (info.warning ? 'warning' : 'mixed');
      return barRow(cat, pct, fc, info.total, '');
    }).join('');

    const sevData = [
      { l: 'Critical', c: 'critical', v: cnt.Critical, col: 'var(--danger)' },
      { l: 'Warning',  c: 'warning',  v: cnt.Warning,  col: '#d97706'       },
      { l: 'Info',     c: 'info',     v: cnt.Info,     col: 'var(--info)'   },
    ];
    const sevBars = sevData.map(r => barRow(r.l, total ? Math.round(r.v / total * 100) : 0, r.c, r.v, 'color:' + r.col)).join('');

    const twoCol = '<div class="two-col">' +
      '<div class="card">' +
        '<div class="card-header"><span class="card-title">Findings by Category</span><span style="font-size:12px;color:var(--text-muted)">' + total + ' total</span></div>' +
        '<div class="card-body"><div class="bar-chart">' + catBars + '</div></div>' +
      '</div>' +
      '<div class="card">' +
        '<div class="card-header"><span class="card-title">Severity Breakdown</span></div>' +
        '<div class="card-body"><div class="bar-chart">' + sevBars + '</div></div>' +
      '</div></div>';

    const recent = findings.slice(0, 10);
    const tRows = recent.length === 0
      ? '<tr><td colspan="5" style="padding:40px;text-align:center;color:var(--text-muted)">No findings yet &mdash; run a scan to get started.</td></tr>'
      : recent.map(f =>
          '<tr><td>' + esc(f.category) + '</td>' +
          '<td>' + severityBadge(f.severity) + '</td>' +
          '<td><div class="cell-title">' + esc(f.title) + '</div><div class="cell-detail">' + esc(f.detail) + '</div></td>' +
          '<td class="muted">' + esc(f.recommendation) + '</td>' +
          '<td><button class="btn btn-secondary btn-sm" onclick="OrgScan.navigate(\'' + esc(f.category) + '\')">View</button></td></tr>'
        ).join('');

    const recentTbl = '<div class="full-col card">' +
      '<div class="card-header"><span class="card-title">Recent Findings</span>' +
      (findings.length > 10 ? '<span style="font-size:12px;color:var(--text-muted)">Showing 10 of ' + findings.length + '</span>' : '') +
      '</div>' +
      '<div class="table-wrapper"><table class="dash-table">' +
        '<thead><tr><th>Category</th><th>Severity</th><th>Title</th><th>Recommendation</th><th>Action</th></tr></thead>' +
        '<tbody>' + tRows + '</tbody>' +
      '</table></div></div>';

    return '<div class="content">' + errHtml + hdr + metrics + twoCol + recentTbl + '</div>';
  }

  // ================================================================
  // CATEGORY VIEW
  // ================================================================
  function renderCategory(cat) {
    const catFindings = state.findings.filter(f => f.category === cat);
    const filt   = state['filter_' + cat] || 'All';
    const filtered = filt === 'All' ? catFindings : catFindings.filter(f => f.severity === filt);
    const isFlows = cat === 'Flows';
    const catIcons = { Users: I.users, Flows: I.flow, Fields: I.fields, Permissions: I.lock, Validation: I.check };

    const pills = ['All', 'Critical', 'Warning', 'Info', 'Resolved'].map(s => {
      const cnt = s === 'All' ? catFindings.length : catFindings.filter(f => f.severity === s).length;
      return '<button class="pill-tab' + (filt === s ? ' active' : '') + '" data-cat="' + cat + '" data-sev="' + s + '">' +
        s + ' <span class="pill-count">' + cnt + '</span></button>';
    }).join('');

    const cols = isFlows ? 5 : 4;
    const rows = filtered.length === 0
      ? '<tr><td colspan="' + cols + '" style="padding:40px;text-align:center;color:var(--text-muted)">No ' +
          (filt === 'All' ? '' : filt + ' ') + 'findings in ' + cat + '.</td></tr>'
      : filtered.map(f => {
          let flowHtml = '';
          if (isFlows) {
            if (f.flow_api_name && f.severity !== 'Resolved') {
              flowHtml =
                '<div style="display:flex;gap:6px;flex-wrap:wrap">' +
                  '<button class="btn btn-secondary btn-sm" data-action="genDesc" data-flow="' + esc(f.flow_api_name) + '">' +
                    I.sparkle + ' AI Description' +
                  '</button>' +
                '</div>' +
                '<div class="desc-area" id="desc-' + esc(f.flow_api_name) + '" style="display:none">' +
                  '<textarea id="desc-text-' + esc(f.flow_api_name) + '" placeholder="AI-generated description will appear here\u2026"></textarea>' +
                  '<div class="desc-actions">' +
                    '<button class="btn btn-success btn-sm" onclick="OrgScan.writeDesc(\'' + esc(f.flow_api_name) + '\')">' +
                      I.pen + ' Write to Org' +
                    '</button>' +
                    '<button class="btn btn-secondary btn-sm" onclick="OrgScan.cancelDesc(\'' + esc(f.flow_api_name) + '\')">Cancel</button>' +
                  '</div>' +
                '</div>';
            } else if (f.severity === 'Resolved') {
              flowHtml = '<span style="color:var(--success);font-weight:700">\u2713 Resolved</span>';
            }
          }
          return '<tr>' +
            '<td>' + severityBadge(f.severity) + '</td>' +
            '<td class="cell-title">' + esc(f.title) + '</td>' +
            '<td class="muted">' + esc(f.detail) + '</td>' +
            '<td class="muted">' + esc(f.recommendation) + '</td>' +
            (isFlows ? '<td>' + flowHtml + '</td>' : '') +
            '</tr>';
        }).join('');

    const thExtra = isFlows ? '<th>Actions</th>' : '';
    return '<div class="content">' +
      (state.error ? '<div class="inline-error">' + esc(state.error) + '</div>' : '') +
      '<div class="page-header"><div>' +
        '<div class="page-title">' + (catIcons[cat] || '') + ' ' + cat + '</div>' +
        '<div class="page-subtitle">' + catFindings.length + ' finding' + (catFindings.length !== 1 ? 's' : '') + ' in this category</div>' +
      '</div></div>' +
      '<div class="pill-tabs">' + pills + '</div>' +
      '<div class="card"><div class="table-wrapper"><table class="dash-table">' +
        '<thead><tr><th>Severity</th><th>Title</th><th>Detail</th><th>Recommendation</th>' + thExtra + '</tr></thead>' +
        '<tbody id="cat-table-body">' + rows + '</tbody>' +
      '</table></div></div>' +
      '</div>';
  }

  // ================================================================
  // ACTIVITY LOG
  // ================================================================
  function renderActivity() {
    const log = state.activityLog;
    const rows = log.length === 0
      ? '<tr><td colspan="5" style="padding:40px;text-align:center;color:var(--text-muted)">No activity recorded yet.</td></tr>'
      : log.map(e => {
          const st = (e.status || '').toLowerCase();
          const scls = st === 'success' ? 'success' : (st === 'error' ? 'error' : 'pending');
          return '<tr>' +
            '<td class="cell-title">' + esc(e.user || e.username || '&mdash;') + '</td>' +
            '<td>' + esc(e.action || '&mdash;') + '</td>' +
            '<td class="muted">' + esc(e.date || e.timestamp || '&mdash;') + '</td>' +
            '<td class="muted">' + esc(e.ip || e.ip_address || '&mdash;') + '</td>' +
            '<td><span class="status-badge ' + scls + '">' + esc(e.status || 'OK') + '</span></td>' +
            '</tr>';
        }).join('');

    return '<div class="content">' +
      (state.error ? '<div class="inline-error">' + esc(state.error) + '</div>' : '') +
      '<div class="page-header"><div>' +
        '<div class="page-title">Activity Log</div>' +
        '<div class="page-subtitle">Recent org activity and audit trail</div>' +
      '</div><button class="btn btn-secondary btn-sm" id="refreshActivityBtn">Refresh</button></div>' +
      '<div class="card"><div class="table-wrapper"><table class="dash-table">' +
        '<thead><tr><th>User</th><th>Action</th><th>Date / Time</th><th>IP Address</th><th>Status</th></tr></thead>' +
        '<tbody>' + rows + '</tbody>' +
      '</table></div></div>' +
      '</div>';
  }

  // ================================================================
  // CONNECT SCREEN
  // ================================================================
  function renderConnectScreen() {
    return '<div class="main-area" style="flex:1">' + renderTopbar() +
      '<div class="connect-screen"><div class="connect-card">' +
        '<div class="connect-logo">' + I.shieldWh + '</div>' +
        '<div class="connect-title">Welcome to OrgScan</div>' +
        '<div class="connect-desc">Connect your Salesforce org to scan for security issues, inactive flows, missing field descriptions, permission gaps, and more.</div>' +
        '<button class="btn btn-primary connect-btn" id="connectOrgBtn">Connect Salesforce Org</button>' +
      '</div></div>' +
      '</div>';
  }

  // ================================================================
  // SETTINGS (stub)
  // ================================================================
  function renderSettings() {
    return '<div class="content">' +
      '<div class="page-header"><div>' +
        '<div class="page-title">Settings</div>' +
        '<div class="page-subtitle">Manage your OrgScan configuration</div>' +
      '</div></div>' +
      '<div class="card"><div class="card-body empty-state" style="padding:60px 40px">' +
        '<div class="empty-state-icon">' + I.cog + '</div>' +
        '<p>Settings coming soon.</p>' +
      '</div></div></div>';
  }

  // ================================================================
  // MAIN RENDER
  // ================================================================
  function render() {
    const app = document.getElementById('app');
    if (!app) return;

    if (!state.activeOrg && state.orgs.length === 0) {
      app.innerHTML = renderConnectScreen();
      bindEvents();
      return;
    }

    const v = state.activeView;
    let body = '';
    if      (v === 'dashboard')          body = renderDashboard();
    else if (CATEGORIES.includes(v))     body = renderCategory(v);
    else if (v === 'activity')           body = renderActivity();
    else if (v === 'settings')           body = renderSettings();
    else                                 body = renderDashboard();

    app.innerHTML = renderSidebar() +
      '<div class="main-area">' + renderTopbar() + body + '</div>';
    bindEvents();
  }

  // ================================================================
  // EVENT BINDING
  // ================================================================
  function bindEvents() {
    document.querySelectorAll('.nav-item[data-view]').forEach(el => {
      el.addEventListener('click', () => navigate(el.dataset.view));
    });

    const disco = document.getElementById('disconnectBtn');
    if (disco) disco.addEventListener('click', disconnectOrg);

    document.querySelectorAll('#connectOrgBtn, #connectOrgBtn2').forEach(b => {
      b.addEventListener('click', connectOrg);
    });

    const scanBtn = document.getElementById('scanNowBtn');
    if (scanBtn) scanBtn.addEventListener('click', runScan);

    const pdfBtn = document.getElementById('exportPdfBtn');
    if (pdfBtn) pdfBtn.addEventListener('click', exportPdf);

    const refreshBtn = document.getElementById('refreshActivityBtn');
    if (refreshBtn) refreshBtn.addEventListener('click', loadActivity);

    document.querySelectorAll('.pill-tab[data-sev]').forEach(b => {
      b.addEventListener('click', () => {
        state['filter_' + b.dataset.cat] = b.dataset.sev;
        render();
      });
    });

    const ctb = document.getElementById('cat-table-body');
    if (ctb) {
      ctb.addEventListener('click', e => {
        const btn = e.target.closest('[data-action]');
        if (btn && btn.dataset.action === 'genDesc') generateDesc(btn.dataset.flow, btn);
      });
    }
  }

  // ================================================================
  // API — ORGS
  // ================================================================
  async function loadOrgs() {
    try {
      const orgs = await fetch(API + '/orgs').then(r => r.json());
      state.orgs = orgs || [];
      if (state.orgs.length > 0 && !state.activeOrg) state.activeOrg = state.orgs[0];
    } catch (e) {
      state.orgs = [];
    }
  }

  async function connectOrg() {
    try {
      const r = await fetch(API + '/orgs/connect', { method: 'POST' }).then(r => r.json());
      window.open(r.auth_url, '_blank', 'width=600,height=700');
    } catch (e) {
      showToast('Failed to connect — check server', 'error');
    }
  }

  async function disconnectOrg() {
    if (!state.activeOrg) return;
    if (!confirm('Disconnect ' + (state.activeOrg.username || state.activeOrg.org_id) + '?')) return;
    try {
      await fetch(API + '/orgs/' + state.activeOrg.org_id, { method: 'DELETE' });
      state.activeOrg = null;
      state.findings  = [];
      state.score     = null;
      await loadOrgs();
      render();
      showToast('Org disconnected');
    } catch (e) {
      showToast('Failed to disconnect', 'error');
    }
  }

  // ================================================================
  // API — SCAN
  // ================================================================
  async function runScan() {
    if (!state.activeOrg) { showToast('Connect an org first', 'error'); return; }
    const btn = document.getElementById('scanNowBtn');
    if (btn) { btn.disabled = true; btn.innerHTML = '<span class="spinner"></span> Scanning\u2026'; }
    state.error = null;
    showToast('Running scan\u2026');
    try {
      const r = await fetch(API + '/scan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ org_id: state.activeOrg.org_id }),
      }).then(r => r.json());
      state.findings   = r.findings || [];
      state.score      = r.score;
      state.activeView = 'dashboard';
      render();
      showToast('Scan complete', 'success');
    } catch (e) {
      state.error = 'Scan failed \u2014 please try again.';
      render();
      showToast('Scan failed', 'error');
    }
  }

  // ================================================================
  // API — AI DESCRIPTION
  // ================================================================
  async function generateDesc(flowApiName, btn) {
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner spinner-dark"></span> Generating\u2026';
    try {
      const r = await fetch(API + '/flows/' + flowApiName + '/describe', { method: 'POST' }).then(r => r.json());
      if (r.detail) { showToast('Error: ' + r.detail, 'error'); return; }
      const ta = document.getElementById('desc-text-' + flowApiName);
      const da = document.getElementById('desc-' + flowApiName);
      if (ta) ta.value = r.description || '';
      if (da) da.style.display = 'block';
      btn.style.display = 'none';
    } catch (e) {
      showToast('Failed to generate description', 'error');
    } finally {
      btn.disabled = false;
      if (btn.innerHTML.indexOf('Generating') !== -1) btn.innerHTML = I.sparkle + ' AI Description';
    }
  }

  async function writeDesc(flowApiName) {
    const ta = document.getElementById('desc-text-' + flowApiName);
    if (!ta) return;
    const description = ta.value.trim();
    if (!description) { showToast('Description cannot be empty', 'error'); return; }
    try {
      const r = await fetch(API + '/flows/' + flowApiName + '/write-description', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ description }),
      }).then(r => r.json());
      if (r.status === 'ok' || r.success) {
        const f = state.findings.find(f => f.flow_api_name === flowApiName && f.severity !== 'Resolved');
        if (f) f.severity = 'Resolved';
        render();
        showToast('Description written to Salesforce', 'success');
      } else {
        showToast('Error: ' + (r.detail || 'Unknown error'), 'error');
      }
    } catch (e) {
      showToast('Failed to write description', 'error');
    }
  }

  function cancelDesc(flowApiName) {
    const a = document.getElementById('desc-' + flowApiName);
    if (a) a.style.display = 'none';
  }

  // ================================================================
  // API — PDF EXPORT
  // ================================================================
  async function exportPdf() {
    const clientName = prompt('Enter client name for the report:');
    if (!clientName) return;
    const btn = document.getElementById('exportPdfBtn');
    if (btn) { btn.disabled = true; btn.textContent = 'Generating\u2026'; }
    showToast('Generating PDF\u2026');
    try {
      const resp = await fetch(API + '/report', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ client_name: clientName }),
      });
      if (!resp.ok) { showToast('PDF generation failed', 'error'); return; }
      const blob = await resp.blob();
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement('a');
      a.href     = url;
      a.download = 'orgscan-' + clientName + '.pdf';
      a.click();
      URL.revokeObjectURL(url);
      showToast('PDF downloaded', 'success');
    } catch (e) {
      showToast('PDF generation failed', 'error');
    } finally {
      if (btn) { btn.disabled = false; btn.innerHTML = I.filePdf + ' PDF'; }
    }
  }

  // ================================================================
  // API — ACTIVITY LOG
  // ================================================================
  async function loadActivity() {
    try {
      const r = await fetch(API + '/activity').then(r => r.json());
      state.activityLog = Array.isArray(r) ? r : (r.activity || r.log || []);
    } catch (e) {
      state.activityLog = [];   // endpoint may not exist yet — graceful empty state
    }
    render();
  }

  // ================================================================
  // INIT
  // ================================================================
  async function init() {
    render();   // immediate skeleton

    await loadOrgs();

    try {
      const cached = await fetch(API + '/findings').then(r => r.json());
      if (cached.findings && cached.findings.length > 0) {
        state.findings = cached.findings;
        state.score    = cached.score;
      }
    } catch (e) { /* no cached findings — ignore */ }

    render();
  }

  // ================================================================
  // PUBLIC API  (called by inline onclick attrs in dynamic HTML)
  // ================================================================
  window.OrgScan = { navigate, writeDesc, cancelDesc, generateDesc };

  init();

}());
