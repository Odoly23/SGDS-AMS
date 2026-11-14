/* Halaman Belajar: Dengar (audio atau suara bawaan HP), Grava ha'u (hanya di HP, TIDAK diunggah), Ha'u aprende ona (progress). */
(function () {
  "use strict";
  var sedangRekam = null;     // hanya satu rekaman aktif pada satu waktu
  var audioAktif = null;

  // ---------- Dengar ----------
  function adaSuara(lang) {
    if (!("speechSynthesis" in window)) return false;
    var awal = lang.slice(0, 2).toLowerCase();
    return speechSynthesis.getVoices().some(function (v) { return v.lang.toLowerCase().indexOf(awal) === 0; });
  }
  function bunyikan(tombol) {
    if (audioAktif) { audioAktif.pause(); audioAktif = null; }
    if ("speechSynthesis" in window) speechSynthesis.cancel();
    var url = tombol.getAttribute("data-audio");
    if (url) { audioAktif = new Audio(url); audioAktif.play().catch(function () {}); return; }
    var teks = tombol.getAttribute("data-teks"), lang = tombol.getAttribute("data-tts");
    if (teks && lang && "speechSynthesis" in window) {
      var u = new SpeechSynthesisUtterance(teks); u.lang = lang; u.rate = 0.9; speechSynthesis.speak(u);
    }
  }
  function cekSuara() {      // tombol suara bawaan HP dimatikan bila HP tidak punya suara bahasa itu (dan tidak ada file audio)
    document.querySelectorAll("button[data-tts]").forEach(function (b) {
      b.disabled = !(b.getAttribute("data-audio") || adaSuara(b.getAttribute("data-tts")));
    });
  }
  if ("speechSynthesis" in window) { cekSuara(); speechSynthesis.onvoiceschanged = cekSuara; } else { cekSuara(); }

  // ---------- Progress (dengan antrean bila sedang offline) ----------
  var ANTRE = "lian_progres_antre";
  function baca() { try { return JSON.parse(localStorage.getItem(ANTRE) || "[]"); } catch (e) { return []; } }
  function simpan(a) { try { localStorage.setItem(ANTRE, JSON.stringify(a)); } catch (e) { /* abaikan */ } }

  function isiTpl(el, nilai) {
    el.querySelectorAll("[data-tpl]").forEach(function (s) {
      s.textContent = s.getAttribute("data-tpl").replace("{done}", nilai.selesai).replace("{total}", nilai.total);
    });
  }
  function perbarui(nilai) {
    var bar = document.getElementById("bar"), teks = document.getElementById("progres-teks");
    if (bar) bar.style.width = nilai.persen + "%";
    if (teks) isiTpl(teks, nilai);
  }
  function kirim(url, hapus) {
    var f = new FormData(); if (hapus) f.append("hapus", "1");
    return fetch(url, { method: "POST", body: f, credentials: "same-origin", headers: { "X-CSRFToken": LianRekam.csrf() } })
      .then(function (r) { if (!r.ok) throw new Error("http"); return r.json(); });
  }
  function kosongkanAntrean() {
    var a = baca(); if (!a.length || !navigator.onLine) return;
    simpan([]);
    a.forEach(function (x) { kirim(x.url, x.hapus).then(perbarui).catch(function () { var b = baca(); b.push(x); simpan(b); }); });
  }
  window.addEventListener("online", kosongkanAntrean);
  kosongkanAntrean();

  function tandai(kartu, tombol) {
    var sudah = tombol.classList.toggle("sudah");
    tombol.setAttribute("aria-pressed", String(sudah));
    var url = kartu.getAttribute("data-progres");
    kirim(url, !sudah).then(perbarui).catch(function () {
      var a = baca(); a.push({ url: url, hapus: !sudah }); simpan(a);    // offline: dikirim saat internet kembali
      // hitung sendiri supaya progress bar tetap bergerak
      var t = document.getElementById("progres-teks");
      if (t) { var n = { selesai: Math.max(0, +t.dataset.done + (sudah ? 1 : -1)), total: +t.dataset.total }; n.persen = n.total ? Math.round(n.selesai * 100 / n.total) : 0; t.dataset.done = n.selesai; perbarui(n); }
    });
  }

  // ---------- Rekam saya ----------
  function mulaiRekam(kartu, tombol) {
    if (sedangRekam) sedangRekam.tutup();
    var galat = kartu.querySelector(".galat"), hasil = kartu.querySelector(".hasil-rekam");
    galat.hidden = true;
    if (!LianRekam.didukung()) { galat.hidden = false; return; }

    function selesai(h) {                       // dipanggil saat berhenti (manual / otomatis) atau dibatalkan (h = null)
      tombol.classList.remove("merekam");
      tombol.querySelector(".lbl-rekam").hidden = false; tombol.querySelector(".lbl-stop").hidden = true;
      sedangRekam = null; tombol._sesi = null;
      if (!h) return;
      var au = hasil.querySelector("audio");
      if (au.src) URL.revokeObjectURL(au.src);
      au.src = h.url; hasil.hidden = false; au.play().catch(function () {});
    }

    LianRekam.mulai({
      maks: 30,
      tick: function (d) { var w = tombol.querySelector(".waktu"); if (w) w.textContent = LianRekam.detik(d); },
      otomatisBerhenti: selesai
    }).then(function (sesi) {
      sedangRekam = { tutup: function () { sesi.batal(); selesai(null); } };
      tombol._sesi = sesi; tombol._selesai = selesai;
      tombol.classList.add("merekam");
      tombol.querySelector(".lbl-rekam").hidden = true; tombol.querySelector(".lbl-stop").hidden = false;
    }).catch(function () { galat.hidden = false; });
  }

  document.addEventListener("click", function (e) {
    var kartu = e.target.closest(".kalimat-kartu");
    var mini = e.target.closest("button[data-tts], .btn-dengar");
    if (mini && !mini.disabled) { bunyikan(mini); return; }
    if (!kartu) return;
    var rekam = e.target.closest(".btn-rekam");
    if (rekam) {
      if (rekam.classList.contains("merekam") && rekam._sesi) { rekam._sesi.berhenti().then(rekam._selesai); }
      else mulaiRekam(kartu, rekam);
      return;
    }
    var belajar = e.target.closest(".btn-belajar");
    if (belajar) tandai(kartu, belajar);
  });
})();
