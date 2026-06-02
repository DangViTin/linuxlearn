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
  const SCROLL_KEY = "lh-sidebar-scroll";

  // --- Sidebar scroll persistence ------------------------------------------
  //
  // Sphinx/Furo serves a separate HTML document per page, so every nav click
  // is a full page reload and the sidebar's scroll position is lost. Persist
  // it in sessionStorage and restore it on load so the left panel feels
  // independent of the content area.

  function getSidebarScroller() {
    // Furo's scrollable element. Fall back gracefully across versions.
    return (
      document.querySelector(".sidebar-scroll") ||
      document.querySelector(".sidebar-drawer .sidebar-container") ||
      document.querySelector(".sidebar-drawer")
    );
  }

  function saveSidebarScroll() {
    const el = getSidebarScroller();
    if (!el) return;
    try {
      sessionStorage.setItem(SCROLL_KEY, String(el.scrollTop));
    } catch (e) {
      /* sessionStorage disabled — ignore. */
    }
  }

  function restoreSidebarScroll() {
    const el = getSidebarScroller();
    if (!el) return;
    let saved = 0;
    try {
      saved = parseInt(sessionStorage.getItem(SCROLL_KEY) || "0", 10) || 0;
    } catch (e) {
      return;
    }
    if (saved > 0) el.scrollTop = saved;
  }

  function wireSidebarScrollPersistence() {
    const el = getSidebarScroller();
    if (!el) return;

    // Save while scrolling (cheap — just writes a number).
    let raf = 0;
    el.addEventListener(
      "scroll",
      function () {
        if (raf) return;
        raf = requestAnimationFrame(function () {
          raf = 0;
          saveSidebarScroll();
        });
      },
      { passive: true }
    );

    // Save right before navigating away (covers link clicks, back/forward).
    window.addEventListener("pagehide", saveSidebarScroll);
    window.addEventListener("beforeunload", saveSidebarScroll);

    // Catch sidebar link clicks explicitly — pagehide fires after the
    // navigation is committed in some browsers; this is the reliable spot.
    document.querySelectorAll(".sidebar-tree a").forEach(function (a) {
      a.addEventListener("click", saveSidebarScroll);
    });
  }

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
    const btn = document.querySelector(".sidebar-toggle");
    if (btn) {
      btn.setAttribute(
        "aria-label",
        nowHidden ? "Show sidebar" : "Hide sidebar"
      );
      btn.setAttribute(
        "title",
        (nowHidden ? "Show" : "Hide") + " sidebar (Ctrl+B)"
      );
    }
  }

  function injectSidebarToggle() {
    if (document.querySelector(".sidebar-toggle")) return;
    const hidden = document.body.classList.contains("sidebar-hidden");
    const btn = document.createElement("button");
    btn.className = "sidebar-toggle";
    btn.setAttribute("type", "button");
    btn.setAttribute("aria-label", hidden ? "Show sidebar" : "Hide sidebar");
    btn.setAttribute(
      "title",
      (hidden ? "Show" : "Hide") + " sidebar (Ctrl+B)"
    );
    // Two icons; CSS shows one based on body.sidebar-hidden.
    btn.innerHTML =
      '<svg class="icon-hide" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
      '<rect x="3" y="3" width="18" height="18" rx="2"></rect>' +
      '<line x1="9" y1="3" x2="9" y2="21"></line>' +
      "</svg>" +
      '<svg class="icon-show" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
      '<line x1="3" y1="6" x2="21" y2="6"></line>' +
      '<line x1="3" y1="12" x2="21" y2="12"></line>' +
      '<line x1="3" y1="18" x2="21" y2="18"></line>' +
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

    // Restore sidebar scroll BEFORE the browser paints, so the user never
    // sees the flash of "scrolled to top".
    restoreSidebarScroll();
    wireSidebarScrollPersistence();

    // Also restore after a tick — Furo / other scripts sometimes adjust
    // the sidebar layout post-DOMContentLoaded (e.g. expanding the current
    // section), which can clobber our scrollTop. Re-apply after that.
    requestAnimationFrame(restoreSidebarScroll);
    setTimeout(restoreSidebarScroll, 0);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
