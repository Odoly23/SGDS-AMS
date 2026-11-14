/* Ko'alia ho AI - percakapan suara langsung dengan lafaek.
   Alur:  tekan lafaek -> DENGAR (pengenalan suara browser) -> PIKIR (kirim teks ke server) -> BICARA (suara + teks) -> dengar lagi (mode langsung).
   Batas teknis yang jujur:
   - Pengenalan suara memakai Web Speech API milik browser (Chrome/Edge/Safari); browser bisa mengirim suara ke layanan vendornya. Tidak ada
     pengenalan suara untuk Tetun, jadi Tetun memakai mesin Portugis sebagai perkiraan (bisa salah dengar). Mengetik selalu tersedia.
   - HP tidak punya suara Tetun: bagian Tetun dibacakan dengan suara Portugis sebagai perkiraan, bagian Inggris dengan suara Inggris. */
(function () {
  "use strict";
  var $ = function (id) { return document.getElementById(id); };
  var root = $("ai"); if (!root) return;
  var D = root.dataset;
  var KUNCI = "lian_ai";
  var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  var MESIN = { tet: "pt-PT", en: "en-US", pt: "pt-PT", id: "id-ID" };      // bahasa ucap -> mesin pengenalan suara
  var GERAK_EMOJI = { lambai: "👋", angguk: "🙂", tertawa: "😄", jempol: "👍", tunjuk: "☝️", pikir: "🤔", bungkuk: "🙏", senyum: "😊" };
  var GERAK_BAWAAN = { preman: "jempol", sopan: "senyum", profesional: "angguk" };     // bila AI tidak memilih gerak
  var st = { karakter: null, nama: "", keadaan: "diam", rec: null, berhenti: false, tanpaSuara: 0, terakhir: null, sisa: parseInt(D.sisa, 10) || 0, mulut: null, nomor: 0 };

  // ---------------------------------------------------------------- bantuan
  function simpan() { try { localStorage.setItem(KUNCI, JSON.stringify({ karakter: st.karakter, nama: st.nama, bahasa: $("bahasa").value, live: $("live").checked })); } catch (e) { /* abaikan */ } }
  function baca() { try { return JSON.parse(localStorage.getItem(KUNCI) || "null"); } catch (e) { return null; } }
  function pesan(kunci) {
    var p = $("pesan");
    if (!kunci) { p.hidden = true; return; }
    var t = $("t-" + kunci); p.innerHTML = t ? t.innerHTML : ""; p.hidden = false;
  }
  function keadaan(k) {
    st.keadaan = k; $("lafaek").setAttribute("data-keadaan", k);
    document.querySelectorAll("#status [data-s]").forEach(function (s) { s.hidden = s.getAttribute("data-s") !== k; });
    clearInterval(st.mulut); st.mulut = null;
    var img = $("img-lafaek"); img.src = D.lafaek;
    if (k === "bicara") {                         // lafaek "berbicara": mulut membuka-menutup selama suara AI
      var buka = false;
      st.mulut = setInterval(function () { buka = !buka; img.src = buka ? D.lafaekBuka : D.lafaek; }, 190);
    }
    if (k !== "dengar") $("sementara").textContent = "";
  }
  function isiSisa() {
    $("sisa").querySelectorAll("[data-tpl]").forEach(function (s) { s.textContent = s.getAttribute("data-tpl").replace("{n}", st.sisa); });
  }
  function gulir() {        // gulir sampai gelembung terbaru terlihat DI ATAS panel lafaek yang menempel di bawah layar
    var o = $("obrolan"), panel = document.querySelector(".kontrol-ai");
    if (!o.lastChild) return;
    o.lastChild.style.scrollMarginBottom = (panel.offsetHeight + 16) + "px";
    o.lastChild.scrollIntoView({ block: "end", behavior: "smooth" });
  }
  function potongSuara() { st.nomor++; if (window.speechSynthesis) speechSynthesis.cancel(); }   // nomor baru = suara lama tidak boleh lanjut

  // ---------------------------------------------------------------- gelembung obrolan (textContent -> aman dari XSS)
  function gelembungUser(teks) {
    var g = document.createElement("div"); g.className = "gelembung user"; g.textContent = teks; $("obrolan").appendChild(g); gulir();
  }
  function gelembungAI(d) {
    var g = document.createElement("div"); g.className = "gelembung ai";
    var r = document.createElement("button"); r.type = "button"; r.className = "rona"; r.innerHTML = '<i class="fa fa-volume-up"></i>';
    r.addEventListener("click", function () { ucapkan(d); });
    var tet = document.createElement("div"); tet.className = "tet"; tet.textContent = d.tet;
    g.appendChild(r); g.appendChild(tet);
    if (d.en) { var en = document.createElement("div"); en.className = "en"; en.textContent = d.en; g.appendChild(en); }
    if (d.koreksi) {
      var k = document.createElement("div"); k.className = "koreksi";
      var h = document.createElement("i"); h.className = "fa fa-pencil"; k.appendChild(h);
      k.appendChild(document.createTextNode(" "));
      k.appendChild(document.importNode($("t-ai_correction").content, true));        // label "Koresaun / Correction / Correção / Koreksi" sesuai bahasa terpilih
      k.appendChild(document.createTextNode(": " + d.koreksi)); g.appendChild(k);
    }
    $("obrolan").appendChild(g); gulir();
  }

  // ---------------------------------------------------------------- gerak-gerik lafaek
  function gerakkan(d) {
    var nama = d.gerak && GERAK_EMOJI[d.gerak] ? d.gerak : (d.koreksi ? "tunjuk" : (GERAK_BAWAAN[st.karakter] || "senyum"));
    var g = $("gerak"), e = $("emoji-gerak");
    g.className = "gerak"; e.className = "emoji-gerak"; void g.offsetWidth;          // mulai ulang animasi
    g.classList.add("gerak-" + nama); g.setAttribute("data-gerak", nama);
    e.textContent = GERAK_EMOJI[nama]; e.classList.add("tampil");
    clearTimeout(st.tGerak); st.tGerak = setTimeout(function () { g.className = "gerak"; e.className = "emoji-gerak"; }, 1600);
  }

  // ---------------------------------------------------------------- suara AI (SpeechSynthesis)
  function suara(lang) {
    var vs = window.speechSynthesis ? speechSynthesis.getVoices() : [], l = lang.toLowerCase();
    return vs.filter(function (v) { return v.lang.toLowerCase() === l; })[0] || vs.filter(function (v) { return v.lang.toLowerCase().indexOf(l.slice(0, 2)) === 0; })[0] || null;
  }
  function ucapkan(d, selesai) {
    st.terakhir = d; $("ulang").disabled = false; gerakkan(d);
    if (!("speechSynthesis" in window)) { if (selesai) selesai(); return; }
    potongSuara(); var nomor = st.nomor;
    var bagian = [];
    if (d.tet) bagian.push({ teks: d.tet, lang: "pt-PT" });       // Tetun: suara Portugis sebagai PERKIRAAN
    if (d.en) bagian.push({ teks: d.en, lang: "en-US" });
    bagian = bagian.filter(function (b) { return suara(b.lang); });
    if (!bagian.length) { if (selesai) selesai(); return; }
    keadaan("bicara");
    var i = 0;
    (function lanjut() {
      if (nomor !== st.nomor) return;                  // sudah dipotong/diganti: berhenti total
      if (st.berhenti || i >= bagian.length) { if (st.keadaan === "bicara") keadaan("diam"); if (selesai && !st.berhenti) selesai(); return; }
      var b = bagian[i++], u = new SpeechSynthesisUtterance(b.teks);
      u.lang = b.lang; u.voice = suara(b.lang); u.rate = 0.92;
      u.onend = u.onerror = lanjut;
      speechSynthesis.speak(u);
    })();
  }

  // ---------------------------------------------------------------- dengar (SpeechRecognition)
  function dengar() {
    if (st.rec) return;
    if (!SR) { pesan("ai_no_support"); $("teks").focus(); return; }
    potongSuara();
    st.berhenti = false; pesan(null);
    var rec = new SR(), final = "";
    st.rec = rec; rec.lang = MESIN[$("bahasa").value] || "pt-PT"; rec.interimResults = true; rec.maxAlternatives = 1; rec.continuous = false;
    rec.onresult = function (e) {
      var sementara = "";
      for (var i = e.resultIndex; i < e.results.length; i++) {
        if (e.results[i].isFinal) final += e.results[i][0].transcript + " "; else sementara += e.results[i][0].transcript;
      }
      $("sementara").textContent = (final + sementara).trim();
    };
    rec.onerror = function (e) {
      if (e.error === "not-allowed" || e.error === "service-not-allowed") { pesan("mic_error"); st.berhenti = true; }
      else if (e.error !== "no-speech" && e.error !== "aborted") pesan("ai_no_speech");
    };
    rec.onend = function () {
      st.rec = null;
      var teks = final.trim();
      if (teks && !st.berhenti) { st.tanpaSuara = 0; kirim(teks, true); return; }
      if (st.keadaan !== "dengar") return;
      keadaan("diam");
      if (!st.berhenti && $("live").checked && ++st.tanpaSuara < 2) { dengar(); return; }       // coba sekali lagi, lalu berhenti
      if (!st.berhenti) pesan("ai_no_speech");
      st.tanpaSuara = 0;
    };
    try { rec.start(); keadaan("dengar"); } catch (e) { st.rec = null; keadaan("diam"); pesan("mic_error"); }
  }
  function hentikanDengar() { if (st.rec) { try { st.rec.abort(); } catch (e) { /* abaikan */ } st.rec = null; } }

  // ---------------------------------------------------------------- kirim ke server
  function kirim(teks, dariSuara) {
    gelembungUser(teks); keadaan("pikir"); pesan(null);
    fetch(D.bicara, {
      method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-CSRFToken": LianRekam.csrf() },
      body: JSON.stringify({ teks: teks, karakter: st.karakter, bahasa: $("bahasa").value })
    }).then(function (r) { return r.json().then(function (d) { return { s: r.status, d: d }; }); })
      .then(function (x) {
        var d = x.d;
        if (d.ok) {
          st.sisa = d.sisa; isiSisa(); gelembungAI(d);
          ucapkan(d, function () { if (dariSuara && $("live").checked && !st.berhenti) dengar(); else keadaan("diam"); });
          if (st.keadaan === "pikir") keadaan("diam");
        } else {
          keadaan("diam");
          pesan(d.kode === "batas" ? "ai_limit" : d.kode === "laju" ? "ai_slow" : "ai_error");
          if (d.kode === "batas") { st.sisa = 0; isiSisa(); }
        }
      }).catch(function () { keadaan("diam"); pesan("ai_error"); });
  }

  // ---------------------------------------------------------------- tombol & pilihan
  $("lafaek").addEventListener("click", function () {
    if (st.keadaan === "dengar") { if (st.rec) st.rec.stop(); return; }          // tekan lagi = selesai bicara
    if (st.keadaan === "bicara") { potongSuara(); keadaan("diam"); }                  // potong AI, giliran Anda
    if (st.keadaan === "pikir") return;
    dengar();
  });
  $("berhenti").addEventListener("click", function () {
    st.berhenti = true; hentikanDengar(); potongSuara(); keadaan("diam"); pesan(null);
  });
  $("ulang").addEventListener("click", function () { if (st.terakhir) { st.berhenti = false; hentikanDengar(); ucapkan(st.terakhir); } });
  $("ketik").addEventListener("submit", function (e) {
    e.preventDefault(); var t = $("teks").value.trim(); if (!t || st.keadaan === "pikir") return;
    $("teks").value = ""; hentikanDengar(); kirim(t, false);
  });
  $("bahasa").addEventListener("change", function () { $("cat-tet").hidden = $("bahasa").value !== "tet"; simpan(); });
  $("live").addEventListener("change", simpan);
  $("hapus").addEventListener("click", function (e) {
    e.preventDefault();
    fetch(D.hapus, { method: "POST", credentials: "same-origin", headers: { "X-CSRFToken": LianRekam.csrf() } })
      .then(function (r) { return r.json(); }).then(function () { $("obrolan").innerHTML = ""; st.terakhir = null; $("ulang").disabled = true; pesan("ai_cleared"); });
  });
  $("ganti").addEventListener("click", function (e) { e.preventDefault(); $("berhenti").click(); $("obrol").hidden = true; $("pilih").hidden = false; });

  function mulai(kode, nama, emoji, aksesori) {
    st.karakter = kode; $("lafaek").setAttribute("data-gaya", kode); if (aksesori) $("aks-lafaek").src = aksesori; st.nama = emoji + " " + nama; $("info-karakter").textContent = st.nama;
    $("pilih").hidden = true; $("obrol").hidden = false; $("obrolan").innerHTML = ""; $("cat-tet").hidden = $("bahasa").value !== "tet";
    simpan(); keadaan("diam"); isiSisa();
    fetch(D.riwayat + "?karakter=" + encodeURIComponent(kode), { credentials: "same-origin" }).then(function (r) { return r.json(); }).then(function (d) {
      (d.riwayat || []).forEach(function (g) { gelembungUser(g.ucapan); gelembungAI(g); st.terakhir = g; $("ulang").disabled = false; });
      window.scrollTo(0, 0);
    }).catch(function () { /* riwayat opsional */ });
  }
  document.querySelectorAll(".pilih-karakter").forEach(function (b) {
    b.addEventListener("click", function () { mulai(b.dataset.kode, b.dataset.nama, b.dataset.emoji, b.dataset.aksesori); });
  });

  if (window.speechSynthesis) { speechSynthesis.getVoices(); speechSynthesis.onvoiceschanged = function () {}; }
  var s = baca();
  if (s) {
    if (s.bahasa) $("bahasa").value = s.bahasa;
    if (typeof s.live === "boolean") $("live").checked = s.live;
    var b = s.karakter && document.querySelector(".pilih-karakter[data-kode='" + s.karakter + "']");
    if (b) mulai(b.dataset.kode, b.dataset.nama, b.dataset.emoji, b.dataset.aksesori);
  }
  isiSisa();
})();
