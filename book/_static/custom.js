(() => {
  "use strict";

  let pendingFrame = null;

  function revealCurrentChapter() {
    const sidebar = document.querySelector(".sidebar-scroll");
    const current = document.querySelector('.sidebar-tree a[aria-current="page"]');
    if (!sidebar || !current || !sidebar.clientHeight) return;

    const viewport = sidebar.getBoundingClientRect();
    const chapter = current.getBoundingClientRect();
    const margin = 20;
    if (chapter.top < viewport.top + margin || chapter.bottom > viewport.bottom - margin) {
      // Scroll this container only; scrollIntoView can also move the article.
      sidebar.scrollTop += chapter.top - viewport.top - (viewport.height - chapter.height) / 2;
    }
  }

  function scheduleReveal() {
    if (pendingFrame !== null) return;
    pendingFrame = requestAnimationFrame(() => {
      pendingFrame = null;
      revealCurrentChapter();
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    scheduleReveal();
    if (document.fonts) document.fonts.ready.then(scheduleReveal);
    document.querySelectorAll(".theme-toggle").forEach(button => {
      button.title = "Change color theme";
    });
    const drawer = document.getElementById("__navigation");
    if (drawer) drawer.addEventListener("change", () => {
      if (drawer.checked) scheduleReveal();
    });
  });
  window.addEventListener("pageshow", scheduleReveal);
  window.addEventListener("resize", scheduleReveal);
})();
