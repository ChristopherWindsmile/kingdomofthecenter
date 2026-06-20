// site-utils.js — shared helpers for Kingdom of the Center
// Load this before any page script that injects sheet/CSV text into the DOM.

// Escape text before it goes into innerHTML or an HTML attribute.
// & must be replaced first, or the later replacements get double-escaped.
function escapeHTML(str) {
  return String(str ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}
