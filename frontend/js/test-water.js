// AquaSure Water Test – assessment form submit, sample loader, clear
// Requires: api.js (window.AquaSureAPI), main.js (window.showError, showSuccess, showToast)

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

  // Representative tap-water values used by "Load Sample Values"
  const SAMPLE_VALUES = {
    ph: 7.2, tds: 450, ec: 700, hardness: 200,
    ca: 65, mg: 28, cl: 180, so4: 120, no3: 22, f: 0.7,
  };

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

  // ------------------------------------------------------------------ form submit

  async function _handleAssess(e) {
    if (e) e.preventDefault();

    const params = _getInputs();

    // Require at least one numeric parameter
    if (!Object.keys(params).length) {
      const errDiv = document.getElementById('formError');
      if (errDiv) errDiv.style.display = '';
      if (window.showError) window.showError('Please enter at least one water quality parameter.');
      return;
    }

    // Hide validation error if previously shown
    const errDiv = document.getElementById('formError');
    if (errDiv) errDiv.style.display = 'none';

    // Read optional text fields
    const sampleEl   = document.getElementById('sampleName');
    const districtEl = document.getElementById('districtName');

    const payload = Object.assign({}, params);
    if (sampleEl   && sampleEl.value.trim())   payload.sample_name = sampleEl.value.trim();
    if (districtEl && districtEl.value.trim()) payload.district    = districtEl.value.trim();

    // Show loading state
    const btn        = document.getElementById('assessBtn');
    const btnLoading = document.getElementById('assessBtnLoading');
    if (btn)        btn.disabled          = true;
    if (btnLoading) btnLoading.style.display = 'inline';

    try {
      const response = await window.AquaSureAPI.assessWater(payload);

      // Persist full response for the results page
      sessionStorage.setItem('aquasure_assessment', JSON.stringify(response));
      window.location.href = 'results.html';

    } catch (err) {
      console.error('Assessment error:', err);
      if (btn)        btn.disabled             = false;
      if (btnLoading) btnLoading.style.display = 'none';
      if (window.showError) {
        window.showError('Assessment failed. Make sure the backend is running on port 5000.');
      }
    }
  }

  // ------------------------------------------------------------------ init

  function _init() {
    // Wire up form submit
    const form = document.getElementById('waterTestForm');
    if (form) form.addEventListener('submit', _handleAssess);

    // "Load Sample Values" – fill every param input with known-good values
    const sampleBtn = document.getElementById('loadSampleBtn');
    if (sampleBtn) {
      sampleBtn.addEventListener('click', () => {
        Object.entries(INPUT_ID_MAP).forEach(([key, htmlId]) => {
          const el = document.getElementById(htmlId);
          if (el) el.value = SAMPLE_VALUES[key] !== undefined ? SAMPLE_VALUES[key] : '';
        });
      });
    }

    // "Clear All" – wipe param inputs, text inputs, and hide error banner
    const clearBtn = document.getElementById('clearFormBtn');
    if (clearBtn) {
      clearBtn.addEventListener('click', () => {
        // Clear numeric param inputs
        Object.values(INPUT_ID_MAP).forEach(htmlId => {
          const el = document.getElementById(htmlId);
          if (el) el.value = '';
        });
        // Clear text inputs
        const sampleEl   = document.getElementById('sampleName');
        const districtEl = document.getElementById('districtName');
        if (sampleEl)   sampleEl.value   = '';
        if (districtEl) districtEl.value = '';
        // Hide validation error banner
        const errDiv = document.getElementById('formError');
        if (errDiv) errDiv.style.display = 'none';
      });
    }
  }

  document.addEventListener('DOMContentLoaded', _init);

})(window);
