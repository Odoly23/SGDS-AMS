/** Warna dari bendera Timor-Leste & tais: merah, kuning, hitam, putih. Tanpa biru. */
module.exports = {
  content: ["./templates/**/*.html", "./static/js/**/*.js", "./lian/**/*.py"],
  safelist: ["kartu-merah", "kartu-kuning", "kartu-hitam", "kartu-putih"],   // dipakai dinamis dari data Level
  theme: {
    extend: {
      colors: {
        merah: { DEFAULT: "#C8201A", tua: "#9E1812" },
        kuning: { DEFAULT: "#FFC72C", tua: "#E3A900", muda: "#FFE59A" },
        hitam: "#1B1411",
        kain: "#FFF6E5",   // warna kapas, latar halaman
      },
      fontFamily: {
        sans: ['"Nunito Variable"', "Nunito", "ui-rounded", "system-ui", "-apple-system", '"Segoe UI"', "Roboto", "sans-serif"],
      },
      boxShadow: { timbul: "0 6px 0 rgba(27,20,17,.9)", lembut: "0 4px 14px rgba(27,20,17,.18)" },
    },
  },
};
