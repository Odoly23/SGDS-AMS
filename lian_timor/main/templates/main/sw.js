{% load static %}/* Service worker Lian Timor: membuat halaman yang sudah dibuka tetap bisa dipakai tanpa internet. */
// Dua cache terpisah: STATIK (CSS/JS/gambar, aman) dan HALAMAN (HTML, bisa memuat progres user -> dihapus saat logout)
const STATIK = "lian-statik-{{ versi }}";
const HALAMAN = "lian-halaman-{{ versi }}";
const KULIT = [
  "/offline/",
  "{% static 'main/css/bootstrap.min.css' %}", "{% static 'main/css/main.css' %}",
  "{% static 'main/font-awesome/css/font-awesome.min.css' %}",
  "{% static 'main/font-awesome/fonts/fontawesome-webfont.woff2' %}",
  "{% static 'main/fonts/nunito-latin-wght-normal.woff2' %}",
  "{% static 'main/js/jquery.min.js' %}", "{% static 'main/js/bootstrap.bundle.min.js' %}", "{% static 'main/js/app.js' %}",
  "{% static 'main/images/tais.svg' %}", "{% static 'main/images/lafaek.svg' %}",
  "{% static 'main/icons/icon-192.png' %}"
];
// Halaman berisi data pribadi TIDAK disimpan (HP sering dipakai bergantian)
const JANGAN_SIMPAN = /^\/(admin|users|report|login|logout|tamu)(\/|$)/;

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(STATIK).then((c) => c.addAll(KULIT)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((nama) => Promise.all(nama.filter((n) => n.startsWith("lian-") && n !== STATIK && n !== HALAMAN).map((n) => caches.delete(n))))
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
        // jangan simpan hasil pengalihan / galat; simpan halaman yang berhasil
        if (res.ok && !res.redirected) { const salinan = res.clone(); caches.open(HALAMAN).then((c) => c.put(req, salinan)); }
        return res;
      }).catch(() => caches.match(req).then((r) => r || caches.match("/offline/")))
    );
    return;
  }
  // Berkas statis (CSS, JS, huruf, gambar): salinan tersimpan dulu, supaya cepat
  if (url.pathname.startsWith("/static/") || url.pathname.startsWith("/media/")) {
    e.respondWith(
      caches.match(req).then((r) => r || fetch(req).then((res) => {
        if (res.ok) { const salinan = res.clone(); caches.open(STATIK).then((c) => c.put(req, salinan)); }
        return res;
      }))
    );
  }
});
