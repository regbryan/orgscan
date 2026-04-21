/**
 * OrgScan — DashStack UI
 * IIFE module pattern. State object drives all rendering.
 * innerHTML is used intentionally for SPA templating.
 * All user-supplied data passes through esc() before insertion.
 */
(function () {
  'use strict';

  const API = '';
  const CATEGORIES = ['Org Config', 'Licenses', 'Users', 'Flows', 'Fields', 'Permissions', 'Validation', 'Layouts', 'Analytics', 'Activity', 'Data Activity', 'Integrations', 'Email', 'Data Quality'];

  // ================================================================
  // STATE
  // ================================================================
  const state = {
    activeOrg: null,
    orgs: [],
    findings: [],
    score: null,
    activeView: 'dashboard',
    activityLog: null,
    dataActivityLog: null,
    activeFinding: null,
    dashPage: 0,
    error: null,
    lastScanTime: null,
    historyTab: null,
    // Duplicates
    dupObjects: null,        // fetched from /duplicates/objects
    dupTab: 'setup',         // 'setup' | 'results' | 'overview'
    dupObjectName: '',
    dupMatchFields: [],
    dupMode: 'custom',
    dupResults: null,        // { groups, total_groups, total_records, records_scanned }
    dupExpanded: {},         // group_id → bool
    dupLoading: false,
    dupScanHistory: {},      // key → { label, type, total_groups, total_records, records_scanned, scannedAt }
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
    layout:   '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="9" y1="21" x2="9" y2="9"/></svg>',
    chart:    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>',
    export:     '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>',
    db:         '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14a9 3 0 0 0 18 0V5"/><path d="M3 12a9 3 0 0 0 18 0"/></svg>',
    extLink:    '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>',
    merge:      '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="18" cy="18" r="3"/><circle cx="6" cy="6" r="3"/><path d="M6 21V9a9 9 0 0 0 9 9"/></svg>',
    trash:      '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/></svg>',
    chevDown:   '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>',
    chevUp:     '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="18 15 12 9 6 15"/></svg>',
    server:     '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="2" width="20" height="8" rx="2"/><rect x="2" y="14" width="20" height="8" rx="2"/><line x1="6" y1="6" x2="6.01" y2="6"/><line x1="6" y1="18" x2="6.01" y2="18"/></svg>',
    tag:        '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/></svg>',
    link:       '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>',
    mail:       '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>',
    database:   '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>',
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

  // Severity → left-border accent color for table rows
  const SEV_ROW_COLOR = {
    Critical: '#f87171',
    Warning:  '#fbbf24',
    Info:     '#6C8EFF',
    Resolved: '#34d399',
  };

  // Build the title cell: title is a link when a direct SF URL exists,
  // with a one-line recommendation hint underneath.
  function titleCell(f, globalIdx) {
    const sfUrl = getSfUrl(f);
    const detailLines = (f.detail || '').split('\n').map(s => s.trim()).filter(Boolean);
    const hasExtra = detailLines.length > 1;

    // Title — link if we have a direct URL, plain text otherwise
    const titleHtml = sfUrl
      ? '<a href="' + esc(sfUrl) + '" target="_blank" rel="noopener" class="finding-title-link">' +
          esc(f.title) + ' ' + I.extLink +
        '</a>'
      : '<span class="finding-title-text">' + esc(f.title) + '</span>';

    // First detail line always shown; expand toggle when multi-line
    const detailPreview = detailLines.length > 0
      ? '<div class="finding-detail-preview">' + esc(detailLines[0]) +
          (hasExtra
            ? ' <button class="finding-expand-btn" data-idx="' + globalIdx + '" title="Show full detail">+' + (detailLines.length - 1) + ' more</button>'
            : '') +
        '</div>'
      : '';

    // Expanded detail lines (hidden by default)
    const expandedDetail = hasExtra
      ? '<ul class="finding-detail-extra" id="fde-' + globalIdx + '" style="display:none">' +
          detailLines.slice(1).map(l => '<li>' + esc(l) + '</li>').join('') +
        '</ul>'
      : '';

    // Recommendation hint — always visible inline
    const recHtml = f.recommendation
      ? '<div class="finding-rec-hint">' + esc(f.recommendation) + '</div>'
      : '';

    return '<td class="finding-title-cell">' +
      titleHtml +
      detailPreview +
      expandedDetail +
      recHtml +
    '</td>';
  }

  // ================================================================
  // SALESFORCE DEEP LINKS
  // ================================================================
  function getSfUrl(f) {
    // Prefer the precise record-level link computed by the backend
    if (f && f.link) return f.link;
    const base = (state.activeOrg || {}).instance_url;
    if (!base || !f) return null;

    // Pull object name from "ObjectName.something" pattern in title or first detail line
    function objFrom(str) {
      if (!str) return null;
      const m = str.match(/^([A-Za-z][A-Za-z0-9_]*)[\.\s—]/);
      return m ? m[1] : null;
    }
    function omUrl(obj, sub) {
      return obj
        ? base + '/lightning/setup/ObjectManager/' + encodeURIComponent(obj) + '/' + sub + '/view'
        : base + '/lightning/setup/ObjectManager/home';
    }

    const firstDetail = (f.detail || '').split('\n')[0];

    switch (f.category) {
      case 'Users':
        return base + '/lightning/setup/ManageUsers/home';

      case 'Flows':
        return base + '/lightning/setup/Flows/home';

      case 'Fields': {
        // title: "Account.MyField__c — no references found"
        const obj = objFrom(f.title) || objFrom(firstDetail);
        return omUrl(obj, 'FieldsAndRelationships');
      }

      case 'Permissions':
        return (f.detail || '').startsWith('Profile:')
          ? base + '/lightning/setup/Profiles/home'
          : base + '/lightning/setup/PermSets/home';

      case 'Validation': {
        // detail: "Account.RuleName — no description"
        const obj = objFrom(firstDetail);
        return omUrl(obj, 'ValidationRules');
      }

      case 'Layouts': {
        // detail lines: "Account — Layout Name [RecordPage]"
        const obj = objFrom(firstDetail);
        if (!obj) return base + '/lightning/setup/FlexiPageList/home';
        // If it's a Lightning page finding, go to FlexiPage list
        if ((f.title || '').toLowerCase().includes('lightning')) {
          return base + '/lightning/setup/FlexiPageList/home';
        }
        return omUrl(obj, 'PageLayouts');
      }

      case 'Analytics':
        return base + '/lightning/setup/Reports/home';

      case 'Activity':
        return base + '/lightning/setup/LoginHistory/home';

      case 'Data Activity':
        return base + '/lightning/setup/AuditTrail/home';

      default:
        return base + '/lightning/setup/SetupOneHome/home';
    }
  }

  function sfLink(f, label, cls) {
    const url = getSfUrl(f);
    if (!url) return '';
    return '<a href="' + esc(url) + '" target="_blank" rel="noopener" class="btn ' + (cls || 'btn-secondary') + ' btn-sm sf-link">' +
      (label || (I.extLink + ' Open in Org')) +
    '</a>';
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

  function showFinding(idx) {
    state.activeFinding = state.findings[idx] || null;
    renderModal();
  }

  function closeModal() {
    state.activeFinding = null;
    const m = document.getElementById('finding-modal');
    if (m) m.remove();
  }

  function formatDetailHtml(detail) {
    if (!detail) return '';
    const lines = detail.split('\n').map(s => s.trim()).filter(Boolean);
    if (lines.length <= 1) {
      return '<p class="modal-detail-text">' + esc(detail) + '</p>';
    }
    return '<ul class="modal-detail-list">' +
      lines.map(l => '<li>' + esc(l) + '</li>').join('') +
      '</ul>';
  }

  function renderModal() {
    const existing = document.getElementById('finding-modal');
    if (existing) existing.remove();
    const f = state.activeFinding;
    if (!f) return;
    const div = document.createElement('div');
    div.id = 'finding-modal';
    div.className = 'modal-overlay';
    const sfUrl = getSfUrl(f);
    const sfBtn = sfUrl
      ? '<a href="' + esc(sfUrl) + '" target="_blank" rel="noopener" class="btn btn-primary btn-sm">' +
          I.extLink + ' Open in Salesforce' +
        '</a>'
      : '';
    const activityBtn = f.category === 'Activity'
      ? '<button class="btn btn-secondary btn-sm" id="modalActionBtn">View Activity Log &rarr;</button>'
      : '';
    const actionBtn = (sfBtn || activityBtn)
      ? '<div class="modal-section" style="display:flex;gap:8px;flex-wrap:wrap">' + sfBtn + activityBtn + '</div>'
      : '';
    const recCallout = f.recommendation
      ? '<div class="modal-rec-callout">' +
          '<div class="modal-rec-callout-label">What to do</div>' +
          '<p class="modal-rec-callout-text">' + esc(f.recommendation) + '</p>' +
        '</div>'
      : '';

    // AI Description section for flows missing descriptions
    var aiSection = '';
    if (f.flow_api_name && f.severity !== 'Resolved') {
      aiSection =
        '<div class="modal-section">' +
          '<div class="modal-section-label">AI Description</div>' +
          '<p style="color:var(--text-muted);font-size:13px;margin:0 0 10px">Read this flow and generate a plain-English description of what it does.</p>' +
          '<div style="display:flex;gap:8px;flex-wrap:wrap">' +
          '<button class="btn btn-secondary btn-sm" id="modalGenDescBtn" style="display:inline-flex;align-items:center;gap:6px">' +
            I.sparkle + ' Generate Description' +
          '</button>' +
          '<button class="btn btn-primary btn-sm" id="modalFlowPdfBtn" style="display:inline-flex;align-items:center;gap:6px">' +
            I.filePdf + ' Download Flow PDF' +
          '</button>' +
          '</div>' +
          '<div id="modalDescArea" style="display:none;margin-top:12px">' +
            '<textarea id="modalDescText" style="width:100%;min-height:180px;border-radius:8px;border:1px solid var(--border);padding:10px;font-size:13px;font-family:inherit;resize:vertical" placeholder="AI-generated description and recommendations will appear here\u2026"></textarea>' +
            '<div style="display:flex;gap:8px;margin-top:8px">' +
              '<button class="btn btn-success btn-sm" id="modalWriteDescBtn">' + I.pen + ' Write to Salesforce</button>' +
              '<button class="btn btn-secondary btn-sm" id="modalCancelDescBtn">Cancel</button>' +
            '</div>' +
          '</div>' +
        '</div>';
    }

    div.innerHTML =
      '<div class="modal-card" role="dialog" aria-modal="true">' +
        '<div class="modal-header">' +
          '<div>' +
            severityBadge(f.severity) +
            '<span class="modal-category">' + esc(f.category) + '</span>' +
          '</div>' +
          '<button class="modal-close" id="modalCloseBtn" aria-label="Close">&times;</button>' +
        '</div>' +
        '<h3 class="modal-title">' + esc(f.title) + '</h3>' +
        recCallout +
        '<div class="modal-section">' +
          '<div class="modal-section-label">Detail</div>' +
          formatDetailHtml(f.detail) +
        '</div>' +
        actionBtn +
        aiSection +
      '</div>';
    document.body.appendChild(div);
    div.addEventListener('click', e => { if (e.target === div) closeModal(); });
    document.getElementById('modalCloseBtn').addEventListener('click', closeModal);
    const actBtn = document.getElementById('modalActionBtn');
    if (actBtn) actBtn.addEventListener('click', () => { closeModal(); navigate('activity'); });

    // Wire up AI description buttons in the modal
    const genBtn = document.getElementById('modalGenDescBtn');
    if (genBtn) {
      genBtn.addEventListener('click', async function () {
        genBtn.innerHTML = I.sparkle + ' Generating\u2026';
        genBtn.disabled = true;
        try {
          var r = await fetch(API + '/flows/' + f.flow_api_name + '/describe', { method: 'POST' });
          var data = await r.json();
          if (data.description) {
            document.getElementById('modalDescArea').style.display = 'block';
            document.getElementById('modalDescText').value = data.description;
            genBtn.style.display = 'none';
          } else {
            showToast(data.detail || 'Failed to generate description', 'error');
            genBtn.innerHTML = I.sparkle + ' Generate Description';
            genBtn.disabled = false;
          }
        } catch (e) {
          showToast('Failed to generate description', 'error');
          genBtn.innerHTML = I.sparkle + ' Generate Description';
          genBtn.disabled = false;
        }
      });
    }
    var writeBtn = document.getElementById('modalWriteDescBtn');
    if (writeBtn) {
      writeBtn.addEventListener('click', async function () {
        var desc = document.getElementById('modalDescText').value.trim();
        if (!desc) return;
        try {
          var r = await fetch(API + '/flows/' + f.flow_api_name + '/write-description', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ description: desc })
          });
          var data = await r.json();
          if (data.status === 'ok') {
            showToast('Description written to Salesforce!', 'success');
            f.severity = 'Resolved';
            closeModal();
            render();
          } else {
            showToast(data.detail || 'Failed to write description', 'error');
          }
        } catch (e) {
          showToast('Failed to write description', 'error');
        }
      });
    }
    var cancelDescBtn = document.getElementById('modalCancelDescBtn');
    if (cancelDescBtn) {
      cancelDescBtn.addEventListener('click', function () {
        document.getElementById('modalDescArea').style.display = 'none';
        var genBtn2 = document.getElementById('modalGenDescBtn');
        if (genBtn2) { genBtn2.style.display = ''; genBtn2.innerHTML = I.sparkle + ' Generate Description'; genBtn2.disabled = false; }
      });
    }

    // Wire up Flow PDF download button
    var pdfBtn = document.getElementById('modalFlowPdfBtn');
    if (pdfBtn) {
      pdfBtn.addEventListener('click', async function () {
        pdfBtn.innerHTML = I.filePdf + ' Generating PDF\u2026';
        pdfBtn.disabled = true;
        try {
          var resp = await fetch(API + '/flows/' + f.flow_api_name + '/document', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ client_name: '' })
          });
          if (!resp.ok) {
            var err = await resp.json();
            showToast(err.detail || 'Failed to generate PDF', 'error');
            pdfBtn.innerHTML = I.filePdf + ' Download Flow PDF';
            pdfBtn.disabled = false;
            return;
          }
          var blob = await resp.blob();
          var url = URL.createObjectURL(blob);
          var a = document.createElement('a');
          a.href = url;
          a.download = 'flow-' + f.flow_api_name + '.pdf';
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          URL.revokeObjectURL(url);
          showToast('Flow PDF downloaded!', 'success');
        } catch (e) {
          showToast('Failed to generate PDF', 'error');
        }
        pdfBtn.innerHTML = I.filePdf + ' Download Flow PDF';
        pdfBtn.disabled = false;
      });
    }
  }

  function navigate(view) {
    state.activeView = view;
    state.error = null;
    if (view === 'activity')       { state.activityLog = null; }
    if (view === 'data-activity')  { state.dataActivityLog = null; }
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
    const total = state.findings.length;
    const critCount = state.findings.filter(f => f.severity === 'Critical').length;
    const findingsBadge = total > 0
      ? '<span class="nav-badge ' + (critCount > 0 ? 'has-critical' : '') + '">' + total + '</span>'
      : '';

    let nav = navItem('dashboard', I.grid, 'Dashboard', '');
    nav += navItem('findings', I.fields, 'Findings', findingsBadge);
    nav += navItem('activity', I.clock, 'History', '');
    nav += navItem('duplicates', I.merge, 'Duplicates', '');
    nav += '<div class="nav-divider"></div>';

    let bottom = navItem('settings', I.cog, 'Settings', '');
    if (state.activeOrg) {
      bottom += '<div class="nav-item danger" id="disconnectBtn">' +
        I.logout + '<span class="nav-item-label">Disconnect Org</span></div>';
    }

    return '<aside class="sidebar">' +
      '<div class="sidebar-logo">' +
        '<div class="sidebar-logo-icon">' + I.shieldWh + '</div>' +
        '<div class="sidebar-logo-text">' +
          '<span class="sidebar-logo-name">OrgScan</span>' +
          '<span class="sidebar-logo-sub">Technical Guardian</span>' +
        '</div>' +
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
        '<button class="btn btn-secondary btn-sm" id="exportPdfBtn">' + I.filePdf + ' PDF</button>' +
        '<button class="btn btn-secondary btn-sm" id="exportCsvBtn">' + I.export + ' CSV</button>'
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

    function gaugeColor(s) {
      if (s >= 75) return '#2F6B3F';
      if (s >= 50) return '#B45309';
      if (s >= 25) return '#B45309';
      return '#9B2C2C';
    }
    function gaugeLabel(s) {
      if (s >= 90) return 'EXCELLENT';
      if (s >= 75) return 'GOOD';
      if (s >= 50) return 'FAIR';
      if (s >= 25) return 'NEEDS WORK';
      return 'CRITICAL';
    }

    // Large gauge for the health card (bigger arc, dark bg)
    function buildLargeGauge(s) {
      const R = 72, cx = 100, cy = 108;
      const col = gaugeColor(s);
      function p2xy(deg, r) {
        const rad = (deg - 90) * Math.PI / 180;
        return { x: +(cx + r * Math.cos(rad)).toFixed(2), y: +(cy + r * Math.sin(rad)).toFixed(2) };
      }
      function arc(startDeg, sweepDeg, r) {
        const s0 = p2xy(startDeg, r);
        const e0 = p2xy(startDeg + sweepDeg, r);
        const lg = sweepDeg > 180 ? 1 : 0;
        return 'M ' + s0.x + ' ' + s0.y + ' A ' + r + ' ' + r + ' 0 ' + lg + ' 1 ' + e0.x + ' ' + e0.y;
      }
      return '<svg class="dash-gauge-svg" viewBox="0 0 200 148" fill="none">' +
        '<path d="' + arc(-130, 260, R) + '" stroke="#D9D4C7" stroke-width="10" stroke-linecap="butt" fill="none"/>' +
        (s > 0 ? '<path d="' + arc(-130, (s / 100) * 260, R) + '" stroke="#1B1C1E" stroke-width="10" stroke-linecap="butt" fill="none"/>' : '') +
        '<text x="' + cx + '" y="' + (cy - 8) + '" text-anchor="middle" class="dash-g-num" fill="#1B1C1E">' + s + '</text>' +
        '<text x="' + cx + '" y="' + (cy + 14) + '" text-anchor="middle" class="dash-g-sub">/ 100</text>' +
        '<text x="' + cx + '" y="' + (cy + 33) + '" text-anchor="middle" class="dash-g-label" fill="' + col + '">' + gaugeLabel(s) + '</text>' +
      '</svg>';
    }

    // Health card (dark navy, large gauge)
    const col = score != null ? gaugeColor(score) : '#6C8EFF';
    const healthCard = '<div class="dash-health-card">' +
      '<div class="dash-health-hdr">OVERALL ORG HEALTH</div>' +
      (score != null ? buildLargeGauge(score) : '<div class="dash-gauge-empty">—</div>') +
      '<div class="dash-health-stats">' +
        '<div class="dash-stat">' +
          '<div class="dash-stat-num">' + total + '</div>' +
          '<div class="dash-stat-lbl">FINDINGS</div>' +
        '</div>' +
        '<div class="dash-stat-div"></div>' +
        '<div class="dash-stat">' +
          '<div class="dash-stat-num" style="color:#f87171">' + cnt.Critical + '</div>' +
          '<div class="dash-stat-lbl">CRITICAL</div>' +
        '</div>' +
      '</div>' +
    '</div>';

    // Critical + Warning metric cards
    const critCard = '<div class="card dash-mc dash-mc-crit">' +
      '<div class="dash-mc-lbl">CRITICAL FINDINGS</div>' +
      '<div class="dash-mc-num">' + String(cnt.Critical).padStart(2, '0') + '</div>' +
      '<div class="dash-mc-foot">' +
        '<span class="dash-mc-icon-wrap">' + I.shieldSm + '</span>' +
        '<span>Requires immediate attention</span>' +
      '</div>' +
    '</div>';

    const warnCard = '<div class="card dash-mc dash-mc-warn">' +
      '<div class="dash-mc-lbl">ACTIVE WARNINGS</div>' +
      '<div class="dash-mc-num">' + String(cnt.Warning).padStart(2, '0') + '</div>' +
      '<div class="dash-mc-foot">' +
        '<span>' + cnt.Info + ' informational</span>' +
      '</div>' +
    '</div>';

    // Category breakdown table
    const cc = catCounts();
    // Get actual severity counts per category for badge display
    const catSevCounts = {};
    CATEGORIES.forEach(c => { catSevCounts[c] = { critical: 0, warning: 0, info: 0 }; });
    findings.forEach(f => {
      if (catSevCounts[f.category]) {
        if (f.severity === 'Critical') catSevCounts[f.category].critical++;
        else if (f.severity === 'Warning') catSevCounts[f.category].warning++;
        else if (f.severity === 'Info') catSevCounts[f.category].info++;
      }
    });

    const catRows = CATEGORIES.map(cat => {
      const info = cc[cat];
      const sc = catSevCounts[cat];
      const statusCol = sc.critical > 0 ? '#fd5454' : sc.warning > 0 ? '#fcbe2d' : info.total > 0 ? '#00b69b' : '#b0b8c4';
      const statusLbl = sc.critical > 0 ? 'Critical' : sc.warning > 0 ? 'Warning' : info.total > 0 ? 'OK' : 'Clear';
      const badges =
        (sc.critical > 0 ? '<span class="dash-cbadge dash-cbadge-crit">' + sc.critical + ' critical</span>' : '') +
        (sc.warning  > 0 ? '<span class="dash-cbadge dash-cbadge-warn">' + sc.warning  + ' warnings</span>' : '') +
        (sc.info     > 0 ? '<span class="dash-cbadge dash-cbadge-info">' + sc.info     + ' info</span>'     : '');
      return '<tr>' +
        '<td class="dash-cat-name">' + cat + '</td>' +
        '<td class="dash-cat-total">' + info.total + '</td>' +
        '<td class="dash-cat-badges">' + (badges || '<span style="color:var(--text-muted);font-size:12px">—</span>') + '</td>' +
        '<td><span class="dash-cat-status"><span class="dash-cat-dot" style="background:' + statusCol + '"></span>' + statusLbl + '</span></td>' +
      '</tr>';
    }).join('');

    const catTable = '<div class="card">' +
      '<div class="card-header">' +
        '<span class="card-title">FINDINGS BY CATEGORY</span>' +
        '<button class="btn btn-secondary btn-sm" onclick="OrgScan.navigate(\'findings\')">View All</button>' +
      '</div>' +
      '<div class="table-wrapper"><table class="dash-cat-table">' +
        '<thead><tr>' +
          '<th>CATEGORY</th><th style="width:60px">TOTAL</th><th>BREAKDOWN</th><th style="width:90px">STATUS</th>' +
        '</tr></thead>' +
        '<tbody>' + catRows + '</tbody>' +
      '</table></div>' +
    '</div>';

    const rightCol = '<div class="dash-right-col">' +
      '<div class="dash-mc-row">' + critCard + warnCard + '</div>' +
      catTable +
    '</div>';

    // Duplicate health widget (only shown if at least one scan has been run)
    const dupHistory = state.dupScanHistory;
    const dupKeys = Object.keys(dupHistory);
    let dupWidget = '';
    if (dupKeys.length > 0) {
      const totalAffected = dupKeys.reduce((s, k) => s + (dupHistory[k].total_records || 0), 0);
      const totalScanned  = dupKeys.reduce((s, k) => s + (dupHistory[k].records_scanned || 0), 0);
      const overallPct = totalScanned > 0 ? ((totalAffected / totalScanned) * 100).toFixed(1) : '0.0';
      const pctNum = parseFloat(overallPct);
      const pctColor = pctNum === 0 ? '#00b69b' : pctNum < 5 ? '#fcbe2d' : '#fd5454';
      const pctLabel = pctNum === 0 ? 'Clean' : pctNum < 5 ? 'Low Risk' : pctNum < 20 ? 'Moderate' : 'High Risk';

      const miniCards = dupKeys.map(k => {
        const h = dupHistory[k];
        const sc = h.records_scanned || 0;
        const aff = h.total_records || 0;
        const p = sc > 0 ? Math.min(100, (aff / sc) * 100) : 0;
        const col = p === 0 ? '#00b69b' : p < 5 ? '#fcbe2d' : '#fd5454';
        return '<div class="dup-mini-row">' +
          '<span class="dup-mini-label">' + esc(h.label) + '</span>' +
          '<div class="dup-mini-bar"><div class="dup-mini-fill" style="width:' + Math.max(p, p > 0 ? 2 : 0) + '%;background:' + col + '"></div></div>' +
          '<span class="dup-mini-pct" style="color:' + col + '">' + p.toFixed(1) + '%</span>' +
        '</div>';
      }).join('');

      dupWidget = '<div class="card dup-dash-widget">' +
        '<div class="card-header">' +
          '<span class="card-title">' + I.merge + ' DUPLICATE HEALTH</span>' +
          '<button class="btn btn-secondary btn-sm" onclick="OrgScan.navigate(\'duplicates\')">View Details</button>' +
        '</div>' +
        '<div class="card-body">' +
          '<div class="dup-dash-summary">' +
            '<div class="dup-dash-pct" style="color:' + pctColor + '">' + overallPct + '%</div>' +
            '<div class="dup-dash-lbl">' +
              '<div class="dup-dash-status" style="color:' + pctColor + '">' + pctLabel + '</div>' +
              '<div style="font-size:12px;color:var(--text-muted)">' + totalAffected + ' of ' + totalScanned + ' records affected</div>' +
            '</div>' +
          '</div>' +
          miniCards +
        '</div>' +
      '</div>';
    }

    return '<div class="content">' + errHtml + hdr +
      '<div class="dash-top-grid">' + healthCard + rightCol + '</div>' +
      (dupWidget ? '<div style="margin-top:20px">' + dupWidget + '</div>' : '') +
    '</div>';
  }

  // ================================================================
  // CATEGORY VIEW
  // ================================================================
  function renderCategory(cat) {
    const catFindings = state.findings.filter(f => f.category === cat);
    const filt   = state['filter_' + cat] || 'All';
    const filtered = filt === 'All' ? catFindings : catFindings.filter(f => f.severity === filt);
    const isFlows = cat === 'Flows';
    const catIcons = { 'Org Config': I.server, Licenses: I.tag, Users: I.users, Flows: I.flow, Fields: I.fields, Permissions: I.lock, Validation: I.check, Layouts: I.layout, Analytics: I.chart, Activity: I.clock, 'Data Activity': I.db, Integrations: I.link, Email: I.mail, 'Data Quality': I.database };

    const pills = ['All', 'Critical', 'Warning', 'Info', 'Resolved'].map(s => {
      const cnt = s === 'All' ? catFindings.length : catFindings.filter(f => f.severity === s).length;
      return '<button class="pill-tab' + (filt === s ? ' active' : '') + '" data-cat="' + cat + '" data-sev="' + s + '">' +
        s + ' <span class="pill-count">' + cnt + '</span></button>';
    }).join('');

    const cols = isFlows ? 4 : 3;
    const rows = filtered.length === 0
      ? '<tr><td colspan="' + cols + '" style="padding:40px;text-align:center;color:var(--text-muted)">No ' +
          (filt === 'All' ? '' : filt + ' ') + 'findings in ' + cat + '.</td></tr>'
      : filtered.map(f => {
          const globalIdx = state.findings.indexOf(f);
          const rowAccent = SEV_ROW_COLOR[f.severity] || 'var(--border-color)';
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
          return '<tr style="border-left:3px solid ' + rowAccent + '">' +
            '<td style="white-space:nowrap;vertical-align:top;padding-top:14px">' + severityBadge(f.severity) + '</td>' +
            titleCell(f, globalIdx) +
            '<td style="white-space:nowrap;text-align:right;vertical-align:top;padding-top:14px">' +
              '<button class="btn btn-secondary btn-sm" onclick="OrgScan.showFinding(' + globalIdx + ')">Details</button>' +
            '</td>' +
            (isFlows ? '<td style="vertical-align:top;padding-top:14px">' + flowHtml + '</td>' : '') +
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
        '<thead><tr><th style="width:80px">Severity</th><th>Finding</th><th style="width:80px"></th>' + thExtra + '</tr></thead>' +
        '<tbody id="cat-table-body">' + rows + '</tbody>' +
      '</table></div></div>' +
      '</div>';
  }

  // ================================================================
  // HISTORY (Login Activity + Data Activity tabs)
  // ================================================================
  function renderActivity() {
    const activeTab = state.historyTab || 'login';

    // Trigger data loads if needed
    if (activeTab === 'login' && !state.activityLog) {
      fetch('/activity')
        .then(r => r.json())
        .then(data => { state.activityLog = data.events || []; render(); })
        .catch(() => { state.activityLog = []; render(); });
    }
    if (activeTab === 'data' && !state.dataActivityLog) {
      fetch('/data-activity?days=90')
        .then(r => r.json())
        .then(data => { state.dataActivityLog = data.events || []; render(); })
        .catch(() => { state.dataActivityLog = []; render(); });
    }

    const tabs = '<div class="pill-tabs" style="margin-bottom:16px">' +
      '<button class="pill-tab' + (activeTab === 'login' ? ' active' : '') + '" data-history-tab="login">Login Activity</button>' +
      '<button class="pill-tab' + (activeTab === 'data'  ? ' active' : '') + '" data-history-tab="data">Data Exports</button>' +
      '<button class="pill-tab' + (activeTab === 'docs'  ? ' active' : '') + '" data-history-tab="docs">Documentation</button>' +
    '</div>';

    let body = '';

    if (activeTab === 'login') {
      if (!state.activityLog) {
        body = '<div class="card"><div class="card-body"><div class="loading-msg">Loading login activity\u2026</div></div></div>';
      } else if (state.activityLog.length === 0) {
        body = '<div class="card"><div class="card-body"><div class="empty-state">' +
          '<div class="empty-state-icon">' + I.clock + '</div>' +
          '<p>No login events found for the last 30 days.</p>' +
        '</div></div></div>';
      } else {
        const rows = state.activityLog.map(e => {
          const ts = e.timestamp ? new Date(e.timestamp) : null;
          const dateStr = ts ? ts.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' }) : '—';
          const timeStr = ts ? ts.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' }) : '';
          const isSuccess = e.status === 'Success';
          const isFailed  = e.status === 'Failed';
          const statusPill = isFailed
            ? '<span class="finding-status-pill" style="background:rgba(253,84,84,0.1);color:#f87171">&#10005; Failed</span>'
            : isSuccess
            ? '<span class="finding-status-pill status-resolved">&#10003; Success</span>'
            : '<span class="finding-status-pill status-open">' + esc(e.status) + '</span>';
          return '<tr>' +
            '<td class="hist-user">' + esc(e.user || '—') + '</td>' +
            '<td class="hist-type"><span class="hist-type-badge">' + esc(e.event_type || '—') + '</span></td>' +
            '<td>' + esc(e.action || '—') + '</td>' +
            '<td>' +
              '<div class="finding-detected-date">' + dateStr + '</div>' +
              (timeStr ? '<div class="finding-detected-time">' + timeStr + '</div>' : '') +
            '</td>' +
            '<td class="hist-ip">' + esc(e.ip_address || '—') + '</td>' +
            '<td>' + statusPill + '</td>' +
          '</tr>';
        }).join('');
        body = '<div class="card"><div class="table-wrapper"><table class="dash-table">' +
          '<thead><tr>' +
            '<th>User</th><th>Type</th><th>Action</th><th>Date / Time</th><th>IP Address</th><th style="text-align:center">Status</th>' +
          '</tr></thead>' +
          '<tbody>' + rows + '</tbody>' +
        '</table></div></div>';
      }
    } else {
      // Data Activity tab
      if (!state.dataActivityLog) {
        body = '<div class="card"><div class="card-body"><div class="loading-msg">Loading data activity\u2026</div></div></div>';
      } else {
        const events  = state.dataActivityLog;
        const exports = events.filter(e => e.event_type === 'Export/Import');
        const batches = events.filter(e => e.event_type === 'Batch Job');
        const shield  = events.filter(e => e.event_type === 'Shield');

        function evtTable(rows, cols, empty) {
          if (!rows.length) return '<div class="empty-state" style="padding:32px;text-align:center;color:var(--text-muted)">' + empty + '</div>';
          return '<div class="table-wrapper"><table class="dash-table">' +
            '<thead><tr>' + cols.map(c => '<th>' + c + '</th>').join('') + '</tr></thead>' +
            '<tbody>' + rows + '</tbody></table></div>';
        }

        const exportRows = exports.map(e => {
          const ts = e.timestamp ? new Date(e.timestamp).toLocaleString() : '—';
          return '<tr><td>' + esc(e.user) + '</td><td>' + esc(e.action) + '</td>' +
            '<td><div class="finding-detected-date">' + ts + '</div></td>' +
            '<td class="hist-ip">' + esc(e.detail || '—') + '</td></tr>';
        }).join('');

        const batchRows = batches.map(e => {
          const ts = e.timestamp ? new Date(e.timestamp).toLocaleString() : '—';
          const hasErr = e.detail && e.detail.toLowerCase().includes('errors:') && !e.detail.includes('Errors: 0');
          return '<tr><td>' + esc(e.user) + '</td><td>' + esc(e.action) + '</td>' +
            '<td><div class="finding-detected-date">' + ts + '</div></td>' +
            '<td class="' + (hasErr ? 'text-danger' : '') + '">' + esc(e.detail || '—') + '</td></tr>';
        }).join('');

        const shieldBanner = shield.length
          ? '<div class="hist-info-banner hist-banner-blue">Salesforce Shield detected &mdash; ' + shield.length + ' event log file(s) available. Download from Setup &rsaquo; Event Log Files.</div>'
          : '<div class="hist-info-banner hist-banner-gray"><strong>Want deeper visibility?</strong> Salesforce Shield Event Monitoring captures row-level data exports and Bulk API operations per user. Not licensed on this org.</div>';

        body =
          '<div class="hist-section-label">Export / Import Events <span class="nav-badge" style="margin-left:6px">' + exports.length + '</span></div>' +
          '<div class="card" style="margin-bottom:20px">' + evtTable(exportRows, ['User', 'Action', 'Date / Time', 'Detail'], 'No data export or import events in the last 90 days.') + '</div>' +
          '<div class="hist-section-label">Batch &amp; Scheduled Jobs <span class="nav-badge" style="margin-left:6px">' + batches.length + '</span></div>' +
          '<div class="card" style="margin-bottom:20px">' + evtTable(batchRows, ['Submitted By', 'Job', 'Date / Time', 'Status'], 'No batch or scheduled Apex jobs found in the last 90 days.') + '</div>' +
          shieldBanner;
      }
    }

    if (activeTab === 'docs') {
      const docs = [
        {
          category: 'Users',
          icon: I.users,
          title: 'Inactive Users',
          desc: 'Users who have never logged in or have not logged in for 90+ days still consume a Salesforce license. OrgScan flags these so you can freeze or deactivate them, recovering license seats and reducing the attack surface.',
          rec: 'Deactivate users inactive 90+ days. Use permission sets instead of profiles to simplify re-enabling if needed.',
        },
        {
          category: 'Flows',
          icon: I.flow,
          title: 'Flow API Version & Descriptions',
          desc: 'Flows built on API versions below 50 may lack modern error handling and are incompatible with newer Flow features. Missing descriptions make flows impossible to audit without opening each one in Flow Builder.',
          rec: 'Open each flagged flow in Flow Builder, upgrade the API version, and use the AI Description button to auto-generate documentation.',
        },
        {
          category: 'Fields',
          icon: I.fields,
          title: 'Unused & Empty Custom Fields',
          desc: 'Custom fields with no data and no metadata references (flows, reports, layouts) are dead weight. They slow down page loads, confuse users, and accumulate tech debt. Fields referenced but empty may indicate broken integrations.',
          rec: 'Confirm with stakeholders, then delete unused fields via Setup > Object Manager. Always export field data before deleting.',
        },
        {
          category: 'Permissions',
          icon: I.lock,
          title: 'Excessive Permissions',
          desc: 'Profiles or permission sets granting "Modify All Data", "View All Data", or similar admin-level access to non-admin users violate the principle of least privilege and create significant compliance risk.',
          rec: 'Audit affected users and remove overpermissive access. Replace broad profile permissions with scoped permission sets.',
        },
        {
          category: 'Validation',
          icon: I.check,
          title: 'Validation Rules Without Descriptions',
          desc: 'Validation rules without descriptions or error messages create a poor user experience and are impossible to maintain. Users receive cryptic errors and admins cannot quickly understand the rule intent during debugging.',
          rec: 'Add a plain-language description to each validation rule and ensure the error message clearly explains what the user should do.',
        },
        {
          category: 'Layouts',
          icon: I.layout,
          title: 'Unassigned Page Layouts',
          desc: 'Page layouts not assigned to any profile or permission set are orphaned. They take up storage, can confuse admins, and represent unused configuration that may have been created in error.',
          rec: 'Assign the layout to the appropriate profiles or delete it if it is no longer needed.',
        },
        {
          category: 'Analytics',
          icon: I.chart,
          title: 'Stale Reports & Dashboards',
          desc: 'Reports and dashboards that have not been viewed in 6+ months are likely unused. They clutter the analytics experience, may run expensive queries on schedule, and can contain outdated business logic.',
          rec: 'Check last-viewed dates in the Reports tab. Archive or delete stale content and remove any associated scheduled runs.',
        },
        {
          category: 'Data Activity',
          icon: I.db,
          title: 'Data Exports & Batch Jobs',
          desc: 'Unexpected data exports or bulk operations may indicate a data leak, unauthorized integration, or misconfigured ETL job. OrgScan surfaces SetupAuditTrail export events and Apex batch job history.',
          rec: 'Review all export events for unfamiliar users or unusual volumes. For full row-level visibility, enable Salesforce Shield Event Monitoring.',
        },
      ];

      const docCards = docs.map(d =>
        '<div class="doc-card">' +
          '<div class="doc-card-header">' +
            '<div class="doc-card-icon">' + d.icon + '</div>' +
            '<div>' +
              '<div class="doc-card-category">' + esc(d.category) + '</div>' +
              '<div class="doc-card-title">' + esc(d.title) + '</div>' +
            '</div>' +
          '</div>' +
          '<p class="doc-card-desc">' + esc(d.desc) + '</p>' +
          '<div class="doc-card-rec">' +
            '<span class="doc-rec-label">Recommendation</span>' +
            '<p>' + esc(d.rec) + '</p>' +
          '</div>' +
        '</div>'
      ).join('');

      body = '<div class="doc-grid">' + docCards + '</div>';
    }

    return '<div class="content">' +
      '<div class="page-header">' +
        '<div>' +
          '<div class="page-title">History</div>' +
          '<div class="page-subtitle">Org activity and data events</div>' +
        '</div>' +
        (activeTab !== 'docs' ? '<button class="btn btn-secondary btn-sm" id="refreshActivityBtn">Refresh</button>' : '') +
      '</div>' +
      tabs + body +
    '</div>';
  }

  // ================================================================
  // DATA EXPORTS & IMPORTS
  // ================================================================
  function renderDataActivity() {
    if (!state.activeOrg) {
      return '<div class="content"><div class="page-header"><div>' +
        '<div class="page-title">' + I.export + ' Data Exports</div>' +
        '<div class="page-subtitle">Connect an org first</div>' +
        '</div></div></div>';
    }

    if (!state.dataActivityLog) {
      fetch('/data-activity?days=90')
        .then(r => r.json())
        .then(data => {
          state.dataActivityLog = data.events || [];
          render();
        })
        .catch(() => {
          state.dataActivityLog = [];
          render();
        });
      return '<div class="content"><div class="page-header"><div>' +
        '<div class="page-title">' + I.export + ' Data Exports &amp; Imports</div>' +
        '<div class="page-subtitle">Last 90 days</div>' +
        '</div></div>' +
        '<div class="card"><div class="card-body"><div class="loading-msg">Loading data activity\u2026</div></div></div>' +
        '</div>';
    }

    const events = state.dataActivityLog;
    const exports  = events.filter(e => e.event_type === 'Export/Import');
    const batches  = events.filter(e => e.event_type === 'Batch Job');
    const shield   = events.filter(e => e.event_type === 'Shield');

    function eventTable(rows, cols, emptyMsg) {
      if (!rows.length) {
        return '<div class="empty-state" style="padding:32px">' + emptyMsg + '</div>';
      }
      return '<div class="table-wrapper"><table class="dash-table">' +
        '<thead><tr>' + cols.map(c => '<th>' + c + '</th>').join('') + '</tr></thead>' +
        '<tbody>' + rows + '</tbody></table></div>';
    }

    const exportRows = exports.map(e => {
      const ts = e.timestamp ? new Date(e.timestamp).toLocaleString() : '—';
      return '<tr>' +
        '<td>' + esc(e.user) + '</td>' +
        '<td>' + esc(e.action) + '</td>' +
        '<td class="muted">' + ts + '</td>' +
        '<td class="muted">' + esc(e.detail) + '</td>' +
        '</tr>';
    }).join('');

    const batchRows = batches.map(e => {
      const ts = e.timestamp ? new Date(e.timestamp).toLocaleString() : '—';
      const hasErr = e.detail && e.detail.toLowerCase().includes('errors:') && !e.detail.includes('Errors: 0');
      return '<tr>' +
        '<td>' + esc(e.user) + '</td>' +
        '<td>' + esc(e.action) + '</td>' +
        '<td class="muted">' + ts + '</td>' +
        '<td class="' + (hasErr ? 'text-danger' : 'muted') + '">' + esc(e.detail) + '</td>' +
        '</tr>';
    }).join('');

    const shieldNote = shield.length
      ? '<div class="info-banner" style="margin-top:16px;padding:12px 16px;background:var(--primary-light,#eaf0ff);border-radius:8px;color:var(--primary)">' +
          '<strong>Salesforce Shield detected</strong> — ' + shield.length + ' event log file(s) available. ' +
          'Download from Setup &rsaquo; Event Log Files for detailed user-level data access records.' +
        '</div>'
      : '<div class="info-banner" style="margin-top:16px;padding:12px 16px;background:#f5f6fa;border-radius:8px;color:#6b7280;">' +
          '<strong>Want deeper visibility?</strong> Salesforce Shield Event Monitoring captures row-level data exports, ' +
          'report exports, and Bulk API operations per user. Not currently licensed on this org.' +
        '</div>';

    return '<div class="content">' +
      '<div class="page-header">' +
        '<div>' +
          '<div class="page-title">' + I.export + ' Data Exports &amp; Imports</div>' +
          '<div class="page-subtitle">Activity detected in SetupAuditTrail and Apex job queue — last 90 days</div>' +
        '</div>' +
        '<button class="btn btn-secondary btn-sm" id="refreshDataActivityBtn">Refresh</button>' +
      '</div>' +

      '<div class="section-title" style="margin-bottom:8px">Export / Import Events <span class="nav-badge" style="margin-left:8px">' + exports.length + '</span></div>' +
      '<div class="card" style="margin-bottom:24px">' +
        eventTable(exportRows,
          ['User', 'Action', 'Date / Time', 'Detail'],
          'No data export or import events detected in SetupAuditTrail for the last 90 days.') +
      '</div>' +

      '<div class="section-title" style="margin-bottom:8px">Batch &amp; Scheduled Jobs <span class="nav-badge" style="margin-left:8px">' + batches.length + '</span></div>' +
      '<div class="card" style="margin-bottom:24px">' +
        eventTable(batchRows,
          ['Submitted By', 'Job', 'Date / Time', 'Status'],
          'No batch or scheduled Apex jobs found in the last 90 days.') +
      '</div>' +

      shieldNote +
      '</div>';
  }

  // ================================================================
  // FINDINGS VIEW (consolidated, replaces per-category views)
  // ================================================================
  function renderFindings() {
    const findings = state.findings;
    const activeSev = state.findingsSev || 'All';
    const activeCat = state.findingsCat || 'All';

    const sevCounts = { All: findings.length, Critical: 0, Warning: 0, Info: 0, Resolved: 0 };
    findings.forEach(f => { if (sevCounts[f.severity] !== undefined) sevCounts[f.severity]++; });

    const filtered = findings.filter(f =>
      (activeSev === 'All' || f.severity === activeSev) &&
      (activeCat === 'All' || f.category === activeCat)
    );

    const sevTabs = ['All', 'Critical', 'Warning', 'Info', 'Resolved'].map(s =>
      '<button class="pill-tab' + (activeSev === s ? ' active' : '') + '" data-findings-sev="' + s + '">' +
        s + ' <span class="pill-count">' + sevCounts[s] + '</span></button>'
    ).join('');

    const catOptions = ['All', ...CATEGORIES].map(c =>
      '<option value="' + c + '"' + (activeCat === c ? ' selected' : '') + '>' + c + '</option>'
    ).join('');

    const filterBar = '<div class="findings-filter-bar">' +
      '<div class="pill-tabs">' + sevTabs + '</div>' +
      '<select class="filter-select" id="findingsCatFilter">' + catOptions + '</select>' +
    '</div>';

    // Format scan time for "Detected" column
    const detectedDate = state.lastScanTime
      ? state.lastScanTime.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
      : 'This scan';
    const detectedTime = state.lastScanTime
      ? state.lastScanTime.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })
      : '';

    const rows = filtered.length === 0
      ? '<tr><td colspan="5" style="padding:40px;text-align:center;color:var(--text-muted)">No findings match the selected filters.</td></tr>'
      : filtered.map(f => {
          const globalIdx = findings.indexOf(f);
          const rowAccent = SEV_ROW_COLOR[f.severity] || 'var(--border-color)';
          const isFlow = f.category === 'Flows' && f.flow_api_name && f.severity !== 'Resolved';
          const flowHtml = isFlow
            ? '<div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:6px">' +
                '<button class="btn btn-secondary btn-sm" data-action="genDesc" data-flow="' + esc(f.flow_api_name) + '">' +
                  I.sparkle + ' AI Description</button></div>' +
                '<div class="desc-area" id="desc-' + esc(f.flow_api_name) + '" style="display:none">' +
                  '<textarea id="desc-text-' + esc(f.flow_api_name) + '" placeholder="AI-generated description\u2026"></textarea>' +
                  '<div class="desc-actions">' +
                    '<button class="btn btn-success btn-sm" onclick="OrgScan.writeDesc(\'' + esc(f.flow_api_name) + '\')">' + I.pen + ' Write to Org</button>' +
                    '<button class="btn btn-secondary btn-sm" onclick="OrgScan.cancelDesc(\'' + esc(f.flow_api_name) + '\')">Cancel</button>' +
                  '</div></div>'
            : '';

          const isResolved = f.severity === 'Resolved';
          const statusPill = isResolved
            ? '<span class="finding-status-pill status-resolved">&#10003; Resolved</span>'
            : '<span class="finding-status-pill status-open">&#9679; Open</span>';

          return '<tr style="border-left:3px solid ' + rowAccent + '">' +
            '<td style="white-space:nowrap;vertical-align:top;padding-top:14px">' +
              severityBadge(f.severity) +
              '<br><span class="muted" style="font-size:11px;display:block;margin-top:4px;text-align:center">' + esc(f.category) + '</span>' +
            '</td>' +
            '<td class="finding-title-cell">' +
              (f.link ? '<a href="' + esc(f.link) + '" target="_blank" rel="noopener" class="finding-title-link">' + esc(f.title) + ' ' + I.extLink + '</a>'
                      : '<span class="finding-title-text">' + esc(f.title) + '</span>') +
              '<div class="finding-detail-preview">' + esc((f.detail || '').split('\n')[0]) + '</div>' +
              flowHtml +
            '</td>' +
            '<td style="white-space:nowrap;vertical-align:top;padding-top:14px;text-align:center">' +
              statusPill +
            '</td>' +
            '<td style="vertical-align:top;padding-top:12px">' +
              '<div class="finding-detected-date">' + detectedDate + '</div>' +
              (detectedTime ? '<div class="finding-detected-time">' + detectedTime + '</div>' : '') +
            '</td>' +
            '<td style="white-space:nowrap;text-align:right;vertical-align:top;padding-top:14px">' +
              '<button class="btn btn-secondary btn-sm" onclick="OrgScan.showFinding(' + globalIdx + ')">Details</button>' +
            '</td></tr>';
        }).join('');

    const emptyState = findings.length === 0
      ? '<div class="card"><div class="card-body"><div class="empty-state">' +
          '<div class="empty-state-icon">' + I.shieldSm + '</div>' +
          '<p>No findings yet — run a scan to get started.</p>' +
        '</div></div></div>'
      : '';

    return '<div class="content">' +
      '<div class="page-header">' +
        '<div><div class="page-title">Findings</div>' +
          '<div class="page-subtitle">' + findings.length + ' total finding' + (findings.length !== 1 ? 's' : '') + '</div></div>' +
      '</div>' +
      emptyState +
      (findings.length > 0 ? filterBar +
        '<div class="card"><div class="table-wrapper" id="findings-table-body"><table class="dash-table">' +
          '<thead><tr>' +
            '<th style="width:90px">Severity</th><th>Finding</th>' +
            '<th style="width:90px;text-align:center">Status</th>' +
            '<th style="width:120px">Detected</th>' +
            '<th style="width:80px"></th>' +
          '</tr></thead>' +
          '<tbody>' + rows + '</tbody>' +
        '</table></div></div>' : '') +
    '</div>';
  }

  // ================================================================
  // DUPLICATES
  // ================================================================
  function renderDuplicates() {
    if (!state.activeOrg) {
      return '<div class="content">' +
        '<div class="page-header"><div>' +
          '<div class="page-title">' + I.merge + ' Duplicate Management</div>' +
          '<div class="page-subtitle">Connect an org first</div>' +
        '</div></div></div>';
    }

    // Load object catalogue if not yet fetched
    if (!state.dupObjects) {
      fetch('/duplicates/objects')
        .then(r => r.json())
        .then(d => { state.dupObjects = d.objects || []; render(); })
        .catch(() => { state.dupObjects = []; render(); });
    }

    const isCross = state.dupObjectName === '_cross_lead_contact';
    const activeTab = state.dupTab || 'setup';
    const resultCount = state.dupResults
      ? (isCross ? state.dupResults.total_matches : state.dupResults.total_groups)
      : null;

    const historyCount = Object.keys(state.dupScanHistory).length;
    const tabs = '<div class="pill-tabs" style="margin-bottom:20px">' +
      '<button class="pill-tab' + (activeTab === 'overview' ? ' active' : '') + '" data-dup-tab="overview">' +
        'Overview' + (historyCount > 0 ? ' <span class="pill-count">' + historyCount + '</span>' : '') +
      '</button>' +
      '<button class="pill-tab' + (activeTab === 'setup' ? ' active' : '') + '" data-dup-tab="setup">Setup</button>' +
      '<button class="pill-tab' + (activeTab === 'results' ? ' active' : '') + '" data-dup-tab="results">' +
        'Results' + (resultCount !== null ? ' <span class="pill-count">' + resultCount + '</span>' : '') +
      '</button>' +
    '</div>';

    let body = '';

    if (activeTab === 'overview') {
      // ── Overview tab ───────────────────────────────────────────────
      const history = state.dupScanHistory;
      const keys = Object.keys(history);

      if (keys.length === 0) {
        body = '<div class="card"><div class="card-body"><div class="empty-state">' +
          '<div class="empty-state-icon">' + I.merge + '</div>' +
          '<p>No scans yet. Use the <strong>Setup</strong> tab to run your first duplicate scan.</p>' +
          '<button class="btn btn-primary btn-sm" data-dup-tab="setup" style="margin-top:12px">Go to Setup</button>' +
        '</div></div></div>';
      } else {
        // Summary header
        const totalAffected = keys.reduce((s, k) => s + (history[k].total_records || 0), 0);
        const totalScanned  = keys.reduce((s, k) => s + (history[k].records_scanned || 0), 0);
        const overallPct = totalScanned > 0 ? ((totalAffected / totalScanned) * 100).toFixed(1) : '0.0';
        const pctNum = parseFloat(overallPct);
        const pctColor = pctNum === 0 ? 'var(--success)' : pctNum < 5 ? '#fcbe2d' : 'var(--danger)';

        const summaryBanner = '<div class="dup-ov-summary">' +
          '<div class="dup-ov-sum-item">' +
            '<div class="dup-ov-sum-num" style="color:' + pctColor + '">' + overallPct + '%</div>' +
            '<div class="dup-ov-sum-lbl">Overall Duplicate Rate</div>' +
          '</div>' +
          '<div class="dup-ov-sum-div"></div>' +
          '<div class="dup-ov-sum-item">' +
            '<div class="dup-ov-sum-num">' + totalAffected + '</div>' +
            '<div class="dup-ov-sum-lbl">Affected Records</div>' +
          '</div>' +
          '<div class="dup-ov-sum-div"></div>' +
          '<div class="dup-ov-sum-item">' +
            '<div class="dup-ov-sum-num">' + totalScanned + '</div>' +
            '<div class="dup-ov-sum-lbl">Records Scanned</div>' +
          '</div>' +
          '<div class="dup-ov-sum-div"></div>' +
          '<div class="dup-ov-sum-item">' +
            '<div class="dup-ov-sum-num">' + keys.length + '</div>' +
            '<div class="dup-ov-sum-lbl">Objects Scanned</div>' +
          '</div>' +
        '</div>';

        const cards = keys.map(k => {
          const h = history[k];
          const scanned = h.records_scanned || 0;
          const affected = h.total_records || 0;
          const pct = scanned > 0 ? Math.min(100, (affected / scanned) * 100) : 0;
          const pctStr = pct.toFixed(1);
          const col = pct === 0 ? 'var(--success)' : pct < 5 ? '#fcbe2d' : 'var(--danger)';
          const statusLbl = pct === 0 ? 'Clean' : pct < 5 ? 'Low' : pct < 20 ? 'Moderate' : 'High';
          const isCrossCard = h.type === 'cross';

          return '<div class="dup-ov-card">' +
            '<div class="dup-ov-card-hdr">' +
              '<div class="dup-ov-card-icon">' + I.merge + '</div>' +
              '<div class="dup-ov-card-title">' + esc(h.label) + '</div>' +
              '<span class="dup-ov-status-badge" style="background:' + col + '20;color:' + col + '">' + statusLbl + '</span>' +
            '</div>' +
            '<div class="dup-ov-pct-row">' +
              '<div class="dup-ov-pct-num" style="color:' + col + '">' + pctStr + '%</div>' +
              '<div class="dup-ov-bar-wrap">' +
                '<div class="dup-ov-bar-track">' +
                  '<div class="dup-ov-bar-fill" style="width:' + Math.max(pct, pct > 0 ? 1 : 0) + '%;background:' + col + '"></div>' +
                '</div>' +
              '</div>' +
            '</div>' +
            '<div class="dup-ov-card-stats">' +
              (isCrossCard
                ? '<span>' + affected + ' lead' + (affected !== 1 ? 's' : '') + ' match contacts</span><span>' + scanned + ' leads scanned</span>'
                : '<span>' + affected + ' records in duplicate groups</span><span>' + scanned + ' records scanned</span>') +
            '</div>' +
            (h.total_groups !== undefined && !isCrossCard
              ? '<div class="dup-ov-card-foot">' + h.total_groups + ' duplicate group' + (h.total_groups !== 1 ? 's' : '') + ' found</div>'
              : '') +
            (h.scannedAt
              ? '<div class="dup-ov-card-time">Last scanned ' + new Date(h.scannedAt).toLocaleString() + '</div>'
              : '') +
            '<button class="btn btn-secondary btn-sm dup-ov-drill-btn" data-dup-drill="' + esc(k) + '" style="margin-top:10px">View Results</button>' +
          '</div>';
        }).join('');

        body = summaryBanner +
          '<div style="display:flex;justify-content:flex-end;margin:-4px 0 12px">' +
            '<button class="btn btn-secondary btn-sm" data-dup-download="overview">' + I.export + ' Download Summary CSV</button>' +
          '</div>' +
          '<div class="dup-ov-grid">' + cards + '</div>';
      }

    } else if (activeTab === 'setup') {
      if (!state.dupObjects) {
        body = '<div class="card"><div class="card-body"><div class="loading-msg">Loading objects\u2026</div></div></div>';
      } else {
        const objOptions = state.dupObjects.map(o =>
          '<option value="' + esc(o.value) + '"' + (state.dupObjectName === o.value ? ' selected' : '') + '>' + esc(o.label) + '</option>'
        ).join('');

        const selectedObj = state.dupObjects.find(o => o.value === state.dupObjectName);
        const matchFieldsHtml = selectedObj
          ? selectedObj.match_fields.map(f =>
              '<label class="dup-field-label">' +
                '<input type="checkbox" class="dup-field-cb" value="' + esc(f.value) + '"' +
                  (state.dupMatchFields.includes(f.value) ? ' checked' : '') + '>' +
                '<span>' + esc(f.label) + '</span>' +
                '<code class="dup-field-code">' + esc(f.value) + '</code>' +
              '</label>'
            ).join('')
          : '<p class="dup-empty-msg">Select an object above to configure matching fields.</p>';

        // Mode toggle only for non-cross-object
        const modeSection = !isCross
          ? '<div class="dup-setup-section">' +
              '<div class="dup-mode-row">' +
                '<div class="dup-mode-info">' +
                  '<div class="dup-mode-title">Detection Mode</div>' +
                  '<div class="dup-mode-desc">Custom: match on field values you choose. Native: read Salesforce\'s own duplicate rules.</div>' +
                '</div>' +
                '<div class="dup-mode-btns">' +
                  '<button class="dup-mode-btn' + (state.dupMode === 'custom' ? ' active' : '') + '" data-dup-mode="custom">Custom</button>' +
                  '<button class="dup-mode-btn' + (state.dupMode === 'native' ? ' active' : '') + '" data-dup-mode="native">Native</button>' +
                '</div>' +
              '</div>' +
            '</div>'
          : '';

        const canScan = state.dupObjectName &&
          ((!isCross && state.dupMode === 'native') || state.dupMatchFields.length > 0);

        const crossNote = isCross
          ? '<div class="dup-cross-note">' +
              I.merge +
              '<div><strong>Cross-Object Scan</strong> — Finds unconverted Leads that already have a matching Contact. ' +
              'When a match is found, the Lead should be converted (not kept as a separate record). ' +
              'Matching is normalized: punctuation, spaces, and case are ignored.</div>' +
            '</div>'
          : '';

        body = crossNote +
          '<div class="card">' +
          '<div class="card-header"><span class="card-title">Scan Configuration</span></div>' +
          '<div class="card-body">' +
            '<div class="dup-setup-grid">' +
              '<div class="dup-setup-section">' +
                '<div class="dup-setup-label">Scan Type</div>' +
                '<div class="dup-setup-desc">Choose an object to scan for same-object duplicates, or select <em>Lead → Contact</em> to find Leads that already exist as Contacts.</div>' +
                '<select class="dup-object-select" id="dupObjectSelect">' +
                  '<option value="">— Select scan type —</option>' + objOptions +
                '</select>' +
              '</div>' +
              '<div class="dup-setup-section">' +
                '<div class="dup-setup-label">Match Fields</div>' +
                '<div class="dup-setup-desc">' +
                  (isCross
                    ? 'A Lead is flagged when it matches a Contact on ALL checked fields simultaneously (AND logic, case and punctuation insensitive). Select First Name + Last Name together for name-based matching.'
                    : 'Two records are considered duplicates when all checked fields match.') +
                '</div>' +
                '<div class="dup-field-list">' + matchFieldsHtml + '</div>' +
              '</div>' +
              modeSection +
            '</div>' +
            '<div class="dup-scan-footer">' +
              (state.dupMatchFields.length === 0 && state.dupObjectName && (isCross || state.dupMode === 'custom')
                ? '<p class="dup-hint-msg" style="margin:0 0 12px">Select at least one match field above.</p>'
                : '') +
              '<button class="btn btn-primary" id="dupScanBtn"' + (canScan && !state.dupLoading ? '' : ' disabled') + '>' +
                (state.dupLoading
                  ? '<span class="spinner"></span> Scanning\u2026'
                  : I.merge + ' Scan for Duplicates') +
              '</button>' +
            '</div>' +
          '</div>' +
        '</div>' +
        (!isCross
          ? '<div class="card dup-info-card"><div class="card-body"><div class="dup-info-grid">' +
              '<div class="dup-info-item"><div class="dup-info-icon" style="color:var(--primary)">' + I.merge + '</div>' +
              '<div><div class="dup-info-title">Custom Mode</div>' +
              '<div class="dup-info-desc">OrgScan pulls up to 5,000 records and groups them by normalized field values. Works on any org.</div></div></div>' +
              '<div class="dup-info-item"><div class="dup-info-icon" style="color:var(--success)">' + I.shieldSm + '</div>' +
              '<div><div class="dup-info-title">Native Mode</div>' +
              '<div class="dup-info-desc">Reads DuplicateRecordSet objects from Salesforce\'s own active duplicate rules.</div></div></div>' +
            '</div></div></div>'
          : '');
      }

    } else {  // results tab
      // ── Results tab ──────────────────────────────────────────────
      if (isCross) {
        // Cross-object results
        const matches = state.dupResults && state.dupResults.matches;
        if (!matches || !matches.length) {
          body = '<div class="card"><div class="card-body"><div class="empty-state">' +
            '<div class="empty-state-icon">' + I.merge + '</div>' +
            '<p>' + (state.dupResults ? 'No Lead \u2194 Contact matches found. Your data looks clean!' : 'Run a scan on the Setup tab first.') + '</p>' +
            '<button class="btn btn-primary btn-sm" data-dup-tab="setup" style="margin-top:12px">Go to Setup</button>' +
          '</div></div></div>';
        } else {
          const cfg = state.dupResults.config || {};
          const banner = '<div class="dup-results-banner">' +
            '<div class="dup-banner-stat"><div class="dup-banner-num">' + matches.length + '</div><div class="dup-banner-lbl">Leads to Convert</div></div>' +
            '<div class="dup-banner-div"></div>' +
            '<div class="dup-banner-stat"><div class="dup-banner-num">Lead \u2194 Contact</div><div class="dup-banner-lbl">Scan Type</div></div>' +
            (cfg.match_fields && cfg.match_fields.length
              ? '<div class="dup-banner-div"></div>' +
                '<div class="dup-banner-stat"><div class="dup-banner-num" style="font-size:13px;font-weight:600">' + cfg.match_fields.join(', ') + '</div><div class="dup-banner-lbl">Matched On</div></div>'
              : '') +
          '</div>';

          const matchCards = matches.map(m => {
            const isOpen = state.dupExpanded[m.group_id];
            const lead = m.lead || {};
            const contacts = m.contacts || [];
            const matchedOn = (m.matched_on || []).join(', ');

            const leadRow = '<div class="cross-record cross-lead">' +
              '<div class="cross-badge cross-badge-lead">Lead</div>' +
              '<div class="cross-record-info">' +
                '<div class="cross-record-name">' + esc(lead.Name || '—') + '</div>' +
                '<div class="cross-record-meta">' +
                  (lead.Email ? '<span>' + esc(lead.Email) + '</span>' : '') +
                  (lead.Phone ? '<span>' + esc(lead.Phone) + '</span>' : '') +
                  (lead.Company ? '<span>' + esc(lead.Company) + '</span>' : '') +
                  '<span class="cross-record-id">' + esc(lead.Id || '') + '</span>' +
                '</div>' +
              '</div>' +
              '<div class="cross-record-actions">' +
                (m.convert_url
                  ? '<a href="' + esc(m.convert_url) + '" target="_blank" rel="noopener" class="btn btn-primary btn-sm">' +
                      I.merge + ' Convert Lead' +
                    '</a>'
                  : '') +
              '</div>' +
            '</div>';

            const contactRows = contacts.map(c =>
              '<div class="cross-record cross-contact">' +
                '<div class="cross-badge cross-badge-contact">Contact</div>' +
                '<div class="cross-record-info">' +
                  '<div class="cross-record-name">' + esc(c.Name || '—') + '</div>' +
                  '<div class="cross-record-meta">' +
                    (c.Email ? '<span>' + esc(c.Email) + '</span>' : '') +
                    (c.Phone ? '<span>' + esc(c.Phone) + '</span>' : '') +
                    '<span class="cross-record-id">' + esc(c.Id || '') + '</span>' +
                  '</div>' +
                '</div>' +
              '</div>'
            ).join('');

            return '<div class="dup-group-card" id="dupgroup-' + m.group_id + '">' +
              '<div class="dup-group-header" data-dup-toggle="' + m.group_id + '">' +
                '<div class="dup-group-info">' +
                  '<span class="dup-group-count">' + esc(lead.Name || lead.Id || 'Lead') + '</span>' +
                  '<span class="dup-group-fields"><code>matched on: ' + esc(matchedOn) + '</code></span>' +
                  '<span class="cross-contact-count">' + contacts.length + ' contact match' + (contacts.length !== 1 ? 'es' : '') + '</span>' +
                '</div>' +
                '<div class="dup-group-actions">' +
                  (m.convert_url
                    ? '<a href="' + esc(m.convert_url) + '" target="_blank" rel="noopener" class="btn btn-primary btn-sm">' +
                        I.merge + ' Convert Lead' +
                      '</a>'
                    : '') +
                  '<button class="dup-toggle-btn" data-dup-toggle="' + m.group_id + '">' +
                    (isOpen ? I.chevUp : I.chevDown) +
                    '<span>' + (isOpen ? 'Collapse' : 'Expand') + '</span>' +
                  '</button>' +
                '</div>' +
              '</div>' +
              (isOpen
                ? '<div class="dup-group-body cross-group-body">' +
                    leadRow +
                    '<div class="cross-divider">' + I.chevDown + ' Matches existing Contact(s)</div>' +
                    contactRows +
                    '<div class="dup-merge-hint">' +
                      'Click <strong>Convert Lead</strong> to open Salesforce\'s lead conversion screen — you can attach it to the existing Contact and Account without creating duplicates.' +
                    '</div>' +
                  '</div>'
                : '') +
            '</div>';
          }).join('');

          body = '<div style="display:flex;justify-content:flex-end;margin-bottom:8px">' +
            '<button class="btn btn-secondary btn-sm" data-dup-download="results">' + I.export + ' Download CSV</button>' +
          '</div>' + banner + '<div class="dup-groups-list">' + matchCards + '</div>';
        }

      } else {
        // Same-object results
        if (!state.dupResults || !state.dupResults.groups || !state.dupResults.groups.length) {
          body = '<div class="card"><div class="card-body"><div class="empty-state">' +
            '<div class="empty-state-icon">' + I.merge + '</div>' +
            '<p>' + (state.dupResults ? 'No duplicate groups found. Your data looks clean!' : 'Run a scan on the Setup tab to find duplicates.') + '</p>' +
            '<button class="btn btn-primary btn-sm" data-dup-tab="setup" style="margin-top:12px">Go to Setup</button>' +
          '</div></div></div>';
        } else {
          const groups = state.dupResults.groups;
          const cfg = state.dupResults.config || {};

          const banner = '<div class="dup-results-banner">' +
            '<div class="dup-banner-stat"><div class="dup-banner-num">' + state.dupResults.total_groups + '</div><div class="dup-banner-lbl">Duplicate Groups</div></div>' +
            '<div class="dup-banner-div"></div>' +
            '<div class="dup-banner-stat"><div class="dup-banner-num">' + state.dupResults.total_records + '</div><div class="dup-banner-lbl">Affected Records</div></div>' +
            '<div class="dup-banner-div"></div>' +
            '<div class="dup-banner-stat"><div class="dup-banner-num">' + esc(cfg.object_name || '—') + '</div><div class="dup-banner-lbl">Object</div></div>' +
            (cfg.match_fields && cfg.match_fields.length
              ? '<div class="dup-banner-div"></div><div class="dup-banner-stat"><div class="dup-banner-num" style="font-size:13px;font-weight:600">' + cfg.match_fields.join(', ') + '</div><div class="dup-banner-lbl">Matched On</div></div>'
              : '') +
          '</div>';

          const groupRows = groups.map(g => {
            const isOpen = state.dupExpanded[g.group_id];
            const recordRows = isOpen ? g.records.map((r, ri) => {
              const isMaster = ri === 0;
              const name = esc(r.Name || r.Id || '—');
              const createdStr = r.CreatedDate ? new Date(r.CreatedDate).toLocaleDateString(undefined, {month:'short',day:'numeric',year:'numeric'}) : '—';
              const modStr = r.LastModifiedDate ? new Date(r.LastModifiedDate).toLocaleDateString(undefined, {month:'short',day:'numeric',year:'numeric'}) : '—';
              return '<tr class="dup-record-row' + (isMaster ? ' dup-record-master' : '') + '">' +
                '<td><span class="dup-record-name">' + name + '</span>' +
                  (isMaster ? '<span class="dup-master-badge">Master</span>' : '') +
                '</td>' +
                '<td class="dup-record-id">' + esc(r.Id || '—') + '</td>' +
                '<td>' + createdStr + '</td>' +
                '<td>' + modStr + '</td>' +
                '<td style="text-align:right">' +
                  (!isMaster
                    ? '<button class="btn btn-danger btn-sm dup-delete-btn" data-object="' + esc(g.object_name) + '" data-id="' + esc(r.Id) + '" data-gid="' + g.group_id + '">' + I.trash + ' Delete</button>'
                    : '<span style="color:var(--text-muted);font-size:12px">Keep</span>') +
                '</td>' +
              '</tr>';
            }).join('') : '';

            return '<div class="dup-group-card" id="dupgroup-' + g.group_id + '">' +
              '<div class="dup-group-header" data-dup-toggle="' + g.group_id + '">' +
                '<div class="dup-group-info">' +
                  '<span class="dup-group-count">' + g.count + ' records</span>' +
                  (g.match_fields && g.match_fields.length
                    ? '<span class="dup-group-fields">' + g.match_fields.map(f => '<code>' + esc(f) + '</code>').join(' + ') + '</span>'
                    : '') +
                '</div>' +
                '<div class="dup-group-actions">' +
                  (g.merge_url ? '<a href="' + esc(g.merge_url) + '" target="_blank" rel="noopener" class="btn btn-primary btn-sm">' + I.merge + ' Merge in Salesforce</a>' : '') +
                  '<button class="btn btn-secondary btn-sm dup-dismiss-btn" data-dup-dismiss="' + g.group_id + '" title="Mark as resolved and remove from this list">Dismiss</button>' +
                  '<button class="dup-toggle-btn" data-dup-toggle="' + g.group_id + '">' +
                    (isOpen ? I.chevUp : I.chevDown) + '<span>' + (isOpen ? 'Collapse' : 'Expand') + '</span>' +
                  '</button>' +
                '</div>' +
              '</div>' +
              (isOpen
                ? '<div class="dup-group-body"><div class="table-wrapper"><table class="dash-table">' +
                    '<thead><tr><th>Name</th><th>Record ID</th><th>Created</th><th>Last Modified</th><th style="text-align:right"></th></tr></thead>' +
                    '<tbody>' + recordRows + '</tbody>' +
                  '</table></div>' +
                  '<div class="dup-merge-hint">' +
                    'Click <strong>Merge in Salesforce</strong> to open the Salesforce merge screen — choose which field values to keep and confirm. ' +
                    (g.count > 3 ? '<strong>Note:</strong> Salesforce merges up to 3 records at a time; you may need to merge in rounds. ' : '') +
                    'After merging, click <strong>Dismiss</strong> to remove this group from OrgScan. ' +
                    'Use <strong>Delete</strong> only when you are certain a record has no unique data.' +
                  '</div></div>'
                : '') +
            '</div>';
          }).join('');

          body = '<div style="display:flex;justify-content:flex-end;margin-bottom:8px">' +
            '<button class="btn btn-secondary btn-sm" data-dup-download="results">' + I.export + ' Download CSV</button>' +
          '</div>' + banner + '<div class="dup-groups-list">' + groupRows + '</div>';
        }
      }
    }

    return '<div class="content">' +
      '<div class="page-header">' +
        '<div>' +
          '<div class="page-title">' + I.merge + ' Duplicate Management</div>' +
          '<div class="page-subtitle">Find and resolve duplicate records in your org</div>' +
        '</div>' +
      '</div>' +
      tabs + body +
    '</div>';
  }

  // ================================================================
  // CONNECT SCREEN
  // ================================================================
  function renderConnectScreen() {
    return '<div class="main-area" style="flex:1;margin-left:0">' + renderTopbar() +
      '<div class="connect-screen"><div class="connect-card">' +
        '<div class="connect-logo">' + I.shieldWh + '</div>' +
        '<div class="connect-title">Welcome to OrgScan</div>' +
        '<div class="connect-desc">Connect your Salesforce org to scan for security issues, inactive flows, missing field descriptions, permission gaps, and more.</div>' +
        '<button class="btn btn-primary connect-btn" id="connectOrgBtn">Connect Salesforce Org</button>' +
      '</div></div>' +
      '</div>';
  }

  // ================================================================
  // SETTINGS
  // ================================================================
  function renderSettings() {
    const org = state.activeOrg;
    const score = state.score;
    const findings = state.findings;
    const cnt = { Critical: 0, Warning: 0, Info: 0 };
    findings.forEach(f => { if (cnt[f.severity] !== undefined) cnt[f.severity]++; });

    function gaugeColor(s) {
      if (s >= 75) return '#2F6B3F';
      if (s >= 50) return '#B45309';
      if (s >= 25) return '#B45309';
      return '#9B2C2C';
    }

    const username = org ? (org.username || 'Unknown User') : '—';
    const instanceUrl = org ? (org.instance_url || '—') : '—';
    const orgId = org ? (org.org_id || '—') : '—';
    const initial = username && username !== '—' ? username[0].toUpperCase() : '?';

    // Determine org type from instance URL
    const isSandbox = instanceUrl.includes('sandbox') || instanceUrl.includes('--');
    const orgType = isSandbox ? 'Sandbox' : 'Production';
    const orgTypeBadge = isSandbox
      ? '<span class="stg-badge stg-sandbox">Sandbox</span>'
      : '<span class="stg-badge stg-prod">Production</span>';

    // Score ring (small)
    const scoreCol = score != null ? gaugeColor(score) : '#4880ff';
    const scoreRing = score != null
      ? '<div class="stg-score-ring" style="--ring-col:' + scoreCol + ';--ring-pct:' + score + '%">' +
          '<span class="stg-score-num" style="color:' + scoreCol + '">' + score + '</span>' +
          '<span class="stg-score-lbl">/ 100</span>' +
        '</div>'
      : '<div class="stg-score-ring" style="--ring-col:#b0b8c4;--ring-pct:0%">' +
          '<span class="stg-score-num" style="color:var(--text-muted)">—</span>' +
        '</div>';

    const profileCard = '<div class="card stg-profile-card">' +
      '<div class="stg-profile-left">' +
        '<div class="stg-avatar">' + initial + '</div>' +
        '<div class="stg-profile-info">' +
          '<div class="stg-profile-name">' + esc(username) + '</div>' +
          '<div class="stg-profile-role">Connected Salesforce Admin</div>' +
          '<div class="stg-badges">' +
            orgTypeBadge +
            '<span class="stg-badge stg-connected">Connected</span>' +
          '</div>' +
        '</div>' +
      '</div>' +
      '<div class="stg-profile-right">' +
        '<div class="stg-score-card">' +
          '<div class="stg-score-title">Account Security Score</div>' +
          '<div class="stg-score-sub">Based on latest scan results</div>' +
          scoreRing +
          (score != null ? '<div class="stg-score-breakdown">' +
            '<span class="stg-sbd stg-sbd-crit">' + cnt.Critical + ' critical</span>' +
            '<span class="stg-sbd stg-sbd-warn">' + cnt.Warning + ' warnings</span>' +
            '<span class="stg-sbd stg-sbd-info">' + cnt.Info + ' info</span>' +
          '</div>' : '<div class="stg-score-breakdown" style="color:var(--text-muted);font-size:12px">Run a scan to calculate score</div>') +
        '</div>' +
      '</div>' +
    '</div>';

    const orgInfoCard = '<div class="card">' +
      '<div class="card-header"><span class="card-title">Org Information</span></div>' +
      '<div class="card-body">' +
        '<div class="stg-info-grid">' +
          '<div class="stg-info-row">' +
            '<div class="stg-info-label">Username</div>' +
            '<div class="stg-info-value">' + esc(username) + '</div>' +
          '</div>' +
          '<div class="stg-info-row">' +
            '<div class="stg-info-label">Instance URL</div>' +
            '<div class="stg-info-value">' +
              (org && instanceUrl !== '—'
                ? '<a href="' + esc(instanceUrl) + '" target="_blank" rel="noopener" class="stg-link">' + esc(instanceUrl) + ' ' + I.extLink + '</a>'
                : '—') +
            '</div>' +
          '</div>' +
          '<div class="stg-info-row">' +
            '<div class="stg-info-label">Org Type</div>' +
            '<div class="stg-info-value">' + orgType + '</div>' +
          '</div>' +
          '<div class="stg-info-row">' +
            '<div class="stg-info-label">Org ID</div>' +
            '<div class="stg-info-value stg-mono">' + esc(orgId) + '</div>' +
          '</div>' +
          '<div class="stg-info-row">' +
            '<div class="stg-info-label">Scan Status</div>' +
            '<div class="stg-info-value">' +
              (findings.length > 0
                ? '<span style="color:var(--success)">&#10003; Last scan: ' + findings.length + ' findings</span>'
                : '<span style="color:var(--text-muted)">No scan run yet</span>') +
            '</div>' +
          '</div>' +
        '</div>' +
      '</div>' +
    '</div>';

    const prefsCard = '<div class="card">' +
      '<div class="card-header"><span class="card-title">System Preferences</span></div>' +
      '<div class="card-body">' +
        '<div class="stg-pref-list">' +
          '<div class="stg-pref-row">' +
            '<div class="stg-pref-info">' +
              '<div class="stg-pref-name">PDF Report Branding</div>' +
              '<div class="stg-pref-desc">Customize the client name when generating PDF reports</div>' +
            '</div>' +
            '<div class="stg-pref-action">' +
              '<button class="btn btn-secondary btn-sm" onclick="OrgScan.navigate(\'dashboard\')">Edit in Report</button>' +
            '</div>' +
          '</div>' +
          '<div class="stg-pref-row">' +
            '<div class="stg-pref-info">' +
              '<div class="stg-pref-name">Flow AI Descriptions</div>' +
              '<div class="stg-pref-desc">Generate AI-powered descriptions for flows missing documentation</div>' +
            '</div>' +
            '<div class="stg-pref-action">' +
              '<button class="btn btn-secondary btn-sm" onclick="OrgScan.navigate(\'findings\')">View Flows</button>' +
            '</div>' +
          '</div>' +
          '<div class="stg-pref-row">' +
            '<div class="stg-pref-info">' +
              '<div class="stg-pref-name">Scan Depth</div>' +
              '<div class="stg-pref-desc">Full scan checks Users, Flows, Fields, Permissions, Validations, Layouts, Analytics, and Data Activity</div>' +
            '</div>' +
            '<div class="stg-pref-action">' +
              '<span class="stg-badge stg-prod">Full Scan</span>' +
            '</div>' +
          '</div>' +
        '</div>' +
      '</div>' +
    '</div>';

    const dangerCard = org ? '<div class="card stg-danger-card">' +
      '<div class="card-header"><span class="card-title stg-danger-title">Danger Zone</span></div>' +
      '<div class="card-body">' +
        '<div class="stg-pref-row">' +
          '<div class="stg-pref-info">' +
            '<div class="stg-pref-name">Disconnect Org</div>' +
            '<div class="stg-pref-desc">Remove this org connection. You can reconnect at any time.</div>' +
          '</div>' +
          '<div class="stg-pref-action">' +
            '<div class="nav-item danger" id="disconnectBtn" style="display:inline-flex;align-items:center;gap:6px;padding:8px 14px;border-radius:8px;cursor:pointer;font-size:13px;font-weight:600;border:1px solid rgba(253,84,84,0.3);background:rgba(253,84,84,0.05)">' +
              I.logout + ' Disconnect' +
            '</div>' +
          '</div>' +
        '</div>' +
      '</div>' +
    '</div>' : '';

    return '<div class="content">' +
      '<div class="page-header"><div>' +
        '<div class="page-title">Settings</div>' +
        '<div class="page-subtitle">Manage your OrgScan configuration</div>' +
      '</div></div>' +
      profileCard + orgInfoCard + prefsCard + dangerCard +
    '</div>';
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
    else if (v === 'findings')           body = renderFindings();
    else if (CATEGORIES.includes(v))     body = renderFindings();  // legacy routes → findings
    else if (v === 'activity')           body = renderActivity();
    else if (v === 'data-activity')      body = renderDataActivity();
    else if (v === 'duplicates')         body = renderDuplicates();
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

    const csvBtn = document.getElementById('exportCsvBtn');
    if (csvBtn) csvBtn.addEventListener('click', exportCsv);

    document.querySelectorAll('.pill-tab[data-sev]').forEach(b => {
      b.addEventListener('click', () => {
        state['filter_' + b.dataset.cat] = b.dataset.sev;
        render();
      });
    });

    document.querySelectorAll('.pill-tab[data-findings-sev]').forEach(b => {
      b.addEventListener('click', () => {
        state.findingsSev = b.dataset.findingsSev;
        render();
      });
    });

    document.querySelectorAll('.pill-tab[data-history-tab]').forEach(b => {
      b.addEventListener('click', () => {
        state.historyTab = b.dataset.historyTab;
        render();
      });
    });

    const refreshActivityBtn = document.getElementById('refreshActivityBtn');
    if (refreshActivityBtn) refreshActivityBtn.addEventListener('click', () => {
      if (state.historyTab === 'data' || state.historyTab === 'docs') {
        state.dataActivityLog = null;
      } else {
        state.activityLog = null;
      }
      render();
    });

    const catFilter = document.getElementById('findingsCatFilter');
    if (catFilter) catFilter.addEventListener('change', () => {
      state.findingsCat = catFilter.value;
      render();
    });

    const findingsTableBody = document.getElementById('findings-table-body');
    if (findingsTableBody) {
      findingsTableBody.addEventListener('click', e => {
        const btn = e.target.closest('[data-action]');
        if (btn && btn.dataset.action === 'genDesc') generateDesc(btn.dataset.flow, btn);
      });
    }

    const ctb = document.getElementById('cat-table-body');
    if (ctb) {
      ctb.addEventListener('click', e => {
        const btn = e.target.closest('[data-action]');
        if (btn && btn.dataset.action === 'genDesc') generateDesc(btn.dataset.flow, btn);
      });
    }

    // Duplicates — tab switching
    document.querySelectorAll('.pill-tab[data-dup-tab]').forEach(b => {
      b.addEventListener('click', () => { state.dupTab = b.dataset.dupTab; render(); });
    });

    // Duplicates — object selector
    const dupObjSel = document.getElementById('dupObjectSelect');
    if (dupObjSel) {
      dupObjSel.addEventListener('change', (e) => {
        state.dupObjectName = e.target.value;
        state.dupMatchFields = [];
        render();
      });
    }

    // Duplicates — match field checkboxes (delegated)
    document.querySelectorAll('.dup-field-cb').forEach(cb => {
      cb.addEventListener('change', () => {
        const checked = [...document.querySelectorAll('.dup-field-cb:checked')].map(el => el.value);
        state.dupMatchFields = checked;
        render();
      });
    });

    // Duplicates — mode buttons
    document.querySelectorAll('.dup-mode-btn').forEach(b => {
      b.addEventListener('click', () => { state.dupMode = b.dataset.dupMode; render(); });
    });

    // Duplicates — scan button
    const dupScanBtn = document.getElementById('dupScanBtn');
    if (dupScanBtn) dupScanBtn.addEventListener('click', scanDuplicates);

    // Duplicates — expand/collapse groups (delegated on content area)
    const contentEl = document.querySelector('.content');
    if (contentEl) {
      contentEl.addEventListener('click', e => {
        // Toggle group
        // Dismiss group — must be checked BEFORE toggle because button lives inside [data-dup-toggle] header
        const dismissBtn = e.target.closest('.dup-dismiss-btn');
        if (dismissBtn) {
          const gid = parseInt(dismissBtn.dataset.dupDismiss, 10);
          if (state.dupResults && state.dupResults.groups) {
            state.dupResults.groups = state.dupResults.groups.filter(g => g.group_id !== gid);
            state.dupResults.total_groups = state.dupResults.groups.length;
            state.dupResults.total_records = state.dupResults.groups.reduce((s, g) => s + g.count, 0);
          }
          // Update history so overview reflects the dismissal
          const histKey = state.dupObjectName;
          if (state.dupScanHistory[histKey]) {
            state.dupScanHistory[histKey].total_groups = state.dupResults.total_groups;
            state.dupScanHistory[histKey].total_records = state.dupResults.total_records;
            state.dupScanHistory[histKey].rawResult = state.dupResults;
          }
          render();
          return;
        }
        // Toggle group expand/collapse
        const toggleBtn = e.target.closest('[data-dup-toggle]');
        if (toggleBtn) {
          const gid = parseInt(toggleBtn.dataset.dupToggle, 10);
          state.dupExpanded[gid] = !state.dupExpanded[gid];
          render();
          return;
        }
        // Delete record
        const delBtn = e.target.closest('.dup-delete-btn');
        if (delBtn) {
          deleteDuplicateRecord(delBtn.dataset.object, delBtn.dataset.id, parseInt(delBtn.dataset.gid, 10), delBtn);
          return;
        }
        // Go to setup tab link
        const tabBtn = e.target.closest('[data-dup-tab]');
        if (tabBtn && !tabBtn.classList.contains('pill-tab')) {
          state.dupTab = tabBtn.dataset.dupTab;
          render();
          return;
        }
        // Drill into a scan from overview
        const drillBtn = e.target.closest('[data-dup-drill]');
        if (drillBtn) {
          const key = drillBtn.dataset.dupDrill;
          state.dupObjectName = key;
          state.dupResults = state.dupScanHistory[key] ? state.dupScanHistory[key].rawResult : null;
          state.dupTab = 'results';
          state.dupExpanded = {};
          render();
          return;
        }
        // Download CSV
        const dlBtn = e.target.closest('[data-dup-download]');
        if (dlBtn) {
          if (dlBtn.dataset.dupDownload === 'results') downloadDupResults();
          else if (dlBtn.dataset.dupDownload === 'overview') downloadDupOverview();
        }
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
      state.findings     = r.findings || [];
      state.score        = r.score;
      state.dashPage     = 0;
      state.lastScanTime = new Date();
      state.activeView   = 'dashboard';
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

  async function exportCsv() {
    var btn = document.getElementById('exportCsvBtn');
    if (btn) { btn.disabled = true; btn.textContent = 'Exporting\u2026'; }
    showToast('Generating CSV\u2026');
    try {
      var resp = await fetch(API + '/export/csv');
      if (!resp.ok) { showToast('CSV export failed', 'error'); return; }
      var blob = await resp.blob();
      var url  = URL.createObjectURL(blob);
      var a    = document.createElement('a');
      a.href     = url;
      // Note: innerHTML used here is safe — I.export is a static SVG constant
      // defined in the ICONS object, not user-supplied data.
      a.download = 'orgscan-findings.csv';
      a.click();
      URL.revokeObjectURL(url);
      showToast('CSV downloaded', 'success');
    } catch (e) {
      showToast('CSV export failed', 'error');
    } finally {
      if (btn) { btn.disabled = false; btn.textContent = ''; btn.insertAdjacentHTML('afterbegin', I.export + ' CSV'); }
    }
  }

  // ================================================================
  // API — ACTIVITY LOG
  // ================================================================
  function loadActivity() {
    state.activityLog = null;
    render();
  }

  // ================================================================
  // API — DUPLICATES
  // ================================================================
  async function scanDuplicates() {
    if (!state.activeOrg) { showToast('Connect an org first', 'error'); return; }
    if (!state.dupObjectName) { showToast('Select a scan type', 'error'); return; }
    if (state.dupMatchFields.length === 0 && (state.dupObjectName === '_cross_lead_contact' || state.dupMode === 'custom')) {
      showToast('Select at least one match field', 'error'); return;
    }

    const isCross = state.dupObjectName === '_cross_lead_contact';
    state.dupLoading = true;
    render();
    showToast('Scanning for duplicates\u2026');

    try {
      let r;
      if (isCross) {
        r = await fetch('/duplicates/cross-scan', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ match_fields: state.dupMatchFields }),
        }).then(res => res.json());
        if (r.detail) { showToast('Scan error: ' + r.detail, 'error'); return; }
        state.dupResults = {
          matches: r.matches || [],
          total_matches: r.total_matches || 0,
          leads_scanned: r.leads_scanned || 0,
          contacts_scanned: r.contacts_scanned || 0,
          config: { match_fields: state.dupMatchFields.slice() },
        };
        state.dupScanHistory['_cross_lead_contact'] = {
          label: 'Lead \u2194 Contact',
          type: 'cross',
          total_groups: r.total_matches || 0,
          total_records: r.total_matches || 0,
          records_scanned: r.leads_scanned || 0,
          scannedAt: Date.now(),
          rawResult: state.dupResults,
        };
        showToast('Scan complete \u2014 ' + (r.total_matches || 0) + ' Lead \u2194 Contact matches found', 'success');
      } else {
        const payload = {
          object_name: state.dupObjectName,
          match_fields: state.dupMode === 'native' ? [] : state.dupMatchFields,
          mode: state.dupMode,
        };
        r = await fetch('/duplicates/scan', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        }).then(res => res.json());
        if (r.detail) { showToast('Scan error: ' + r.detail, 'error'); return; }
        const objLabel = state.dupObjects
          ? (state.dupObjects.find(o => o.value === state.dupObjectName) || {}).label || state.dupObjectName
          : state.dupObjectName;
        state.dupResults = {
          groups: r.groups || [],
          total_groups: r.total_groups || 0,
          total_records: r.total_records || 0,
          records_scanned: r.records_scanned || 0,
          config: { object_name: state.dupObjectName, match_fields: state.dupMatchFields.slice(), mode: state.dupMode },
        };
        state.dupScanHistory[state.dupObjectName] = {
          label: objLabel,
          type: 'same',
          total_groups: r.total_groups || 0,
          total_records: r.total_records || 0,
          records_scanned: r.records_scanned || 0,
          scannedAt: Date.now(),
          rawResult: state.dupResults,
        };
        showToast('Scan complete \u2014 ' + (r.total_groups || 0) + ' duplicate groups found', 'success');
      }
      state.dupExpanded = {};
      state.dupTab = 'results';
    } catch (err) {
      showToast('Scan failed \u2014 please try again', 'error');
    } finally {
      state.dupLoading = false;
      render();
    }
  }

  // ================================================================
  // DOWNLOAD HELPERS
  // ================================================================
  function downloadCSV(filename, rows) {
    const lines = rows.map(row =>
      row.map(cell => {
        const s = cell == null ? '' : String(cell);
        return /[,"\n\r]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
      }).join(',')
    );
    const csv = '\uFEFF' + lines.join('\r\n'); // BOM for Excel UTF-8
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = filename;
    document.body.appendChild(a); a.click();
    document.body.removeChild(a); URL.revokeObjectURL(url);
  }

  function downloadDupResults() {
    if (!state.dupResults) return;
    const isCross = state.dupObjectName === '_cross_lead_contact';
    if (isCross) {
      const matches = state.dupResults.matches || [];
      const rows = [['Lead ID','Lead Name','Lead Email','Lead Phone','Lead Company','Lead Status','Contact ID','Contact Name','Contact Email','Contact Phone','Matched On']];
      for (const m of matches) {
        const lead = m.lead || {};
        for (const c of (m.contacts || [])) {
          rows.push([lead.Id||'', lead.Name||'', lead.Email||'', lead.Phone||'', lead.Company||'', lead.Status||'', c.Id||'', c.Name||'', c.Email||'', c.Phone||'', (m.matched_on||[]).join('; ')]);
        }
      }
      downloadCSV('lead-contact-duplicates.csv', rows);
    } else {
      const groups = state.dupResults.groups || [];
      const objName = (state.dupResults.config && state.dupResults.config.object_name) || 'records';
      const rows = [['Group #','Record ID','Name','Created Date','Last Modified Date','Is Master']];
      for (const g of groups) {
        for (let i = 0; i < g.records.length; i++) {
          const r = g.records[i];
          rows.push([g.group_id + 1, r.Id||'', r.Name||'', r.CreatedDate ? new Date(r.CreatedDate).toLocaleDateString() : '', r.LastModifiedDate ? new Date(r.LastModifiedDate).toLocaleDateString() : '', i === 0 ? 'Yes' : 'No']);
        }
      }
      downloadCSV(objName.toLowerCase() + '-duplicates.csv', rows);
    }
  }

  function downloadDupOverview() {
    const history = state.dupScanHistory;
    const rows = [['Object','Scan Type','Records Scanned','Affected Records','Duplicate Groups','Duplicate Rate %','Last Scanned']];
    for (const k of Object.keys(history)) {
      const h = history[k];
      const scanned = h.records_scanned || 0;
      const affected = h.total_records || 0;
      const pct = scanned > 0 ? ((affected / scanned) * 100).toFixed(1) : '0.0';
      rows.push([h.label||k, h.type === 'cross' ? 'Cross-object (Lead-Contact)' : 'Same-object', scanned, affected, h.total_groups||0, pct + '%', h.scannedAt ? new Date(h.scannedAt).toLocaleString() : '']);
    }
    downloadCSV('duplicate-overview.csv', rows);
  }

  async function deleteDuplicateRecord(objectName, recordId, groupId, btn) {
    if (!confirm('Permanently delete record ' + recordId + ' from Salesforce? This cannot be undone.')) return;
    if (btn) { btn.disabled = true; btn.innerHTML = '<span class="spinner spinner-dark"></span>'; }
    try {
      const r = await fetch('/duplicates/records/' + objectName + '/' + recordId, { method: 'DELETE' })
        .then(res => res.json());
      if (r.status === 'ok') {
        if (state.dupResults && state.dupResults.groups) {
          for (const g of state.dupResults.groups) {
            g.records = g.records.filter(rec => rec.Id !== recordId);
            g.count = g.records.length;
          }
          state.dupResults.groups = state.dupResults.groups.filter(g => g.count >= 2);
          state.dupResults.total_groups = state.dupResults.groups.length;
          state.dupResults.total_records = state.dupResults.groups.reduce(function(s, g) { return s + g.count; }, 0);
        }
        showToast('Record deleted', 'success');
        render();
      } else {
        showToast('Error: ' + (r.detail || 'Delete failed'), 'error');
        if (btn) { btn.disabled = false; btn.innerHTML = I.trash + ' Delete'; }
      }
    } catch (err) {
      showToast('Delete failed \u2014 please try again', 'error');
      if (btn) { btn.disabled = false; btn.innerHTML = I.trash + ' Delete'; }
    }
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
  function setDashPage(n) {
    state.dashPage = n;
    render();
  }

  window.OrgScan = { navigate, writeDesc, cancelDesc, generateDesc, showFinding, closeModal, setDashPage, state, render };

  // One-time delegated listener for inline detail expand buttons.
  // Registered once here rather than inside bindEvents() to avoid accumulation.
  document.addEventListener('click', function (e) {
    const btn = e.target.closest('.finding-expand-btn');
    if (!btn) return;
    const idx = btn.dataset.idx;
    const extra = document.getElementById('fde-' + idx);
    if (!extra) return;
    const open = extra.style.display !== 'none';
    extra.style.display = open ? 'none' : 'block';
    const lineCount = extra.querySelectorAll('li').length;
    btn.textContent = open ? '+' + lineCount + ' more' : 'less';
  });

  init();

}());
