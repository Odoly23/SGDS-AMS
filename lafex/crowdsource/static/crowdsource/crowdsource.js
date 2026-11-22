/* Halaman crowdsource "Bantu AI Belajar Bahasa Kamu":
   1) pilih lian  2) pilih estilu  3) tampil 1 kalimat -> rekam -> dengar ulang -> kirim -> terima kasih + penghitung. */
(function () {
  "use strict";
  var $ = function (id) { return document.getElementById(id); };
  var root = $("cs"); if (!root) return;
  var URL_BERIKUT = root.dataset.berikut, URL_KIRIM = root.dataset.kirim;
  var KUNCI = "lafex_cs";
  var st = { bahasa: null, nama: "", gaya: null, gayaNama: "", kalimat: null, sesi: null, hasil: null };

  function simpanPilihan() { try { localStorage.setItem(KUNCI, JSON.stringify({ bahasa: st.bahasa, nama: st.nama, gaya: st.gaya, gayaNama: st.gayaNama })); } catch (e) { /* abaikan */ } }
  function bacaPilihan() { try { return JSON.parse(localStorage.getItem(KUNCI) || "null"); } catch (e) { return null; } }

  function langkah(n) {
    [1, 2, 3].forEach(function (i) { $("langkah" + i).hidden = i !== n; });
    window.scrollTo(0, 0);
  }
  function pesan(idTemplate) {          // tampilkan pesan 4 bahasa dari <template>
    var p = $("pesan");
    if (!idTemplate) { p.hidden = true; return; }
    p.innerHTML = $(idTemplate).innerHTML; p.hidden = false;
  }
  function isiTpl(el, nilai) {
    el.querySelectorAll("[data-tpl]").forEach(function (s) {
      s.textContent = s.getAttribute("data-tpl").replace("{n}", nilai.n == null ? "" : Number(nilai.n).toLocaleString("id-ID")).replace("{lian}", nilai.lian || "");
    });
  }
  function jsonGalat(r) { if (!r.ok) throw new Error("http " + r.status); return r.json(); }

  // ---- langkah 1 & 2: pilihan ----
  document.querySelectorAll(".pilih-lian").forEach(function (b) {
    b.addEventListener("click", function () { st.bahasa = b.dataset.kode; st.nama = b.dataset.nama; langkah(2); });
  });
  document.querySelectorAll(".pilih-gaya").forEach(function (b) {
    b.addEventListener("click", function () {
      st.gaya = b.dataset.kode; st.gayaNama = b.dataset.emoji + " " + b.dataset.nama;
      simpanPilihan(); mulaiLangkah3();
    });
  });
  document.querySelector("[data-ke='1']").addEventListener("click", function () { langkah(1); });
  $("ganti").addEventListener("click", function (e) { e.preventDefault(); batalRekam(); langkah(1); });

  // ---- langkah 3 ----
  function mulaiLangkah3() {
    $("info-lian").textContent = st.nama; $("info-gaya").textContent = st.gayaNama || st.gaya;
    langkah(3); kalimatBerikut();
  }
  function reset() {
    batalRekam(); st.hasil = null;
    $("hasil").hidden = true; $("terima").hidden = true; $("kosong").hidden = true; pesan(null);
    $("mic").hidden = false; $("mic-label").hidden = false; $("timer").hidden = true; $("lewati").hidden = false;
  }
  function kalimatBerikut() {
    reset();
    $("kartu-kalimat").hidden = true;
    if (!navigator.onLine) { pesan("t-offline"); return; }
    fetch(URL_BERIKUT + "?bahasa=" + encodeURIComponent(st.bahasa) + "&gaya=" + encodeURIComponent(st.gaya), { credentials: "same-origin" })
      .then(jsonGalat).then(function (d) {
        if (!d.kalimat) { $("mic").hidden = true; $("mic-label").hidden = true; $("lewati").hidden = true; $("kosong").hidden = false; return; }
        st.kalimat = d.kalimat;
        $("k-emoji").textContent = d.kalimat.emoji || "";
        $("k-tet").textContent = d.kalimat.tet;
        ["en", "pt", "id"].forEach(function (k) {
          var teks = d.kalimat[k === "id" ? "id_" : k] || ""; $("k-" + k).textContent = teks;
          document.querySelector("[data-bahasa='" + k + "']").hidden = !teks;
        });
        isiTpl($("kartu-kalimat"), { lian: st.nama });
        $("kartu-kalimat").hidden = false;
      }).catch(function () { pesan("t-galat"); });
  }

  // ---- rekam ----
  function batalRekam() {
    if (st.sesi) { st.sesi.batal(); st.sesi = null; }
    $("mic").classList.remove("merekam");
  }
  function selesaiRekam(h) {
    st.sesi = null; $("mic").classList.remove("merekam"); $("timer").hidden = true;
    if (!h) return;
    if (h.durasi < 1) { pesan("t-pendek"); $("mic-label").hidden = false; return; }
    st.hasil = h; pesan(null);
    var au = $("putar"); if (au.src) URL.revokeObjectURL(au.src);
    au.src = h.url; $("hasil").hidden = false; $("mic").hidden = true; $("mic-label").hidden = true; $("lewati").hidden = true;
  }
  $("mic").addEventListener("click", function () {
    if (st.sesi) { st.sesi.berhenti().then(selesaiRekam); return; }          // tekan lagi = berhenti
    if (!LafexRekam.didukung()) { pesan("t-mic"); return; }
    pesan(null);
    LafexRekam.mulai({
      maks: 60,
      tick: function (d) { $("timer").textContent = LafexRekam.detik(d); },
      otomatisBerhenti: selesaiRekam
    }).then(function (sesi) {
      st.sesi = sesi; $("mic").classList.add("merekam"); $("timer").hidden = false; $("timer").textContent = "0:00";
    }).catch(function () { pesan("t-mic"); });
  });
  $("ulang").addEventListener("click", function () { st.hasil = null; $("hasil").hidden = true; $("mic").hidden = false; $("mic-label").hidden = false; $("lewati").hidden = false; pesan(null); });
  $("lewati").addEventListener("click", kalimatBerikut);
  $("lagi").addEventListener("click", kalimatBerikut);

  // ---- kirim ----
  $("kirim").addEventListener("click", function () {
    if (!st.hasil || !st.kalimat) return;
    if (!navigator.onLine) { pesan("t-offline"); return; }
    var tombol = $("kirim"); tombol.disabled = true; pesan("t-kirim");
    var ext = /ogg/.test(st.hasil.mime) ? "ogg" : /mp4|aac/.test(st.hasil.mime) ? "m4a" : /mpeg|mp3/.test(st.hasil.mime) ? "mp3" : "webm";
    var f = new FormData();
    f.append("audio", st.hasil.blob, "rekaman." + ext);
    f.append("kalimat", st.kalimat.id); f.append("bahasa", st.bahasa); f.append("gaya", st.gaya); f.append("durasi", st.hasil.durasi);
    fetch(URL_KIRIM, { method: "POST", body: f, credentials: "same-origin", headers: { "X-CSRFToken": LafexRekam.csrf() } })
      .then(jsonGalat).then(function (d) {
        tombol.disabled = false; pesan(null);
        $("hasil").hidden = true; st.hasil = null;
        isiTpl($("penghitung"), { n: d.total, lian: d.bahasa });
        $("terima").hidden = false;
        var btn = document.querySelector(".pilih-lian[data-kode='" + st.bahasa + "']");   // perbarui angka di langkah 1
        if (btn) { btn.querySelector(".jumlah").innerHTML = '<i class="fa fa-microphone"></i> ' + d.total; }
      }).catch(function () { tombol.disabled = false; pesan("t-galat"); });
  });

  // ---- pilihan tersimpan dari kunjungan sebelumnya ----
  // ---- contoh suara kalimat: XTTS milik sendiri bila sudah dipasang; bila tidak, suara browser (tidak ada suara Tetun: pt-PT sebagai pendekatan) ----
  function putarContoh() {
    var teks = $("k-tet").textContent.trim().slice(0, 300); if (!teks) return;
    function browser() {
      try { speechSynthesis.cancel(); var u = new SpeechSynthesisUtterance(teks); u.lang = "pt-PT"; speechSynthesis.speak(u); } catch (e) { /* tanpa suara */ }
    }
    fetch(root.dataset.tts, { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json", "X-CSRFToken": LafexRekam.csrf() }, body: JSON.stringify({ teks: teks }) })
      .then(function (r) { if (!r.ok) throw new Error("tts"); return r.blob(); })
      .then(function (b) { var a = new Audio(URL.createObjectURL(b)); return a.play(); })
      .catch(browser);
  }
  if ($("contoh")) $("contoh").addEventListener("click", putarContoh);

  var tersimpan = bacaPilihan();
  if (tersimpan && tersimpan.bahasa && tersimpan.gaya && document.querySelector(".pilih-lian[data-kode='" + tersimpan.bahasa + "']") && document.querySelector(".pilih-gaya[data-kode='" + tersimpan.gaya + "']")) {
    st.bahasa = tersimpan.bahasa; st.nama = tersimpan.nama; st.gaya = tersimpan.gaya; st.gayaNama = tersimpan.gayaNama;
    mulaiLangkah3();
  }
})();
