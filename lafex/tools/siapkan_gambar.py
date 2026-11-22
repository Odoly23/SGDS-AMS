#!/usr/bin/env python3
"""
Siapkan gambar maskot LAFEX untuk halaman Video Call: latar putih -> transparan, semua pose dipotong dengan KOTAK YANG SAMA
(supaya LAFEX tidak "melompat" saat pose berganti), diperkecil, lalu disimpan sebagai <mode>_<pose>.png.

Contoh:
  python tools/siapkan_gambar.py --mode preman --out ai/static/img/lafex \
      --diam a.jpg --ngomong b.jpg --jempol c.jpg --mikir d.jpg [--lambai e.jpg]
Butuh:  pip install pillow numpy scipy
Tiga metode latar: putih polos (--latar putih, bawaan), pastel bergambar (--latar warna), rumit/kantor (--latar model, butuh rembg). Periksa hasilnya dengan mata: potongan otomatis bisa
meninggalkan sedikit sisa bayangan atau memakan bagian putih yang menyentuh tepi gambar.
"""
import argparse
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

CELAH_MIN = 5000          # luas (piksel, pada gambar 1600 px) minimal agar putih terkurung dianggap latar
LUBANG_MODEL_MAKS = 6000    # latar model: lubang terkurung lebih kecil dari ini (piksel) ditutup
LUBANG_WARNA_MAKS = 40000   # latar berwarna: bagian PUCAT milik maskot (mis. sisi halaman buku) yang terkurung ikut ditutup
POSE = ('diam', 'ngomong', 'jempol', 'mikir', 'lambai')


def buat_alfa(rgb):
	"""Alfa: piksel putih/abu muda polos yang TERHUBUNG ke tepi gambar dianggap latar."""
	r, g, b = (rgb[..., i].astype(int) for i in range(3))
	terang = np.minimum(np.minimum(r, g), b) >= 200
	polos = (np.maximum(np.maximum(r, g), b) - np.minimum(np.minimum(r, g), b)) <= 12      # putih/abu, bukan krem/berwarna
	kandidat = terang & polos
	label, n = ndimage.label(kandidat)
	tepi = np.unique(np.concatenate([label[0], label[-1], label[:, 0], label[:, -1]]))
	ukuran = ndimage.sum(kandidat, label, range(1, n + 1)) if n else []
	besar = {i + 1 for i, u in enumerate(ukuran) if u >= CELAH_MIN}        # celah latar besar yang terkurung (antar kaki/ekor) ikut dibuang
	latar = np.isin(label, [t for t in tepi if t > 0] + sorted(besar))     # putih kecil (gigi, mata, huruf) tetap bagian maskot
	depan = ~latar
	depan = ndimage.binary_opening(depan, iterations=1)                    # buang bintik kecil
	label, n = ndimage.label(depan)
	if n > 1:                                                              # simpan hanya benda terbesar (maskot), buang kotoran
		ukuran = ndimage.sum(depan, label, range(1, n + 1))
		depan = label == (1 + int(np.argmax(ukuran)))
	lubang = ndimage.binary_fill_holes(depan) & ~depan                      # tutup lubang KECIL saja (mis. pantulan di kacamata)
	lab, m = ndimage.label(lubang)
	if m:
		kecil = [i + 1 for i, u in enumerate(ndimage.sum(lubang, lab, range(1, m + 1))) if u < CELAH_MIN]
		depan = depan | np.isin(lab, kecil)
	depan = ndimage.binary_erosion(depan, iterations=1)                    # kikis 1 piksel agar tepi tidak berpinggiran putih
	alfa = ndimage.gaussian_filter(depan.astype(float), 0.9)               # tepi halus
	return np.clip(alfa * 255, 0, 255).astype('uint8'), depan


def buat_alfa_warna(rgb, ambang=0.24):
	"""Untuk latar BERGAMBAR/berwarna pucat (mis. ruang kelas pastel): maskot berwarna JENUH, latar pucat. Alfa dari kejenuhan warna;
	hanya benda jenuh TERBESAR (maskot) yang dipertahankan, sehingga tulisan/benda di latar terbuang."""
	a = rgb.astype(float) / 255
	mx, mn = a.max(2), a.min(2)
	jenuh = (mx - mn) / np.maximum(mx, 1e-6)
	depan = ndimage.binary_opening(jenuh > ambang, iterations=2)
	label, n = ndimage.label(depan)
	if n > 1:
		ukuran = ndimage.sum(depan, label, range(1, n + 1))
		depan = label == (1 + int(np.argmax(ukuran)))
	depan = ndimage.binary_closing(depan, iterations=3)                      # sambungkan bingkai kacamata dsb.
	lubang = ndimage.binary_fill_holes(depan) & ~depan                      # tutup lubang KECIL saja
	lab, m = ndimage.label(lubang)
	if m:
		kecil = [i + 1 for i, u in enumerate(ndimage.sum(lubang, lab, range(1, m + 1))) if u < LUBANG_WARNA_MAKS]
		depan = depan | np.isin(lab, kecil)
	depan = ndimage.binary_erosion(depan, iterations=1)
	alfa = ndimage.gaussian_filter(depan.astype(float), 1.0)
	return np.clip(alfa * 255, 0, 255).astype('uint8'), depan


def buat_alfa_model(rgb, sesi, roi=None):
	"""Untuk latar RUMIT (kantor, jas hitam, kemeja putih) yang tidak bisa dipisah dengan warna: model segmentasi (rembg/ISNet).
	Alfa dikeraskan agar tidak ada sisa bayangan setengah-transparan; hanya benda terbesar (maskot) yang dipertahankan."""
	from rembg import remove
	mentah = np.asarray(remove(Image.fromarray(rgb), session=sesi))[..., 3].astype(float) / 255
	alfa = np.clip((mentah - 0.35) / 0.30, 0, 1)                            # keraskan: <0.35 hilang, >0.65 penuh
	# Model sering ragu pada bagian yang menumpuk di latar mirip (mis. ekor di atas meja krem) -> tembus pandang. Pulihkan area yang model
	# anggap ADA benda (alfa mentah > 0.12) DAN berwarna (jenuh, bukan putih/krem pucat) selama TERSAMBUNG ke badan yang pasti.
	f = rgb.astype(float) / 255
	jenuh = (f.max(2) - f.min(2)) / np.maximum(f.max(2), 1e-6)
	calon = (mentah > 0.10) & (jenuh > 0.06)
	dekat = ndimage.binary_dilation(alfa > 0.9, iterations=90)                # hanya yang dekat badan (bukan tanaman/benda jauh)
	alfa = np.maximum(alfa, (calon & dekat).astype(float))
	if roi:                                                                 # model gagal melihat bagian tertentu (mis. ekor): pulihkan lewat WARNA di kotak roi
		x0, y0, x1, y1 = roi
		hsv = np.asarray(Image.fromarray(rgb).convert('HSV')).astype(float)
		hue, sat, val = hsv[..., 0] * 360 / 255, hsv[..., 1] / 255, hsv[..., 2] / 255
		hijau = (hue >= 45) & (hue <= 150) & (sat > 0.17) & (val > 0.2)    # hijau/kuning-hijau; lantai krem (hue ~30-40) tidak ikut
		kotak = np.zeros_like(hijau); kotak[y0:y1, x0:x1] = True
		pulih = ndimage.binary_opening(hijau & kotak, iterations=1)
		lab, m = ndimage.label(pulih)
		if m:
			besar = [i + 1 for i, u in enumerate(ndimage.sum(pulih, lab, range(1, m + 1))) if u >= 800]
			pulih = np.isin(lab, besar)
		pulih = ndimage.binary_fill_holes(ndimage.binary_closing(pulih, iterations=3))
		alfa = np.maximum(alfa, pulih.astype(float))
	depan = alfa > 0.5
	label, n = ndimage.label(depan)
	if n > 1:                                                               # buang kotoran kecil, TAPI pertahankan bagian besar yang terpisah (mis. ekor di balik kaki)
		ukuran = ndimage.sum(depan, label, range(1, n + 1))
		simpan = [i + 1 for i, u in enumerate(ukuran) if u >= 0.02 * ukuran.max()]
		depan = np.isin(label, simpan)
	lubang = ndimage.binary_fill_holes(depan) & ~depan                      # lubang KECIL di dalam badan (mis. kemeja putih yang dikira latar) ditutup
	lab, m = ndimage.label(lubang)                                          # celah BESAR (antara lengan dan badan) tetap tembus
	if m:
		kecil = [i + 1 for i, u in enumerate(ndimage.sum(lubang, lab, range(1, m + 1))) if u < LUBANG_MODEL_MAKS]
		depan = depan | np.isin(lab, kecil)
	dekat = ndimage.binary_dilation(depan, iterations=2)
	inti = ndimage.binary_erosion(depan, iterations=3)
	alfa = np.where(inti, 1.0, alfa * dekat)                                # bagian dalam penuh, hanya tepi yang halus
	alfa = ndimage.gaussian_filter(alfa, 0.7)
	return np.clip(alfa * 255, 0, 255).astype('uint8'), depan


def main():
	a = argparse.ArgumentParser()
	a.add_argument('--mode', required=True, help='preman | pintar | pro')
	a.add_argument('--out', required=True)
	for p in POSE:
		a.add_argument(f'--{p}')
	a.add_argument('--tinggi', type=int, default=900, help='tinggi akhir (piksel)')
	a.add_argument('--latar', choices=('putih', 'warna', 'model'), default='putih',
	             help="putih = latar putih polos; warna = latar bergambar pucat (maskot lebih jenuh); model = latar rumit, pakai rembg (pip install rembg onnxruntime)")
	a.add_argument('--pulih', help="x0,y0,x1,y1 (piksel pada gambar setelah dipotong atas/bawah): pulihkan bagian hijau yang gagal dilihat model, mis. ekor")
	a.add_argument('--atas', type=float, default=0.0, help='buang bagian atas gambar (pecahan 0-1), mis. 0.15 untuk judul')
	a.add_argument('--bawah', type=float, default=1.0, help='simpan sampai pecahan ini (0-1), mis. 0.865 untuk membuang tulisan di bawah')
	a.add_argument('--ambang', type=float, default=0.24, help='ambang kejenuhan untuk --latar warna')
	o = a.parse_args()
	pakai = [(p, getattr(o, p)) for p in POSE if getattr(o, p)]
	if not all(os.path.exists(f) for _, f in pakai):
		sys.exit('Ada berkas masukan yang tidak ditemukan.')
	hasil, kotak = {}, None
	sesi = None
	if o.latar == 'model':
		from rembg import new_session
		sesi = new_session('isnet-general-use')
	for pose, f in pakai:
		im = Image.open(f).convert('RGB')
		if o.atas > 0 or o.bawah < 1:
			im = im.crop((0, int(im.height * o.atas), im.width, int(im.height * o.bawah)))
		rgb = np.asarray(im)
		if o.latar == 'putih':
			alfa, depan = buat_alfa(rgb)
		elif o.latar == 'warna':
			alfa, depan = buat_alfa_warna(rgb, o.ambang)
		else:
			alfa, depan = buat_alfa_model(rgb, sesi, tuple(int(v) for v in o.pulih.split(',')) if o.pulih else None)
		ys, xs = np.where(depan)
		k = (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)
		kotak = k if kotak is None else (min(kotak[0], k[0]), min(kotak[1], k[1]), max(kotak[2], k[2]), max(kotak[3], k[3]))
		rgba = np.dstack([np.asarray(im), alfa])
		hasil[pose] = Image.fromarray(rgba, 'RGBA')
	pad = 12
	w, h = next(iter(hasil.values())).size
	kotak = (max(0, kotak[0] - pad), max(0, kotak[1] - pad), min(w, kotak[2] + pad), min(h, kotak[3] + pad))
	os.makedirs(o.out, exist_ok=True)
	for pose, im in hasil.items():
		im = im.crop(kotak)
		skala = o.tinggi / im.height
		im = im.resize((round(im.width * skala), o.tinggi), Image.LANCZOS)
		jalur = os.path.join(o.out, f'{o.mode}_{pose}.png')
		im.save(jalur, optimize=True)
		print(f'{jalur}  {im.width}x{im.height}  {os.path.getsize(jalur) // 1024} KB')
	print('Kotak potong (sama untuk semua pose):', kotak)


if __name__ == '__main__':
	main()
