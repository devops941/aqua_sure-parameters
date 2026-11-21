// AquaSure Compare — district comparison charts
// Requires: api.js, main.js, Chart.js

(function (window) {
  'use strict';

  const PARAM_LABELS = {
    ph: 'pH', tds: 'TDS', ec: 'EC', hardness: 'Hardness',
    ca: 'Calcium', mg: 'Magnesium', cl: 'Chloride',
    so4: 'Sulphate', no3: 'Nitrate', f: 'Fluoride',
  };
  const DATASET_COLORS = ['#0284c7', '#16a34a', '#d97706', '#dc2626'];

  let _wqiChart = null, _param1Chart = null, _param2Chart = null;

  function _destroyAll() {
    [_wqiChart, _param1Chart, _param2Chart].forEach(c => c && c.destroy());
    _wqiChart = _param1Chart = _param2Chart = null;
  }

  function _chartOpts() {
    return {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { labels: { color: '#334155', font: { size: 11 } } },
        tooltip: { backgroundColor: '#0f172a', borderColor: '#334155', borderWidth: 1, titleColor: '#e2e8f0', bodyColor: '#94a3b8' },
      },
      scales: {
        x: { grid: { color: '#e2e8f0' }, ticks: { color: '#64748b' } },
        y: { grid: { color: '#e2e8f0' }, ticks: { color: '#64748b' }, beginAtZero: true },
      },
    };
  }

  function _esc(s) {
    return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }

  function _gradeClass(grade) {
    return ({ A:'badge-grade-a', B:'badge-grade-b', C:'badge-grade-c', D:'badge-grade-d', E:'badge-grade-e' })[grade] || 'badge-info';
  }

  // ── Populate district dropdowns ────────────────────────────────────────────
  async function _populateDropdowns() {
    try {
      const districts = await AquaSureAPI.getDistricts();
      const opts = districts.map(d => `<option value="${_esc(d.district)}">${_esc(d.district)}</option>`).join('');
      ['district1','district2','district3','district4'].forEach(id => {
        const sel = document.getElementById(id);
        if (sel) sel.innerHTML = '<option value="">— Select —</option>' + opts;
      });
    } catch (err) {
      console.error('Compare: failed to load districts', err);
    }
  }

  // ── Build comparison ───────────────────────────────────────────────────────
  async function _runComparison() {
    const names = ['district1','district2','district3','district4']
      .map(id => (document.getElementById(id)?.value || '').trim())
      .filter(Boolean);

    const errEl = document.getElementById('compareError');
    if (names.length < 2) {
      if (errEl) errEl.style.display = '';
      return;
    }
    if (errEl) errEl.style.display = 'none';

    // Show loading, hide others
    document.getElementById('compareLoading').style.display = '';
    document.getElementById('compareResults').classList.remove('visible');
    document.getElementById('compareEmpty').style.display = 'none';

    try {
      const data = await AquaSureAPI.getDistrictComparison(names);
      _destroyAll();
      _renderSummary(data);
      _renderWQIChart(data);
      _renderParamChart1(data);
      _renderParamChart2(data);
      _renderTable(data);
      document.getElementById('compareResults').classList.add('visible');
    } catch (err) {
      console.error('Compare error:', err);
      showError('Comparison failed. Make sure the backend is running.');
      document.getElementById('compareEmpty').style.display = '';
    } finally {
      document.getElementById('compareLoading').style.display = 'none';
    }
  }

  function _renderSummary(data) {
    const row = document.getElementById('compareSummaryRow');
    if (!row) return;
    row.innerHTML = data.map((d, i) => {
      const grade = gradeFromWQI(d.mean_wqi);
      const color = gradeColor(grade);
      const colorVar = DATASET_COLORS[i];
      return `<div class="card card-padded" style="border-top:3px solid ${colorVar}">
        <div class="kpi-label">${_esc(d.district)}</div>
        <div class="kpi-value" style="font-size:1.5rem;color:${colorVar}">${formatWQI(d.mean_wqi)}</div>
        <div style="margin-top:.4rem">
          <span class="badge ${_gradeClass(grade)}" style="margin-right:.4rem">Grade ${grade}</span>
          <span style="font-size:.78rem;color:var(--text-muted)">${(d.potable_pct||0).toFixed(1)}% potable</span>
        </div>
      </div>`;
    }).join('');
  }

  function _renderWQIChart(data) {
    const ctx = document.getElementById('compareWQIChart');
    if (!ctx) return;
    _wqiChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: data.map(d => d.district),
        datasets: [{
          label: 'Mean WQI',
          data: data.map(d => d.mean_wqi || 0),
          backgroundColor: DATASET_COLORS.slice(0, data.length).map(c => c + '33'),
          borderColor: DATASET_COLORS.slice(0, data.length),
          borderWidth: 2, borderRadius: 5,
        }],
      },
      options: { ..._chartOpts(), plugins: { ..._chartOpts().plugins, legend: { display: false } } },
    });
  }

  function _renderParamChart1(data) {
    const ctx = document.getElementById('compareParamChart1');
    if (!ctx) return;
    const params = ['ph', 'tds'];
    _param1Chart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: params.map(p => PARAM_LABELS[p]),
        datasets: data.map((d, i) => ({
          label: d.district,
          data: params.map(p => d.parameter_averages?.[p] || 0),
          backgroundColor: DATASET_COLORS[i] + '33',
          borderColor: DATASET_COLORS[i],
          borderWidth: 2, borderRadius: 4,
        })),
      },
      options: _chartOpts(),
    });
  }

  function _renderParamChart2(data) {
    const ctx = document.getElementById('compareParamChart2');
    if (!ctx) return;
    const params = ['no3', 'f'];
    _param2Chart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: params.map(p => PARAM_LABELS[p]),
        datasets: data.map((d, i) => ({
          label: d.district,
          data: params.map(p => d.parameter_averages?.[p] || 0),
          backgroundColor: DATASET_COLORS[i] + '33',
          borderColor: DATASET_COLORS[i],
          borderWidth: 2, borderRadius: 4,
        })),
      },
      options: _chartOpts(),
    });
  }

  function _renderTable(data) {
    const head = document.getElementById('compareTableHead');
    const body = document.getElementById('compareTableBody');
    if (!head || !body) return;

    head.innerHTML = '<tr><th>Parameter</th>' +
      data.map((d,i) => `<th style="color:${DATASET_COLORS[i]};text-align:right">${_esc(d.district)}</th>`).join('') + '</tr>';

    const params = Object.keys(PARAM_LABELS);
    body.innerHTML = params.map(p => {
      const cells = data.map(d => {
        const v = d.parameter_averages?.[p];
        return `<td style="text-align:right">${v != null ? parseFloat(v).toFixed(2) : '—'}</td>`;
      }).join('');
      return `<tr><td>${PARAM_LABELS[p]}</td>${cells}</tr>`;
    }).join('');
  }

  // ── Init ───────────────────────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('navToggle')?.addEventListener('click', () => {
      document.getElementById('navLinks')?.classList.toggle('open');
    });

    _populateDropdowns();

    document.getElementById('compareBtn')?.addEventListener('click', _runComparison);

    document.getElementById('clearCompareBtn')?.addEventListener('click', () => {
      ['district1','district2','district3','district4'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.value = '';
      });
      _destroyAll();
      document.getElementById('compareResults').classList.remove('visible');
      document.getElementById('compareEmpty').style.display = '';
    });
  });

})(window);
