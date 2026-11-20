// AquaSure API Client — all fetch calls to Flask backend
// Exposes window.AquaSureAPI, gradeColor, formatWQI, gradeFromWQI, formatNumber

(function (window) {
  'use strict';

  const API_BASE = 'http://localhost:5000';

  const GRADE_COLORS = {
    A: '#16a34a',
    B: '#0284c7',
    C: '#d97706',
    D: '#ea580c',
    E: '#dc2626',
  };

  function gradeColor(grade) {
    return GRADE_COLORS[String(grade).toUpperCase()] || '#94a3b8';
  }

  function formatWQI(val) {
    const n = parseFloat(val);
    return isFinite(n) ? n.toFixed(1) : '—';
  }

  function gradeFromWQI(wqi) {
    const n = parseFloat(wqi);
    if (!isFinite(n)) return '?';
    if (n <= 25)  return 'A';
    if (n <= 50)  return 'B';
    if (n <= 75)  return 'C';
    if (n <= 100) return 'D';
    return 'E';
  }

  function formatNumber(val, decimals) {
    const n = parseFloat(val);
    if (!isFinite(n)) return '—';
    if (decimals === 0) return Math.round(n).toLocaleString();
    return n.toFixed(decimals !== undefined ? decimals : 1);
  }

  // ── HTTP helpers ────────────────────────────────────────────────────────────

  async function _get(path) {
    const res = await fetch(API_BASE + path);
    if (!res.ok) throw new Error(`HTTP ${res.status} – ${path}`);
    return res.json();
  }

  async function _post(path, body) {
    const res = await fetch(API_BASE + path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      let msg = `HTTP ${res.status}`;
      try { const j = await res.json(); msg = j.error || msg; } catch (_) {}
      throw new Error(msg);
    }
    return res.json();
  }

  async function _postBlob(path, body) {
    const res = await fetch(API_BASE + path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.blob();
  }

  // ── API ─────────────────────────────────────────────────────────────────────

  const AquaSureAPI = {
    getOverview()          { return _get('/api/overview'); },
    getDistricts()         { return _get('/api/districts'); },
    getDistrict(name)      { return _get(`/api/district/${encodeURIComponent(name)}`); },
    getTrends()            { return _get('/api/trends'); },
    getParameters()        { return _get('/api/parameters'); },
    getCorrelation()       { return _get('/api/correlation'); },

    calculateWQI(params)   { return _post('/api/calculate-wqi', params); },
    assessWater(data)      { return _post('/api/assess-water',  data); },

    getSensitivity(param, params) {
      const qs = new URLSearchParams({ param, ...params });
      return _get(`/api/sensitivity?${qs.toString()}`);
    },

    getDistrictComparison(names) {
      const qs = new URLSearchParams({ districts: names.join(',') });
      return _get(`/api/district-comparison?${qs.toString()}`);
    },

    generatePDF(data) {
      return _postBlob('/api/generate-pdf', data);
    },
  };

  // expose globally
  window.AquaSureAPI  = AquaSureAPI;
  window.gradeColor   = gradeColor;
  window.formatWQI    = formatWQI;
  window.gradeFromWQI = gradeFromWQI;
  window.formatNumber = formatNumber;

})(window);
