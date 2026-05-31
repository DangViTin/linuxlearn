/*
 * Tiny enhancements for the Furo theme.
 *
 *  1. Inject a "Hide sidebar" toggle button on desktop so the reader can
 *     reclaim the full window width when they want a distraction-free read.
 *     Toggling adds / removes `sidebar-hidden` on <body>; CSS handles the
 *     slide-out animation.  State is persisted in localStorage.
 *
 *  2. Keyboard shortcut: press [   to toggle sidebar
 *     (same key as VS Code's "View: Toggle Primary Side Bar" Ctrl+B —
 *     we bind both [ and Ctrl+B so muscle memory works either way).
 *
 *  3. Remember dark-mode preference across pages (Furo already does this
 *     via its own toggle; we just ensure the LocalStorage key is consistent
 *     for the sidebar state too).
 */

(function () {
  "use strict";

  // --- Sidebar toggle -------------------------------------------------------

  const STORAGE_KEY = "lh-sidebar-hidden";

  function applySidebarState(hidden) {
    if (hidden) document.body.classList.add("sidebar-hidden");
    else document.body.classList.remove("sidebar-hidden");
  }

  function readSidebarState() {
    try {
      return localStorage.getItem(STORAGE_KEY) === "1";
    } catch (e) {
      return false;
    }
  }

  function writeSidebarState(hidden) {
    try {
      localStorage.setItem(STORAGE_KEY, hidden ? "1" : "0");
    } catch (e) {
      /* localStorage disabled — ignore. */
    }
  }

  function toggleSidebar() {
    const nowHidden = !document.body.classList.contains("sidebar-hidden");
    applySidebarState(nowHidden);
    writeSidebarState(nowHidden);
    // Update aria-label on the toggle button so screen readers announce
    // the new state.
    const btn = document.querySelector(".sidebar-toggle");
    if (btn) {
      btn.setAttribute(
        "aria-label",
        nowHidden ? "Show sidebar" : "Hide sidebar"
      );
      btn.setAttribute("title", nowHidden ? "Show sidebar (Ctrl+B)" : "Hide sidebar (Ctrl+B)");
    }
  }

  function injectSidebarToggle() {
    if (document.querySelector(".sidebar-toggle")) return; // already there
    const btn = document.createElement("button");
    btn.className = "sidebar-toggle";
    btn.setAttribute("type", "button");
    btn.setAttribute("aria-label", "Toggle sidebar");
    btn.setAttribute("title", "Toggle sidebar (Ctrl+B)");
    btn.innerHTML =
      '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
      '<rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>' +
      '<line x1="9" y1="3" x2="9" y2="21"></line>' +
      "</svg>";
    btn.addEventListener("click", toggleSidebar);
    document.body.appendChild(btn);
  }

  function onKeyDown(ev) {
    // Don't hijack the keystrokes when the user is typing in an input.
    const t = ev.target;
    if (
      t &&
      (t.tagName === "INPUT" ||
        t.tagName === "TEXTAREA" ||
        t.isContentEditable)
    ) {
      return;
    }
    // Ctrl+B (VS Code) toggles sidebar.
    if ((ev.ctrlKey || ev.metaKey) && (ev.key === "b" || ev.key === "B")) {
      ev.preventDefault();
      toggleSidebar();
    }
  }

  function init() {
    applySidebarState(readSidebarState());
    injectSidebarToggle();
    document.addEventListener("keydown", onKeyDown);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
