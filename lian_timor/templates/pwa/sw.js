{% load static %}/* Service worker Lian Timor: membuat halaman yang sudah dibuka tetap bisa dipakai tanpa internet. */
const VERSI = "lian-{{ versi }}";
const KULIT = [
  "/", "/offline/",
  "{% static 'css/tailwind.css' %}", "{% static 'js/app.js' %}",
  "{% static 'fonts/nunito-latin-wght-normal.woff2' %}",
  "{% static 'img/tais.svg' %}", "{% static 'img/lafaek.svg' %}",
  "{% static 'icons/icon-192.png' %}"
];
// Halaman yang berisi data pribadi TIDAK disimpan (HP bisa dipakai bergantian)
const JANGAN_SIMPAN = /^\/(admin|akun|masuk|keluar|api)(\/|$)/;

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(VERSI).then((c) => c.addAll(KULIT)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((nama) => Promise.all(nama.filter((n) => n.startsWith("lian-") && n !== VERSI).map((n) => caches.delete(n))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const req = e.request;
  const url = new URL(req.url);
  if (req.method !== "GET" || url.origin !== location.origin) return;
  if (JANGAN_SIMPAN.test(url.pathname) || req.headers.has("range")) return;   // audio (Range) menyusul di tahap berikutnya

  // Halaman: internet dulu (isi terbaru), kalau gagal pakai salinan tersimpan
  if (req.mode === "navigate") {
    e.respondWith(
      fetch(req).then((res) => {
        if (res.ok) { const salinan = res.clone(); caches.open(VERSI).then((c) => c.put(req, salinan)); }
        return res;
      }).catch(() => caches.match(req).then((r) => r || caches.match("/offline/")))
    );
    return;
  }
  // Berkas statis (CSS, JS, huruf, gambar): salinan tersimpan dulu, supaya cepat
  if (url.pathname.startsWith("/static/") || url.pathname.startsWith("/media/")) {
    e.respondWith(
      caches.match(req).then((r) => r || fetch(req).then((res) => {
        if (res.ok) { const salinan = res.clone(); caches.open(VERSI).then((c) => c.put(req, salinan)); }
        return res;
      }))
    );
  }
});
