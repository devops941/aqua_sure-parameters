// AquaSure Calculator – WQI form, results panel, sensitivity chart
// Requires: api.js, main.js, Chart.js (CDN)

(function (window) {
  'use strict';

  // Map: backend param key → HTML input ID
  const INPUT_ID_MAP = {
    ph:       'inp_pH',
    tds:      'inp_TDS',
    ec:       'inp_EC',
    hardness: 'inp_Hardness',
    ca:       'inp_Calcium',
    mg:       'inp_Magnesium',
    cl:       'inp_Chloride',
    so4:      'inp_Sulphate',
    no3:      'inp_Nitrate',
    f:        'inp_Fluoride',
  };

  // Map: sensitivity select value → backend param key
  const SENSITIVITY_VAL_MAP = {
    'pH':       'ph',
    'TDS':      'tds',
    'EC':       'ec',
    'Hardness': 'hardness',
    'Calcium':  'ca',
    'Magnesium':'mg',
    'Chloride': 'cl',
    'Sulphate': 'so4',
    'Nitrate':  'no3',
    'Fluoride': 'f',
  };

  const PARAM_NAMES = {
    ph:       'pH',
    tds:      'TDS (mg/L)',
    ec:       'EC (µS/cm)',
    hardness: 'Hardness (mg/L)',
    ca:       'Calcium (mg/L)',
    mg:       'Magnesium (mg/L)',
    cl:       'Chloride (mg/L)',
    so4:      'Sulphate (mg/L)',
    no3:      'Nitrate (mg/L)',
    f:        'Fluoride (mg/L)',
  };

  const SAMPLE_VALUES = {
    ph: 7.2, tds: 450, ec: 700, hardness: 200,
    ca: 65, mg: 28, cl: 180, so4: 120, no3: 22, f: 0.7,
  };

  let _sensitivityChart = null;
  let _lastParams = null;

  // ------------------------------------------------------------------ read inputs

  function _getInputs() {
    const params = {};
    Object.entries(INPUT_ID_MAP).forEach(([key, htmlId]) => {
      const el = document.getElementById(htmlId);
      if (el && el.value.trim() !== '') {
        const v = parseFloat(el.value);
        if (isFinite(v)) params[key] = v;
      }
    });
    return params;
  }

  // ------------------------------------------------------------------ animated counter

  function _animateCounter(elId, target, duration) {
    const el = document.getElementById(elId);
    if (!el) return;
    duration = duration || 800;
    const end = parseFloat(target) || 0;
    const start = performance.now();
    function step(now) {
      const progress = Math.min((now - start) / duration, 1);
      const eased    = 1 - Math.pow(1 - progress, 3);
      el.textContent = (end * eased).toFixed(1);
      if (progress < 1) requestAnimationFrame(step);
      else el.textContent = end.toFixed(1);
    }
    requestAnimationFrame(step);
  }

  // ------------------------------------------------------------------ gauge

  function _updateGauge(wqi, color) {
    const fill = document.getElementById('wqiGaugeFill');
    if (!fill) return;
    // Circumference = 2π×40 ≈ 251.2. Scale WQI 0–200 to 0–251.2
    const pct    = Math.min(parseFloat(wqi) / 200, 1);
    const offset = 251.2 * (1 - pct);
    fill.style.strokeDashoffset = offset;
    fill.style.stroke = color;
  }

  // ------------------------------------------------------------------ display results

  function _displayResults(result) {
    const grade = (result.grade || gradeFromWQI(result.wqi)).toUpperCase();
    const color = gradeColor(grade);

    // Hide placeholder, show results
    const placeholder = document.getElementById('resultPlaceholder');
    const loading     = document.getElementById('resultLoading');
    const output      = document.getElementById('resultOutput');
    if (placeholder) placeholder.style.display = 'none';
    if (loading)     loading.style.display     = 'none';
    if (output)      output.style.display      = '';

    // Animated WQI score
    _animateCounter('resultWQIScore', result.wqi);
    _animateCounter('gaugeNumber',    result.wqi);
    _updateGauge(result.wqi, color);

    // Grade badge
    const gradeLetter = document.getElementById('resultGradeLetter');
    const gradeLabel  = document.getElementById('resultGradeLabel');
    const gradeBadge  = document.getElementById('resultGradeBadge');
    if (gradeLetter) gradeLetter.textContent = grade;
    if (gradeLabel)  gradeLabel.textContent  = result.category || '';
    if (gradeBadge)  {
      gradeBadge.style.borderColor = color;
      gradeBadge.style.color       = color;
    }

    // Potability
    const potEl = document.getElementById('resultPotability');
    if (potEl) {
      potEl.textContent = result.potability || '';
      potEl.style.color = result.is_potable ? '#10b981' : '#ef4444';
    }

    // Violations
    const violEl = document.getElementById('violationsList');
    if (violEl) {
      const violations = result.violations || [];
      if (!violations.length) {
        violEl.innerHTML = '<div style="color:#10b981;padding:.5rem 0">&#10003; All parameters within BIS 10500:2012 limits</div>';
      } else {
        violEl.innerHTML = violations.map(v =>
          `<div style="color:#ef4444;padding:.25rem 0">&#9888; ${_esc(typeof v === 'object' ? (v.parameter || JSON.stringify(v)) : v)}</div>`
        ).join('');
      }
    }

    // Sub-index table
    const tbody = document.getElementById('subIndexBody');
    if (tbody && result.sub_indices) {
      tbody.innerHTML = Object.entries(result.sub_indices).map(([key, si]) => {
        const name  = PARAM_NAMES[key] || key.toUpperCase();
        const value = si.value !== undefined ? parseFloat(si.value).toFixed(2) : '—';
        const qi    = si.qi    !== undefined ? parseFloat(si.qi).toFixed(2)    : '—';
        const limit = si.standard_acceptable !== undefined ? si.standard_acceptable : '—';
        return `<tr>
          <td>${_esc(name)}</td>
          <td style="text-align:right">${value}</td>
          <td style="text-align:right">${limit}</td>
          <td style="text-align:right">${qi}</td>
        </tr>`;
      }).join('');
    }
  }

  // ------------------------------------------------------------------ sensitivity

  async function _runSensitivity(paramSelectValue, params) {
    const paramKey = SENSITIVITY_VAL_MAP[paramSelectValue] || paramSelectValue.toLowerCase();
    if (!params[paramKey]) return;

    const wrap = document.getElementById('sensitivityChartWrap');
    const notice = document.getElementById('sensitivityNotice');
    if (wrap)   wrap.style.display   = '';
    if (notice) notice.style.display = 'none';

    try {
      const response = await AquaSureAPI.getSensitivity(paramKey, params);
      const data = Array.isArray(response) ? response : (response.data || []);
      if (!data.length) return;

      const canvas = document.getElementById('sensitivityChart');
      if (!canvas) return;

      if (_sensitivityChart) { _sensitivityChart.destroy(); _sensitivityChart = null; }

      const xs   = data.map(r => parseFloat(r.value).toFixed(2));
      const wqis = data.map(r => r.wqi);
      const curVal = params[paramKey];
      let closestIdx = 0;
      let closestDist = Infinity;
      data.forEach((r, i) => {
        const d = Math.abs(r.value - curVal);
        if (d < closestDist) { closestDist = d; closestIdx = i; }
      });

      _sensitivityChart = new Chart(canvas, {
        type: 'line',
        data: {
          labels: xs,
          datasets: [
            {
              label: `WQI vs ${paramSelectValue}`,
              data: wqis,
              borderColor: '#06b6d4',
              backgroundColor: 'rgba(6,182,212,0.08)',
              tension: 0.3,
              fill: true,
              pointBackgroundColor: wqis.map((_, i) => i === closestIdx ? '#f59e0b' : '#06b6d4'),
              pointRadius: wqis.map((_, i) => i === closestIdx ? 7 : 2),
            },
            {
              label: 'Grade B boundary (50)',
              data: Array(xs.length).fill(50),
              borderColor: '#10b981',
              borderDash: [5, 4],
              borderWidth: 1.5,
              pointRadius: 0,
              fill: false,
            },
            {
              label: 'Grade E boundary (100)',
              data: Array(xs.length).fill(100),
              borderColor: '#ef4444',
              borderDash: [5, 4],
              borderWidth: 1.5,
              pointRadius: 0,
              fill: false,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { labels: { color: '#94a3b8', font: { size: 11 } } },
            tooltip: {
              backgroundColor: '#0f172a', borderColor: '#334155', borderWidth: 1,
              titleColor: '#e2e8f0', bodyColor: '#94a3b8',
            },
          },
          scales: {
            x: {
              grid: { color: '#1e293b' },
              ticks: { color: '#94a3b8', maxTicksLimit: 10 },
              title: { display: true, text: paramSelectValue, color: '#64748b' },
            },
            y: {
              grid: { color: '#1e293b' },
              ticks: { color: '#94a3b8' },
              title: { display: true, text: 'WQI Score', color: '#64748b' },
              beginAtZero: true,
            },
          },
        },
      });
    } catch (err) {
      console.error('Sensitivity error:', err);
    }
  }

  // ------------------------------------------------------------------ calculate

  async function _handleCalculate(e) {
    if (e) e.preventDefault();

    const params = _getInputs();
    if (!Object.keys(params).length) {
      const errDiv = document.getElementById('formError');
      if (errDiv) errDiv.style.display = '';
      return;
    }

    const errDiv = document.getElementById('formError');
    if (errDiv) errDiv.style.display = 'none';

    // Show loading state
    const placeholder = document.getElementById('resultPlaceholder');
    const loading     = document.getElementById('resultLoading');
    const output      = document.getElementById('resultOutput');
    if (placeholder) placeholder.style.display = 'none';
    if (output)      output.style.display      = 'none';
    if (loading)     loading.style.display      = '';

    const btn = document.getElementById('calcBtn');
    if (btn) { btn.disabled = true; }
    const btnText = document.getElementById('calcBtnText');
    if (btnText) btnText.textContent = 'Calculating…';

    try {
      const result = await AquaSureAPI.calculateWQI(params);
      _lastParams = params;
      _displayResults(result);

      // Auto-run sensitivity for first param
      const sel = document.getElementById('sensitivityParam');
      if (sel && sel.value) {
        await _runSensitivity(sel.value, params);
      }

    } catch (err) {
      console.error('Calculate error:', err);
      if (loading) loading.style.display = 'none';
      if (placeholder) placeholder.style.display = '';
      alert('WQI calculation failed. Make sure the backend is running on port 5000.');
    } finally {
      if (btn) btn.disabled = false;
      if (btnText) btnText.textContent = 'Calculate WQI';
    }
  }

  // ------------------------------------------------------------------ init

  function _init() {
    // Load sample values
    const sampleBtn = document.getElementById('loadSampleBtn');
    if (sampleBtn) {
      sampleBtn.addEventListener('click', () => {
        Object.entries(INPUT_ID_MAP).forEach(([key, htmlId]) => {
          const el = document.getElementById(htmlId);
          if (el) el.value = SAMPLE_VALUES[key] || '';
        });
      });
    }

    // Reset
    const resetBtn = document.getElementById('resetBtn');
    if (resetBtn) {
      resetBtn.addEventListener('click', () => {
        const output  = document.getElementById('resultOutput');
        const placeholder = document.getElementById('resultPlaceholder');
        const wrap    = document.getElementById('sensitivityChartWrap');
        const notice  = document.getElementById('sensitivityNotice');
        if (output)      output.style.display      = 'none';
        if (placeholder) placeholder.style.display = '';
        if (wrap)        wrap.style.display         = 'none';
        if (notice)      notice.style.display        = '';
        _lastParams = null;
      });
    }

    // Calculate button
    const calcBtn = document.getElementById('calcBtn');
    if (calcBtn) calcBtn.addEventListener('click', _handleCalculate);

    // Form submit (Enter)
    const form = document.getElementById('wqiForm');
    if (form) form.addEventListener('submit', _handleCalculate);

    // Run Sensitivity button
    const runBtn = document.getElementById('runSensitivityBtn');
    if (runBtn) {
      runBtn.addEventListener('click', () => {
        const sel = document.getElementById('sensitivityParam');
        const params = _lastParams || _getInputs();
        if (sel && sel.value && Object.keys(params).length) {
          _runSensitivity(sel.value, params);
        } else {
          alert('Please calculate WQI first before running sensitivity analysis.');
        }
      });
    }

    // Hide results initially
    const output  = document.getElementById('resultOutput');
    const loading = document.getElementById('resultLoading');
    const wrap    = document.getElementById('sensitivityChartWrap');
    if (output)  output.style.display  = 'none';
    if (loading) loading.style.display = 'none';
    if (wrap)    wrap.style.display    = 'none';
  }

  function _esc(str) {
    return String(str || '')
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  document.addEventListener('DOMContentLoaded', _init);

})(window);
