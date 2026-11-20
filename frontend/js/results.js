// AquaSure Results — reads sessionStorage assessment, populates results.html, drives PDF download
// Requires (loaded before this file): api.js, main.js

(function (window) {
  'use strict';

  // ------------------------------------------------------------------ helpers

  /** Escape text before inserting into innerHTML. */
  function _esc(str) {
    return String(str == null ? '' : str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  /** Set textContent if element exists (silent no-op otherwise). */
  function _setText(id, text) {
    var el = document.getElementById(id);
    if (el) el.textContent = String(text == null ? '' : text);
  }

  /** Set style property if element exists. */
  function _style(id, prop, value) {
    var el = document.getElementById(id);
    if (el) el.style[prop] = value;
  }

  // ------------------------------------------------------------------ sessionStorage read

  /** Load and validate the assessment stored by test-water.js. Returns null on failure. */
  function _loadAssessment() {
    try {
      var raw = sessionStorage.getItem('aquasure_assessment');
      if (!raw) return null;
      var data = JSON.parse(raw);
      // Must be a non-null object with at least one parameter entry
      if (!data || typeof data !== 'object') return null;
      if (!Array.isArray(data.parameters) || !data.parameters.length) return null;
      return data;
    } catch (_) {
      return null;
    }
  }

  // ------------------------------------------------------------------ populate header

  function _populateHeader(data) {
    // Title: sample_name or fallback
    _setText('resultsTitle', data.sample_name || 'Assessment Results');

    // Subtitle: "District · Assessed DATE" (district optional)
    var subtitle = '';
    if (data.district) subtitle += data.district + ' · ';
    subtitle += 'Assessed ' + (data.assessment_date || '');
    _setText('resultsSubtitle', subtitle);
  }

  // ------------------------------------------------------------------ populate grade badge / WQI hero

  function _populateHero(data) {
    var grade = data.grade || '?';
    var color = window.gradeColor(grade);

    // Grade badge
    _setText('gradeLetter', grade);
    _setText('gradeLabel',  data.category || '');
    var badge = document.getElementById('gradeBadge');
    if (badge) {
      badge.style.borderColor = color;
      badge.style.color       = color;
    }

    // WQI score + category
    _setText('wqiScore',    window.formatWQI(data.wqi));
    _setText('wqiCategory', data.category || '');

    // Potability row
    var potEl = document.getElementById('potabilityStatus');
    if (potEl) {
      potEl.textContent = data.potability || '';
      potEl.style.color = data.is_potable ? '#16a34a' : '#dc2626';
    }

    _setText('overallAssessment', data.overall_assessment || '');
  }

  // ------------------------------------------------------------------ parameter table

  /**
   * Returns the CSS color string for a status_code value.
   * normal → green, above_acceptable → orange, above_permissible → red.
   */
  function _statusColor(statusCode) {
    if (statusCode === 'above_permissible') return '#dc2626';
    if (statusCode === 'above_acceptable')  return '#d97706';
    return '#16a34a'; // normal
  }

  function _populateParamTable(parameters) {
    var tbody = document.getElementById('paramTableBody');
    if (!tbody) return;

    var rows = parameters.map(function (p) {
      var measured   = _esc(p.value) + (p.unit ? ' ' + _esc(p.unit) : '');
      var acceptable = p.acceptable_limit != null ? _esc(p.acceptable_limit) : '—';
      var permissible = p.permissible_limit != null ? _esc(p.permissible_limit) : '—';
      var subIdx     = p.sub_index != null ? window.formatNumber(p.sub_index, 2) : '—';
      var statusTxt  = _esc(p.status || '');
      var color      = _statusColor(p.status_code || 'normal');

      return '<tr>' +
        '<td>'  + _esc(p.name || p.key || '') + '</td>' +
        '<td>'  + measured + '</td>' +
        '<td>'  + acceptable + '</td>' +
        '<td>'  + permissible + '</td>' +
        '<td style="text-align:right">' + subIdx + '</td>' +
        '<td style="font-weight:600;color:' + color + '">' + statusTxt + '</td>' +
        '</tr>';
    });

    tbody.innerHTML = rows.join('');
  }

  // ------------------------------------------------------------------ violations

  function _populateViolations(violations) {
    var section = document.getElementById('violationsSection');
    var list    = document.getElementById('violationsList');
    if (!section || !list) return;

    if (!Array.isArray(violations) || !violations.length) {
      // Leave section hidden (default style="display:none")
      return;
    }

    section.style.display = '';

    var items = violations.map(function (v) {
      // violation items may be a plain string or an object with a .parameter field
      var text = (typeof v === 'object' && v !== null)
        ? (v.parameter || JSON.stringify(v))
        : String(v);
      return '<div style="padding:.3rem 0;color:#dc2626">' +
             '<span style="margin-right:.4rem">⚠️</span>' + _esc(text) +
             '</div>';
    });

    list.innerHTML = items.join('');
  }

  // ------------------------------------------------------------------ recommendations

  function _populateRecommendations(recommendations) {
    var container = document.getElementById('recommendationsList');
    if (!container) return;

    if (!Array.isArray(recommendations) || !recommendations.length) {
      container.innerHTML = '<p style="color:var(--text-muted);font-size:.875rem">No specific recommendations.</p>';
      return;
    }

    var ul = '<ul style="margin:0;padding-left:1.25rem;line-height:1.75">';
    ul += recommendations.map(function (r) {
      return '<li style="margin-bottom:.35rem">' + _esc(r) + '</li>';
    }).join('');
    ul += '</ul>';

    container.innerHTML = ul;
  }

  // ------------------------------------------------------------------ params not tested

  function _populateNotTested(paramsNotTested) {
    var section = document.getElementById('notTestedSection');
    var list    = document.getElementById('notTestedList');
    if (!section || !list) return;

    if (!Array.isArray(paramsNotTested) || !paramsNotTested.length) {
      // Leave hidden (default style="display:none")
      return;
    }

    section.style.display = '';
    // Show keys uppercased, comma-joined
    list.textContent = paramsNotTested.map(function (k) {
      return String(k).toUpperCase();
    }).join(', ');
  }

  // ------------------------------------------------------------------ disclaimer

  function _populateDisclaimer(disclaimer) {
    _setText('disclaimerText', disclaimer || '');
  }

  // ------------------------------------------------------------------ PDF download

  /**
   * Build the PDF request payload.
   *
   * report.py _build_pdf() reads these keys directly from the posted JSON:
   *   data.get("sample_name"), data.get("district"), data.get("assessment_date"),
   *   data.get("params_tested"), data.get("wqi"), data.get("grade"),
   *   data.get("category"), data.get("potability"), data.get("overall_assessment"),
   *   data.get("parameters")  — each item: name, value, unit, acceptable_limit,
   *                             permissible_limit, status, status_code
   *   data.get("violations"), data.get("recommendations"), data.get("disclaimer")
   *
   * The full assessment object from /api/assess-water already contains every one of
   * these keys, so we pass it through unchanged.
   */
  function _buildPDFPayload(data) {
    return data;
  }

  function _bindPDFButton(data) {
    var btn = document.getElementById('downloadPdfBtn');
    if (!btn) return;

    btn.addEventListener('click', function () {
      var originalText = btn.textContent;
      btn.disabled     = true;
      btn.textContent  = '⌛ Generating…';

      var payload = _buildPDFPayload(data);

      window.AquaSureAPI.generatePDF(payload)
        .then(function (blob) {
          // Sanitize sample_name: replace spaces/special chars for a safe filename
          var safeName = (data.sample_name || 'Assessment')
            .replace(/[^a-zA-Z0-9_\-]/g, '_')
            .replace(/_+/g, '_');
          var filename = 'AquaSure_' + safeName + '_assessment.pdf';

          var url  = URL.createObjectURL(blob);
          var link = document.createElement('a');
          link.href     = url;
          link.download = filename;
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
          URL.revokeObjectURL(url);

          if (window.showSuccess) window.showSuccess('PDF downloaded.');
        })
        .catch(function (err) {
          console.error('PDF generation error:', err);
          if (window.showError) {
            window.showError(
              'PDF generation failed. Ensure ReportLab is installed and backend is running.'
            );
          }
        })
        .finally(function () {
          btn.disabled    = false;
          btn.textContent = originalText;
        });
    });
  }

  // ------------------------------------------------------------------ init

  function _init() {
    var data = _loadAssessment();

    if (!data) {
      // No valid assessment — keep #noDataState visible, ensure #resultsContainer hidden
      var container = document.getElementById('resultsContainer');
      if (container) container.style.display = 'none';
      // #noDataState is visible by default; nothing further to do
      return;
    }

    // Show results, hide empty state
    var container   = document.getElementById('resultsContainer');
    var noDataState = document.getElementById('noDataState');
    if (container)   container.style.display   = '';
    if (noDataState) noDataState.style.display = 'none';

    // Populate every section
    _populateHeader(data);
    _populateHero(data);
    _populateParamTable(data.parameters || []);
    _populateViolations(data.violations || []);
    _populateRecommendations(data.recommendations || []);
    _populateNotTested(data.params_not_tested || []);
    _populateDisclaimer(data.disclaimer);

    // Wire PDF download button
    _bindPDFButton(data);
  }

  document.addEventListener('DOMContentLoaded', _init);

})(window);
