// AquaSure Main — shared utilities for all pages

(function (window) {
  'use strict';

  // ── Toast ──────────────────────────────────────────────────────────────────

  function showToast(msg, type) {
    const container = document.getElementById('toastContainer');
    if (!container) return;
    const el = document.createElement('div');
    el.className = `toast ${type || 'info'}`;
    const icon = type === 'success' ? '✓' : type === 'error' ? '✕' : 'ℹ';
    el.innerHTML = `<span style="font-size:1rem">${icon}</span><span>${_escHtml(msg)}</span>`;
    container.appendChild(el);
    setTimeout(() => { el.style.opacity = '0'; el.style.transition = 'opacity .3s'; setTimeout(() => el.remove(), 300); }, 4000);
  }

  function showError(msg)   { showToast(msg, 'error'); }
  function showSuccess(msg) { showToast(msg, 'success'); }

  // ── Number / escape helpers ────────────────────────────────────────────────

  function formatNumber(n, decimals) {
    const d = typeof decimals === 'number' ? decimals : 0;
    const v = parseFloat(n);
    if (!isFinite(v)) return '—';
    return v.toLocaleString('en-IN', { minimumFractionDigits: d, maximumFractionDigits: d });
  }

  function _escHtml(str) {
    return String(str || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  // ── Nav toggle ─────────────────────────────────────────────────────────────

  function _initNav() {
    const toggle = document.getElementById('navToggle');
    const links  = document.getElementById('navLinks');
    if (toggle && links) {
      toggle.addEventListener('click', () => links.classList.toggle('open'));
      links.querySelectorAll('a').forEach(a => a.addEventListener('click', () => links.classList.remove('open')));
    }
    // Auto-highlight active page
    const page = location.pathname.split('/').pop() || 'index.html';
    document.querySelectorAll('.nav-links a').forEach(a => {
      const href = (a.getAttribute('href') || '').split('/').pop().split('?')[0];
      if (href === page) a.classList.add('active');
    });
  }

  document.addEventListener('DOMContentLoaded', _initNav);

  window.showToast    = showToast;
  window.showError    = showError;
  window.showSuccess  = showSuccess;
  window.formatNumber = formatNumber;

})(window);
