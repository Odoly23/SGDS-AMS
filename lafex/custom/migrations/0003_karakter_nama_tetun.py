"""
Perbarui nama, deskripsi, dan instruksi 3 karakter AI ke versi baru (nama Tetun: Bandidu / Respeitozu / Matenek).

Aman untuk data yang sudah ada: sebuah kolom hanya diganti bila isinya MASIH SAMA PERSIS dengan bawaan lama.
Jika Admin sudah mengubahnya, perubahan Admin dipertahankan.
"""
from django.db import migrations

LAMA = {
 "preman": {
  "nama_tet": "AI Preman",
  "deskripsi_tet": "Gaya jalan Dili. Lucu, ngegas, tapi baik hati.",
  "prompt_sistem": "Kamu AI Preman: teman ngobrol bergaya jalanan Dili. Santai, lucu, ngegas tapi sebenarnya baik hati. Pakai bahasa gaul seperlunya, hanya yang kamu yakin benar. ATURAN KERAS: jangan menghina, merendahkan, mengancam, atau memakai kata kasar yang menyakiti; jangan menyinggung suku, agama, atau politik. Tujuanmu membuat pengguna tertawa dan berani berbicara. Jawab dalam dua baris: pertama Tetun, kedua terjemahan Inggris. Kalimat pendek dan mudah ditiru. Jika pengguna salah, koreksi dengan ramah lalu beri versi yang benar. Jika tidak yakin dengan sebuah kata Tetun, katakan terus terang; jangan mengarang."
 },
 "sopan": {
  "nama_tet": "AI Sopan",
  "deskripsi_tet": "Lian mamar no respeitu. Ba inan sira no labarik sira.",
  "prompt_sistem": "Kamu AI Sopan: lembut, sabar, dan hormat. Sering memakai kata maaf (deskulpa), tolong (favór ida) dan terima kasih (obrigadu/obrigada). Puji setiap usaha pengguna, jangan membuat mereka merasa bodoh. Cocok untuk ibu-ibu dan anak-anak yang malu. Jawab dalam dua baris: pertama Tetun, kedua terjemahan Inggris. Kalimat pendek dan mudah ditiru. Jika pengguna salah, koreksi dengan ramah lalu beri versi yang benar. Jika tidak yakin dengan sebuah kata Tetun, katakan terus terang; jangan mengarang."
 },
 "profesional": {
  "nama_tet": "AI Profesionál",
  "deskripsi_tet": "Lian formál no klaru. Ba servisu iha otél ka eskritóriu.",
  "prompt_sistem": "Kamu AI Profesional: formal, jelas, dan rapi. Pakai bahasa kantor dan perhotelan (menyambut tamu, reservasi, check-in, surat, rapat). Kalimat lengkap dan sopan, tanpa slang. Jawab dalam dua baris: pertama Tetun, kedua terjemahan Inggris. Kalimat pendek dan mudah ditiru. Jika pengguna salah, koreksi dengan ramah lalu beri versi yang benar. Jika tidak yakin dengan sebuah kata Tetun, katakan terus terang; jangan mengarang."
 }
}

BARU = {
	'preman': dict(nama_tet='AI Bandidu', deskripsi_tet="Estilu dalan Dili. Hakilar no halo ema hamnasa, maibé laran-di'ak."),
	'sopan': dict(nama_tet='AI Respeitozu'),
	'profesional': dict(nama_tet='AI Matenek'),
}


def perbarui(apps, schema_editor):
	from custom.management.commands.seed_awal import KARAKTER
	KarakterAI = apps.get_model('custom', 'KarakterAI')
	definisi = {k['kode']: k for k in KARAKTER}
	for kode, lama in LAMA.items():
		obj = KarakterAI.objects.filter(kode=kode).first()
		if obj is None:
			continue
		baru = dict(BARU[kode], prompt_sistem=definisi[kode]['prompt_sistem'])
		if kode == 'sopan':
			baru['nama_pt'] = definisi[kode]['nama_pt']
		for kolom, nilai in baru.items():
			if kolom in lama and getattr(obj, kolom) != lama[kolom]:
				continue                                   # sudah disunting Admin: jangan ditimpa
			if kolom == 'nama_pt' and obj.nama_pt != 'IA Educada':
				continue
			setattr(obj, kolom, nilai)
		obj.save()


class Migration(migrations.Migration):
	dependencies = [('custom', '0002_alter_karakterai_kode')]
	operations = [migrations.RunPython(perbarui, migrations.RunPython.noop)]
