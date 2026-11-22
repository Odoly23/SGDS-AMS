/* LAFEX - perekam suara di browser (MediaRecorder). Dipakai halaman Belajar ("Grava ha'u", TIDAK diunggah)
   dan Crowdsource (diunggah setelah user menekan Haruka).
   Catatan: mikrofon hanya bisa dipakai di HTTPS atau localhost. */
(function () {
  "use strict";
  var MIME = ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus", "audio/mp4", "audio/mpeg"];

  function didukung() {
    return !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia && window.MediaRecorder);
  }
  function pilihMime() {
    for (var i = 0; i < MIME.length; i++) { if (MediaRecorder.isTypeSupported(MIME[i])) return MIME[i]; }
    return "";
  }

  /* mulai({maks: 60, tick: fn(detik), otomatisBerhenti: fn(hasil)}) -> Promise<{berhenti: fn -> Promise<hasil>, batal: fn}>
     hasil = {blob, url, mime, durasi}. Ditolak (reject) bila mikrofon tidak diizinkan. */
  function mulai(opsi) {
    opsi = opsi || {};
    var maks = opsi.maks || 60;
    return navigator.mediaDevices.getUserMedia({ audio: true }).then(function (stream) {
      var mime = pilihMime(), potong = [], t0 = Date.now(), selesai = false, timer, auto;
      var rec = mime ? new MediaRecorder(stream, { mimeType: mime }) : new MediaRecorder(stream);
      rec.ondataavailable = function (e) { if (e.data && e.data.size) potong.push(e.data); };
      function lepas() { clearInterval(timer); clearTimeout(auto); stream.getTracks().forEach(function (t) { t.stop(); }); }   // matikan mikrofon
      var berhenti = function () {
        return new Promise(function (ok) {
          if (selesai) return ok(null);
          selesai = true;
          rec.onstop = function () {
            lepas();
            var tipe = rec.mimeType || mime || "audio/webm";
            var blob = new Blob(potong, { type: tipe });
            ok({ blob: blob, url: URL.createObjectURL(blob), mime: tipe, durasi: Math.round((Date.now() - t0) / 100) / 10 });
          };
          if (rec.state !== "inactive") rec.stop(); else rec.onstop();
        });
      };
      rec.start(250);
      timer = setInterval(function () { if (opsi.tick) opsi.tick(Math.floor((Date.now() - t0) / 1000)); }, 250);
      auto = setTimeout(function () { berhenti().then(function (h) { if (opsi.otomatisBerhenti) opsi.otomatisBerhenti(h); }); }, maks * 1000);
      return { berhenti: berhenti, batal: function () { selesai = true; try { rec.stop(); } catch (e) { /* abaikan */ } lepas(); } };
    });
  }

  function detik(n) { var m = Math.floor(n / 60), s = n % 60; return m + ":" + (s < 10 ? "0" : "") + s; }
  function csrf() { var m = document.cookie.match(/(?:^|; )csrftoken=([^;]*)/); return m ? decodeURIComponent(m[1]) : ""; }

  window.LafexRekam = { didukung: didukung, mulai: mulai, detik: detik, csrf: csrf };
})();
