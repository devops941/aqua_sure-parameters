// AquaSure Dashboard — KPI cards + four charts (light theme)
// Requires: api.js, main.js, Chart.js

(function (window) {
  'use strict';

  // ── Chart global defaults (light theme) ───────────────────────────────────
  const GRID_COLOR  = '#e2e8f0';
  const TICK_COLOR  = '#64748b';
  const LEGEND_COLOR = '#334155';

  Chart.defaults.color       = TICK_COLOR;
  Chart.defaults.font.family = "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";

  function _baseOptions(extraPlugins) {
    return {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { labels: { color: LEGEND_COLOR, font: { size: 11 } } },
        tooltip: {
          backgroundColor: '#0f172a', borderColor: '#334155', borderWidth: 1,
          titleColor: '#e2e8f0', bodyColor: '#94a3b8',
        },
        ...(extraPlugins || {}),
      },
    };
  }

  function _scaleX(opts) {
    return { grid: { color: GRID_COLOR }, ticks: { color: TICK_COLOR }, ...(opts || {}) };
  }
  function _scaleY(opts) {
    return { grid: { color: GRID_COLOR }, ticks: { color: TICK_COLOR }, beginAtZero: true, ...(opts || {}) };
  }

  const _charts = {};
  function _destroy(key) { if (_charts[key]) { _charts[key].destroy(); delete _charts[key]; } }

  // ── KPI cards ──────────────────────────────────────────────────────────────
  function _updateKPIs(ov) {
    const set = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = v; };
    set('kpiTotalSamples', formatNumber(ov.total_samples, 0));
    set('kpiPotable',      (parseFloat(ov.potable_percent) || 0).toFixed(1) + '%');
    set('kpiAvgWQI',       formatWQI(ov.avg_wqi));
    set('kpiDistricts',    ov.district_count || '—');
  }

  function _hideLoading(id) {
    const el = document.getElementById(id);
    if (el) el.style.display = 'none';
  }

  // ── Grade distribution bar ─────────────────────────────────────────────────
  function _renderGradeChart(gradeDist) {
    _hideLoading('gradeChartLoading');
    const ctx = document.getElementById('gradeChart');
    if (!ctx) return;
    _destroy('grade');

    const labels = ['A', 'B', 'C', 'D', 'E'];
    const data   = labels.map(g => gradeDist[g] || 0);
    const colors = labels.map(g => gradeColor(g));

    _charts.grade = new Chart(ctx, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          label: 'Samples %',
          data,
          backgroundColor: colors.map(c => c + '33'),
          borderColor: colors,
          borderWidth: 2,
          borderRadius: 5,
        }],
      },
      options: {
        ..._baseOptions({ legend: { display: false } }),
        scales: { x: _scaleX(), y: _scaleY() },
      },
    });
  }

  // ── Potability doughnut ────────────────────────────────────────────────────
  function _renderPotabilityChart(ov) {
    _hideLoading('potabilityChartLoading');
    const ctx = document.getElementById('potabilityChart');
    if (!ctx) return;
    _destroy('potability');

    const potable    = ov.potable_count || 0;
    const nonPotable = Math.max(0, (ov.total_samples || 0) - potable);

    _charts.potability = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: ['Potable', 'Non-Potable'],
        datasets: [{
          data: [potable, nonPotable],
          backgroundColor: ['#dcfce7', '#fee2e2'],
          borderColor:     ['#16a34a', '#dc2626'],
          borderWidth: 2,
          hoverOffset: 8,
        }],
      },
      options: {
        ..._baseOptions(),
        cutout: '65%',
        plugins: {
          legend: { position: 'bottom', labels: { color: LEGEND_COLOR, padding: 14, font: { size: 11 } } },
          tooltip: { backgroundColor: '#0f172a', borderColor: '#334155', borderWidth: 1, titleColor: '#e2e8f0', bodyColor: '#94a3b8' },
        },
      },
    });
  }

  // ── WQI trend line ─────────────────────────────────────────────────────────
  function _renderTrendChart(yearly) {
    _hideLoading('trendChartLoading');
    const ctx = document.getElementById('trendChart');
    if (!ctx) return;
    _destroy('trend');

    _charts.trend = new Chart(ctx, {
      type: 'line',
      data: {
        labels: yearly.map(r => r.year),
        datasets: [{
          label: 'Avg WQI',
          data: yearly.map(r => r.avg_wqi),
          borderColor: '#0284c7',
          backgroundColor: 'rgba(2,132,199,.08)',
          tension: 0.4, fill: true,
          pointBackgroundColor: '#0284c7', pointRadius: 4, pointHoverRadius: 6,
        }],
      },
      options: {
        ..._baseOptions(),
        scales: { x: _scaleX(), y: _scaleY({ beginAtZero: false }) },
      },
    });
  }

  // ── District rank horizontal bar ───────────────────────────────────────────
  function _renderDistrictRankChart(districts) {
    _hideLoading('districtRankChartLoading');
    const ctx = document.getElementById('districtRankChart');
    if (!ctx) return;
    _destroy('districtRank');

    const sorted = [...districts]
      .filter(d => d.mean_wqi != null)
      .sort((a, b) => (b.mean_wqi || 0) - (a.mean_wqi || 0))
      .slice(0, 10);

    const colors = sorted.map(d => gradeColor(gradeFromWQI(d.mean_wqi)));

    _charts.districtRank = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: sorted.map(d => d.district),
        datasets: [{
          label: 'Mean WQI',
          data: sorted.map(d => d.mean_wqi || 0),
          backgroundColor: colors.map(c => c + '33'),
          borderColor: colors,
          borderWidth: 2, borderRadius: 4,
        }],
      },
      options: {
        ..._baseOptions({ legend: { display: false } }),
        indexAxis: 'y',
        scales: {
          x: _scaleX({ beginAtZero: true }),
          y: _scaleX({ ticks: { color: TICK_COLOR, font: { size: 10 } } }),
        },
      },
    });
  }

  // ── Init ───────────────────────────────────────────────────────────────────
  async function _init() {
    try {
      const ov = await AquaSureAPI.getOverview();
      _updateKPIs(ov);
      _renderPotabilityChart(ov);
      _renderGradeChart(ov.grade_distribution || {});

      const yr = document.getElementById('yearRangeNote');
      if (yr && ov.year_range) {
        document.getElementById('yearRangeText').textContent =
          `Dataset covers ${ov.year_range[0]} – ${ov.year_range[1]}`;
        yr.style.display = 'flex';
      }
    } catch (err) {
      console.error('Dashboard overview error:', err);
      showError('Could not load overview. Make sure the backend is running on port 5000.');
    }

    try {
      const trends = await AquaSureAPI.getTrends();
      _renderTrendChart(trends.yearly || []);
    } catch (err) {
      console.error('Trends error:', err);
      _hideLoading('trendChartLoading');
    }

    try {
      const districts = await AquaSureAPI.getDistricts();
      _renderDistrictRankChart(districts);
    } catch (err) {
      console.error('Districts error:', err);
      _hideLoading('districtRankChartLoading');
    }
  }

  document.addEventListener('DOMContentLoaded', _init);

})(window);
