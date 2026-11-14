/* Lian Timor - JavaScript dasar: ganti bahasa 1 klik, service worker, tombol pasang di HP. */
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

  document.addEventListener("click", function (e) {
    var b = e.target.closest("[data-set-lang]");
    if (b) setBahasa(b.getAttribute("data-set-lang"));
  });
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
