// nav.js — site-wide navigation, injected into #site-footer (footer-only on regular pages)
// Captured at load time — currentScript is only valid during initial execution
const NAV_ROOT = new URL('.', document.currentScript.src).href;
document.addEventListener('DOMContentLoaded', function() {
  const headerEl = document.getElementById('site-header');
  const footerEl = document.getElementById('site-footer');

// Site root = the folder this script lives in (nav.js sits at the repo root).
  // Works at any page depth and survives repo renames.
  const root = NAV_ROOT;

  const navHTML = `
  <footer style="margin-top: 4rem; padding: 2rem; border-top: 1px solid var(--rule); background: var(--parchment); text-align: left; font-family: Georgia, 'Palatino Linotype', serif; font-size: 1.05rem; line-height: 1.8;">
      <div style="max-width: 1200px; margin: 0 auto; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem;">
          <a href="${root}index.html" style="text-decoration: none; color: var(--accent); font-size: 1.3rem; font-family: 'Cormorant Garamond', Georgia, serif;">
              The Portable Temple
          </a>
          <nav style="display: flex; gap: 1.6rem; flex-wrap: wrap;">
              <a href="${root}index.html">Home</a>
              <a href="${root}using.html">Using This Site</a>
              <a href="${root}index.html#about">About &amp; Contact</a>
              <a href="${root}notes.html">Log &amp; Journal</a>
              <a href="${root}portabletemple/timeline-pt.html" style="color: var(--sepia);">Start Exploring →</a>
          </nav>
          <div style="font-size: 0.95rem; color: var(--muted);">Christopher Windsmile</div>
      </div>
  </footer>`;

  if (headerEl) headerEl.innerHTML = navHTML;
  if (footerEl) footerEl.innerHTML = navHTML;
});
