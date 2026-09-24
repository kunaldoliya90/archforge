// ArchForge theme — theme toggle, mobile nav, outline scrollspy, search, diagram lightbox.
(() => {
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];
  const root = document.documentElement;

  // ── Theme ────────────────────────────────────────────────
  function toggleTheme() {
    const next = root.dataset.theme === "dark" ? "light" : "dark";
    root.dataset.theme = next;
    try { localStorage.setItem("docs-theme", next); } catch (e) {}
  }

  // ── Mobile nav ───────────────────────────────────────────
  const setMenu = (open) => document.body.classList.toggle("nav-open", open);

  document.addEventListener("click", (e) => {
    const action = e.target.closest("[data-action]")?.dataset.action;
    if (action === "theme") toggleTheme();
    else if (action === "menu") setMenu(!document.body.classList.contains("nav-open"));
    else if (action === "close-menu") setMenu(false);
    else if (action === "search") openSearch();
  });

  // ── Outline scrollspy ────────────────────────────────────
  const tocLinks = $$(".toc-link");
  if (tocLinks.length) {
    const byId = new Map(tocLinks.map((a) => [decodeURIComponent(a.hash.slice(1)), a]));
    const headings = [...byId.keys()].map((id) => document.getElementById(id)).filter(Boolean);
    const update = () => {
      const line = window.innerHeight * 0.25;
      let current = headings[0];
      for (const h of headings) {
        if (h.getBoundingClientRect().top - line <= 0) current = h;
        else break;
      }
      tocLinks.forEach((a) => a.classList.remove("active"));
      byId.get(current?.id)?.classList.add("active");
    };
    document.addEventListener("scroll", update, { passive: true });
    update();
  }

  // ── Search ───────────────────────────────────────────────
  const modal = $("#search");
  const input = $("#search-input");
  const list = $("#search-results");
  let index = null;
  let results = [];
  let selected = 0;

  const escapeHtml = (s) => s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const escapeRe = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

  async function openSearch() {
    modal.hidden = false;
    input.value = "";
    input.focus();
    renderResults();
    if (!index) {
      try { index = await (await fetch("/search.json")).json(); } catch (e) { index = []; }
      renderResults();
    }
  }
  const closeSearch = () => { modal.hidden = true; };

  function score(entry, terms) {
    const title = entry.p.toLowerCase(), head = entry.h.toLowerCase(), text = entry.x.toLowerCase();
    const phrase = terms.join(" ");
    let total = terms.length > 1 && (head + " " + text).includes(phrase) ? 6 : 0;
    for (const t of terms) {
      const s = (title.includes(t) ? 8 : 0) + (head.includes(t) ? 6 : 0) + (text.includes(t) ? 1 : 0);
      if (!s) return 0;
      total += s;
    }
    return total + (entry.h ? 0 : 0.5);
  }

  function snippet(text, terms) {
    const lower = text.toLowerCase();
    let at = Math.min(...terms.map((t) => lower.indexOf(t)).filter((i) => i >= 0));
    if (!isFinite(at)) at = 0;
    const start = Math.max(0, at - 50);
    let s = (start ? "…" : "") + text.slice(start, start + 170) + (start + 170 < text.length ? "…" : "");
    s = escapeHtml(s);
    const re = new RegExp("(" + terms.map((t) => escapeRe(escapeHtml(t))).join("|") + ")", "gi");
    return s.replace(re, "<mark>$1</mark>");
  }

  function renderResults() {
    const q = input.value.trim().toLowerCase();
    if (!q) {
      list.innerHTML = '<div class="search-empty">Search pages, sections, services and API fields.</div>';
      results = [];
      return;
    }
    if (!index) { list.innerHTML = '<div class="search-empty">Loading…</div>'; return; }
    const terms = q.split(/\s+/).filter(Boolean);
    results = index
      .map((e) => ({ e, s: score(e, terms) }))
      .filter((r) => r.s > 0)
      .sort((a, b) => b.s - a.s)
      .slice(0, 20)
      .map((r) => r.e);
    selected = 0;
    if (!results.length) {
      list.innerHTML = `<div class="search-empty">No results for “${escapeHtml(input.value.trim())}”</div>`;
      return;
    }
    list.innerHTML = results.map((r, i) => `
      <a class="result${i === 0 ? " sel" : ""}" href="${r.u}">
        <div class="result-crumb">${escapeHtml([r.g, r.h ? r.p : ""].filter(Boolean).join(" › ") || "Overview")}</div>
        <div class="result-title">${escapeHtml(r.h || r.p)}</div>
        <div class="result-snip">${snippet(r.x, terms)}</div>
      </a>`).join("");
  }

  function moveSelection(delta) {
    const items = $$(".result", list);
    if (!items.length) return;
    items[selected]?.classList.remove("sel");
    selected = (selected + delta + items.length) % items.length;
    items[selected].classList.add("sel");
    items[selected].scrollIntoView({ block: "nearest" });
  }

  input.addEventListener("input", renderResults);
  input.addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown") { e.preventDefault(); moveSelection(1); }
    else if (e.key === "ArrowUp") { e.preventDefault(); moveSelection(-1); }
    else if (e.key === "Enter" && results[selected]) { location.href = results[selected].u; closeSearch(); }
  });
  modal.addEventListener("click", (e) => {
    if (e.target === modal) closeSearch();
    if (e.target.closest(".result")) closeSearch();
  });

  // ── Diagram lightbox ─────────────────────────────────────
  const lb = $("#lightbox");
  const stage = $("#lb-stage");
  const img = $("#lb-img");
  const view = { x: 0, y: 0, k: 1 };
  const apply = () => { img.style.transform = `translate(${view.x}px, ${view.y}px) scale(${view.k})`; };

  function fit() {
    const pad = 72;
    const w = img.naturalWidth, h = img.naturalHeight;
    const k = Math.min((stage.clientWidth - pad * 2) / w, (stage.clientHeight - pad * 2) / h, 1.5);
    view.k = k;
    view.x = (stage.clientWidth - w * k) / 2;
    view.y = (stage.clientHeight - h * k) / 2;
    apply();
  }

  function zoomAt(factor, cx = stage.clientWidth / 2, cy = stage.clientHeight / 2) {
    const k = Math.min(8, Math.max(0.1, view.k * factor));
    view.x = cx - ((cx - view.x) * k) / view.k;
    view.y = cy - ((cy - view.y) * k) / view.k;
    view.k = k;
    apply();
  }

  function openLightbox(src, caption) {
    $("#lb-caption").textContent = caption || "";
    lb.hidden = false;
    document.body.style.overflow = "hidden";
    img.onload = fit;
    img.src = src;
    if (img.complete && img.naturalWidth) fit();
  }
  function closeLightbox() {
    lb.hidden = true;
    document.body.style.overflow = "";
  }

  document.addEventListener("click", (e) => {
    const btn = e.target.closest(".diagram-open");
    if (btn) openLightbox(btn.dataset.src, btn.dataset.caption);
    const tool = e.target.closest("[data-lb]")?.dataset.lb;
    if (tool === "in") zoomAt(1.25);
    else if (tool === "out") zoomAt(0.8);
    else if (tool === "reset") fit();
    else if (tool === "close") closeLightbox();
  });

  stage.addEventListener("wheel", (e) => {
    e.preventDefault();
    const r = stage.getBoundingClientRect();
    zoomAt(Math.exp(-e.deltaY * 0.0015), e.clientX - r.left, e.clientY - r.top);
  }, { passive: false });

  let drag = null;
  stage.addEventListener("pointerdown", (e) => {
    drag = { x: e.clientX - view.x, y: e.clientY - view.y };
    stage.setPointerCapture(e.pointerId);
    stage.classList.add("dragging");
  });
  stage.addEventListener("pointermove", (e) => {
    if (!drag) return;
    view.x = e.clientX - drag.x;
    view.y = e.clientY - drag.y;
    apply();
  });
  const endDrag = () => { drag = null; stage.classList.remove("dragging"); };
  stage.addEventListener("pointerup", endDrag);
  stage.addEventListener("pointercancel", endDrag);
  stage.addEventListener("dblclick", fit);
  window.addEventListener("resize", () => { if (!lb.hidden) fit(); });

  // ── Keyboard ─────────────────────────────────────────────
  document.addEventListener("keydown", (e) => {
    const typing = /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement?.tagName);
    if ((e.key === "k" || e.key === "K") && (e.metaKey || e.ctrlKey)) { e.preventDefault(); modal.hidden ? openSearch() : closeSearch(); }
    else if (e.key === "/" && !typing && modal.hidden && lb.hidden) { e.preventDefault(); openSearch(); }
    else if (e.key === "Escape") { if (!lb.hidden) closeLightbox(); else if (!modal.hidden) closeSearch(); else setMenu(false); }
    else if (!lb.hidden && (e.key === "+" || e.key === "=")) zoomAt(1.25);
    else if (!lb.hidden && e.key === "-") zoomAt(0.8);
    else if (!lb.hidden && e.key === "0") fit();
  });

  if (/Mac|iPhone|iPad/.test(navigator.platform)) {
    const kbd = $(".search-kbd");
    if (kbd) kbd.textContent = "⌘ K";
  }
})();
