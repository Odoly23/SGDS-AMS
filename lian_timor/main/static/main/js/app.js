/* Lian Timor - JavaScript dasar: ganti bahasa 1 klik, sidebar HP, service worker, tombol pasang di HP. */
(function () {
  "use strict";
  var KODE = ["tet", "en", "pt", "id"];

  function sinkron() {
    var l = document.documentElement.lang;
    document.querySelectorAll("[data-set-lang]").forEach(function (b) {
      b.setAttribute("aria-pressed", String(b.getAttribute("data-set-lang") === l));
    });
    // aria-label tombol berikon ikut berganti bahasa
    document.querySelectorAll("[data-aria]").forEach(function (el) {
      try { var d = JSON.parse(el.getAttribute("data-aria")); el.setAttribute("aria-label", d[l] || d.tet); } catch (e) { /* abaikan */ }
    });
  }

  function setBahasa(l) {
    if (KODE.indexOf(l) < 0) l = "tet";
    document.documentElement.lang = l;
    try { localStorage.setItem("lian_lang", l); } catch (e) { /* mode privat: abaikan */ }
    sinkron();
  }

  // ---- Sidebar HP (hamburger) ----
  var sidebar = document.getElementById("sidebar"), overlay = document.getElementById("overlay"), ham = document.getElementById("btnHam");
  function sidebar_(buka) {
    if (!sidebar) return;
    sidebar.classList.toggle("active", buka);
    if (overlay) overlay.classList.toggle("active", buka);
    document.body.classList.toggle("sb-open", buka);
    if (ham) ham.setAttribute("aria-expanded", String(buka));
  }

  document.addEventListener("click", function (e) {
    var b = e.target.closest("[data-set-lang]");
    if (b) setBahasa(b.getAttribute("data-set-lang"));
    if (ham && e.target.closest("#btnHam")) sidebar_(!sidebar.classList.contains("active"));
    else if (overlay && e.target.closest("#overlay")) sidebar_(false);
    else if (sidebar && e.target.closest("#sidebar a")) sidebar_(false);
  });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape") sidebar_(false); });
  window.addEventListener("resize", function () { if (window.innerWidth >= 1200) sidebar_(false); });
  sinkron();

  // PWA: service worker hanya di HTTPS atau localhost
  var aman = location.protocol === "https:" || location.hostname === "localhost" || location.hostname === "127.0.0.1";
  if ("serviceWorker" in navigator && aman) {
    window.addEventListener("load", function () { navigator.serviceWorker.register("/sw.js").catch(function () {}); });
  }

  // Tombol "Pasang di layar utama"
  var tunda = null, tombol = document.getElementById("pasang");
  window.addEventListener("beforeinstallprompt", function (e) {
    e.preventDefault(); tunda = e; if (tombol) tombol.hidden = false;
  });
  if (tombol) tombol.addEventListener("click", function () {
    if (!tunda) return; tunda.prompt(); tunda = null; tombol.hidden = true;
  });
})();
