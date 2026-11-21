// AquaSure Districts – cards, search/filter/sort, detail modal
// Requires: api.js, main.js, Chart.js (CDN)

(function (window) {
  'use strict';

  let _allDistricts  = [];
  let _trendChart    = null;
  let _overviewChart = null;

  // ------------------------------------------------------------------ grade helper

  const STATUS_TO_GRADE = {
    'Excellent': 'A', 'Good': 'B', 'Poor': 'C',
    'Very Poor': 'D', 'Unsuitable for Drinking': 'E',
  };

  function _gradeFromDistrict(d) {
    return STATUS_TO_GRADE[d.overall_status] || gradeFromWQI(d.mean_wqi || 0);
  }

  function _esc(str) {
    return String(str || '')
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  // ------------------------------------------------------------------ card build

  function _buildCard(d) {
    const grade   = _gradeFromDistrict(d);
    const color   = gradeColor(grade);
    const wqi     = parseFloat(d.mean_wqi || 0).toFixed(1);
    const potable = parseFloat(d.potable_pct || 0).toFixed(1);

    const card = document.createElement('div');
    card.className = 'district-card';
    card.style.cursor = 'pointer';
    card.style.borderTop = `3px solid ${color}`;
    card.dataset.district = d.district;
    card.dataset.grade    = grade;
    card.dataset.wqi      = d.mean_wqi || 0;
    card.dataset.potable  = d.potable_pct || 0;

    card.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:.6rem">
        <h3 style="font-size:1rem;font-weight:600;color:#0f172a;margin:0">${_esc(d.district)}</h3>
        <span style="background:${color}22;color:${color};border:1px solid ${color}55;padding:.15rem .55rem;border-radius:999px;font-size:.72rem;font-weight:700">
          Grade ${grade}
        </span>
      </div>
      <div style="display:flex;align-items:baseline;gap:.35rem;margin-bottom:.5rem">
        <span style="font-size:1.9rem;font-weight:700;color:${color}">${wqi}</span>
        <span style="font-size:.78rem;color:#64748b">Avg WQI</span>
      </div>
      <div style="display:flex;justify-content:space-between;font-size:.78rem;color:#94a3b8">
        <span>Potable: <strong>${potable}%</strong></span>
        <span>Samples: <strong>${formatNumber(d.total_samples || 0, 0)}</strong></span>
      </div>`;

    card.addEventListener('click', () => _openModal(d.district));
    return card;
  }

  // ------------------------------------------------------------------ grid render

  function _renderGrid(districts) {
    const grid = document.getElementById('districtsGrid');
    if (!grid) return;
    grid.innerHTML = '';
    if (!districts.length) {
      grid.innerHTML = '<p style="color:#94a3b8;grid-column:1/-1;text-align:center;padding:3rem">No districts match your filter.</p>';
    } else {
      districts.forEach(d => grid.appendChild(_buildCard(d)));
    }
    // Update counts
    const shown = document.getElementById('shownCount');
    const total = document.getElementById('totalCount');
    if (shown) shown.textContent = districts.length;
    if (total) total.textContent = _allDistricts.length;
  }

  // ------------------------------------------------------------------ stats bar

  function _updateStatsBar(districts) {
    const totalSamples = districts.reduce((s, d) => s + (d.total_samples || 0), 0);
    const avgPotable   = districts.reduce((s, d) => s + (d.potable_pct || 0), 0) / (districts.length || 1);
    const avgWQI       = districts.reduce((s, d) => s + (d.mean_wqi || 0), 0) / (districts.length || 1);

    const tsEl = document.getElementById('totalSamplesBar');
    const apEl = document.getElementById('avgPotable');
    const wEl  = document.getElementById('stateAvgWQI');
    if (tsEl) tsEl.textContent = formatNumber(totalSamples, 0);
    if (apEl) apEl.textContent = avgPotable.toFixed(1) + '%';
    if (wEl)  wEl.textContent  = avgWQI.toFixed(1);
  }

  // ------------------------------------------------------------------ filter / sort

  function _applyFilters() {
    const search = (document.getElementById('districtSearch')?.value || '').toLowerCase();
    const grade  = (document.getElementById('gradeFilter')?.value  || '');
    const sort   = (document.getElementById('sortSelect')?.value   || 'name');

    let filtered = _allDistricts.filter(d => {
      const matchName  = !search || d.district.toLowerCase().includes(search);
      const matchGrade = !grade  || _gradeFromDistrict(d) === grade;
      return matchName && matchGrade;
    });

    filtered.sort((a, b) => {
      if (sort === 'wqi_asc')      return (a.mean_wqi || 0) - (b.mean_wqi || 0);
      if (sort === 'wqi_desc')     return (b.mean_wqi || 0) - (a.mean_wqi || 0);
      if (sort === 'potable_desc') return (b.potable_pct || 0) - (a.potable_pct || 0);
      return a.district.localeCompare(b.district);
    });

    _renderGrid(filtered);
  }

  // ------------------------------------------------------------------ modal close

  function _closeModal() {
    const modal = document.getElementById('districtModal');
    if (!modal) return;
    modal.classList.remove('active');
    modal.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
  }

  // ------------------------------------------------------------------ modal open

  function _openModal(districtName) {
    const modal = document.getElementById('districtModal');
    if (!modal) return;

    // Reset modal content
    _resetModal();

    // Open modal
    modal.classList.add('active');
    modal.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';

    // Populate from cache immediately
    const cached = _allDistricts.find(d => d.district === districtName);
    if (cached) _fillModalBasic(cached);

    // Fetch full detail
    AquaSureAPI.getDistrict(districtName)
      .then(detail => _fillModalDetail(detail))
      .catch(err => {
        console.error('District detail error:', err);
        const excEl = document.getElementById('modalExceedances');
        if (excEl) excEl.innerHTML = '<p style="color:#ef4444">Could not load parameter data.</p>';
      });
  }

  function _resetModal() {
    const ids = ['modalAvgWQI','modalGrade','modalPotablePct','modalSampleCount',
                 'modalPH','modalTDS','modalNitrate','modalFluoride'];
    ids.forEach(id => {
      const el = document.getElementById(id);
      if (el) el.textContent = '—';
    });
    const noteEl = document.getElementById('modalPotabilityNote');
    if (noteEl) noteEl.textContent = 'Loading district data…';
    const excEl = document.getElementById('modalExceedances');
    if (excEl) excEl.innerHTML = '<p style="color:#94a3b8;font-size:.875rem">Loading parameter data…</p>';
  }

  // ------------------------------------------------------------------ modal fill

  function _fillModalBasic(d) {
    const grade = _gradeFromDistrict(d);
    const color = gradeColor(grade);

    // Title
    const titleEl = document.getElementById('modalTitle');
    if (titleEl) titleEl.textContent = d.district;

    // Grade pill + WQI in meta row
    const metaEl = document.getElementById('modalDistrictMeta');
    if (metaEl) {
      metaEl.innerHTML = `
        <span style="background:${color}22;color:${color};border:1px solid ${color}55;padding:.15rem .6rem;border-radius:999px;font-size:.8rem;font-weight:700;margin-right:.6rem">
          Grade ${grade}
        </span>
        <span style="color:${color};font-size:1.1rem;font-weight:700">WQI ${formatWQI(d.mean_wqi)}</span>`;
    }

    // Overview tab fields
    const set = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.textContent = isFinite(parseFloat(val)) ? parseFloat(val).toFixed(2) : '—';
    };
    set('modalAvgWQI',     d.mean_wqi);
    set('modalPotablePct', null); // fill as string below
    set('modalSampleCount', null);

    const potEl = document.getElementById('modalPotablePct');
    if (potEl) potEl.textContent = `${parseFloat(d.potable_pct || 0).toFixed(1)}%`;

    const sampEl = document.getElementById('modalSampleCount');
    if (sampEl) sampEl.textContent = formatNumber(d.total_samples || 0, 0);

    const gradeEl = document.getElementById('modalGrade');
    if (gradeEl) {
      gradeEl.textContent  = `Grade ${grade} — ${d.overall_status || ''}`;
      gradeEl.style.color  = color;
    }

    // Potability note
    const noteEl = document.getElementById('modalPotabilityNote');
    if (noteEl) {
      const potable = parseFloat(d.potable_pct || 0);
      noteEl.textContent = `${potable.toFixed(1)}% of samples are potable in ${d.district}. ${
        potable >= 50 ? 'Groundwater quality is relatively acceptable.' :
        potable >= 25 ? 'Significant proportion requires treatment.' :
        'Most samples require treatment or are non-potable.'}`;
    }
  }

  function _fillModalDetail(d) {
    // Update parameter averages from full detail
    const params = d.parameter_averages || {};
    const set = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.textContent = isFinite(parseFloat(val)) ? parseFloat(val).toFixed(2) : '—';
    };
    set('modalPH',      params.ph);
    set('modalTDS',     params.tds);
    set('modalNitrate', params.no3);
    set('modalFluoride',params.f);

    // Trend chart
    _renderTrendChart(d.yearly_trend || []);

    // Exceedances
    _renderExceedances(d.exceedances || {});
  }

  // ------------------------------------------------------------------ trend chart

  function _renderTrendChart(yearly) {
    const container = document.querySelector('#tabTrends .chart-wrap');
    const placeholder = document.querySelector('#tabTrends .trend-placeholder');
    const canvas = document.getElementById('districtTrendChart');

    if (!canvas) return;
    if (!yearly.length) return;

    if (placeholder) placeholder.style.display = 'none';
    if (container)   container.style.display   = '';

    if (_trendChart) { _trendChart.destroy(); _trendChart = null; }

    _trendChart = new Chart(canvas, {
      type: 'line',
      data: {
        labels: yearly.map(r => r.year),
        datasets: [
          {
            label: 'Avg WQI',
            data: yearly.map(r => r.avg_wqi),
            borderColor: '#06b6d4',
            backgroundColor: 'rgba(6,182,212,0.08)',
            tension: 0.4,
            fill: true,
            pointBackgroundColor: '#06b6d4',
            pointRadius: 4,
            yAxisID: 'y',
          },
          {
            label: 'Potable %',
            data: yearly.map(r => r.potable_pct),
            borderColor: '#10b981',
            backgroundColor: 'transparent',
            tension: 0.4,
            borderDash: [4, 3],
            pointBackgroundColor: '#10b981',
            pointRadius: 4,
            yAxisID: 'y1',
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { labels: { color: '#94a3b8', font: { size: 11 } } },
          tooltip: { backgroundColor: '#0f172a', borderColor: '#334155', borderWidth: 1, titleColor: '#e2e8f0', bodyColor: '#94a3b8' },
        },
        scales: {
          x:  { grid: { color: '#1e293b' }, ticks: { color: '#94a3b8' } },
          y:  { grid: { color: '#1e293b' }, ticks: { color: '#94a3b8' }, title: { display: true, text: 'WQI', color: '#64748b' } },
          y1: { grid: { display: false }, ticks: { color: '#10b981' }, position: 'right', title: { display: true, text: 'Potable %', color: '#10b981' } },
        },
      },
    });
  }

  // ------------------------------------------------------------------ overview chart

  function _renderOverviewChart(districts) {
    const canvas = document.getElementById('allDistrictsChart');
    if (!canvas) return;

    const sorted = [...districts].sort((a, b) => (a.mean_wqi || 0) - (b.mean_wqi || 0));
    const labels = sorted.map(d => d.district);
    const data   = sorted.map(d => parseFloat(d.mean_wqi || 0).toFixed(1));
    const colors = sorted.map(d => gradeColor(_gradeFromDistrict(d)));

    if (_overviewChart) { _overviewChart.destroy(); _overviewChart = null; }

    _overviewChart = new Chart(canvas, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: 'Avg WQI',
          data: data,
          backgroundColor: colors,
          borderRadius: 4,
          borderWidth: 0,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: {
          duration: 1000,
          easing: 'easeOutQuart',
          delay: function (context) {
            if (context.type === 'data' && context.mode === 'default') {
              return context.dataIndex * 25;
            }
            return 0;
          },
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: '#0f172a',
            titleColor: '#fff',
            bodyColor: '#e2e8f0',
            callbacks: {
              label: function (context) {
                return 'WQI: ' + context.parsed.y;
              },
              afterLabel: function (context) {
                const d = sorted[context.dataIndex];
                return [
                  'Potable: ' + parseFloat(d.potable_pct || 0).toFixed(1) + '%',
                  'Samples: ' + (d.total_samples || 0),
                ];
              },
            },
          },
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: {
              maxRotation: 90,
              minRotation: 45,
              autoSkip: false,
              font: { size: 10 },
              color: '#64748b',
            },
          },
          y: {
            beginAtZero: true,
            grid: { color: '#e2e8f0' },
            ticks: { color: '#64748b' },
            title: { display: true, text: 'WQI Score', color: '#475569' },
          },
        },
      },
    });
  }

  // ------------------------------------------------------------------ exceedances

  function _renderExceedances(exceedances) {
    const container = document.getElementById('modalExceedances');
    if (!container) return;

    const entries = Object.entries(exceedances);
    if (!entries.length) {
      container.innerHTML = '<p style="color:#10b981;font-size:.875rem">&#10003; No significant parameter exceedances.</p>';
      return;
    }

    const rows = entries
      .filter(([, e]) => e.exceed_permissible_pct > 0)
      .sort(([, a], [, b]) => b.exceed_permissible_pct - a.exceed_permissible_pct)
      .map(([key, e]) => `
        <div style="display:flex;justify-content:space-between;align-items:center;padding:.45rem 0;border-bottom:1px solid #1e293b;font-size:.82rem">
          <span style="color:#e2e8f0;font-weight:500;min-width:90px">${key.toUpperCase()}</span>
          <span style="color:#f97316">${e.exceed_permissible_pct.toFixed(1)}% exceed limit</span>
          <span style="color:#94a3b8">Limit: ${e.standard_permissible} ${e.unit}</span>
        </div>`).join('');

    container.innerHTML = rows || '<p style="color:#10b981;font-size:.875rem">&#10003; All parameters within permissible limits.</p>';
  }

  // ------------------------------------------------------------------ init

  async function _init() {
    const grid = document.getElementById('districtsGrid');

    try {
      _allDistricts = await AquaSureAPI.getDistricts();
    } catch (err) {
      console.error('Districts fetch error:', err);
      const loaderEl = document.getElementById('districtsLoading');
      if (loaderEl) loaderEl.style.display = 'none';
      if (grid) grid.innerHTML = '<p style="color:#ef4444;grid-column:1/-1;text-align:center;padding:3rem">Failed to load districts. Make sure the backend is running on port 5000.</p>';
      return;
    }

    _updateStatsBar(_allDistricts);
    _renderGrid(_allDistricts);
    _renderOverviewChart(_allDistricts);

    // Hide loader, reveal grid
    const loaderEl = document.getElementById('districtsLoading');
    if (loaderEl) loaderEl.style.display = 'none';
    if (grid) grid.style.display = '';

    // Bind filters
    const searchEl = document.getElementById('districtSearch');
    const gradeEl  = document.getElementById('gradeFilter');
    const sortEl   = document.getElementById('sortSelect');
    if (searchEl) searchEl.addEventListener('input',  _applyFilters);
    if (gradeEl)  gradeEl.addEventListener('change',  _applyFilters);
    if (sortEl)   sortEl.addEventListener('change',   _applyFilters);

    // Bug 2: modal close — close button, backdrop click, Escape key
    const closeBtn = document.getElementById('modalClose');
    if (closeBtn) closeBtn.addEventListener('click', _closeModal);

    const modalBackdrop = document.getElementById('districtModal');
    if (modalBackdrop) {
      modalBackdrop.addEventListener('click', function (e) {
        if (e.target === modalBackdrop) _closeModal();
      });
    }

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') {
        const modal = document.getElementById('districtModal');
        if (modal && modal.classList.contains('active')) _closeModal();
      }
    });

    // Bug 3: modal tab switching
    const tabBtns = document.querySelectorAll('#modalTabs .tab-btn');
    tabBtns.forEach(function (btn) {
      btn.addEventListener('click', function () {
        document.querySelectorAll('#modalTabs .tab-btn').forEach(function (b) { b.classList.remove('active'); });
        document.querySelectorAll('.tab-panel').forEach(function (p) { p.classList.remove('active'); });
        btn.classList.add('active');
        const panel = document.getElementById(btn.dataset.tab);
        if (panel) panel.classList.add('active');
      });
    });
  }

  document.addEventListener('DOMContentLoaded', _init);

})(window);
