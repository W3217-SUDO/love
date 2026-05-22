// Couple Diary — global client helpers.
// Phase B/C use inline JS in templates for form submission. This file is
// reserved for shared utilities (toast helpers, HTMX defaults, etc.).
(function () {
  'use strict';

  // HTMX global defaults (only applies if HTMX is loaded).
  document.addEventListener('htmx:configRequest', function (evt) {
    // Default to JSON for state-changing requests if Content-Type not set.
    if (evt.detail.verb !== 'get' && !evt.detail.headers['Content-Type']) {
      // Leave default form-encoding; switching to JSON requires per-form opt-in.
    }
  });

  // Suppress unhandled HTMX errors with a visible toast (future).
  document.addEventListener('htmx:responseError', function (evt) {
    console.error('htmx:responseError', evt.detail);
  });
})();
