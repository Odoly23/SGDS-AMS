#!/usr/bin/env python3
"""
Fine-tune Whisper dengan data crowdsource LAFEX (Tetun / bahasa daerah).

Masukan  : folder hasil `python manage.py export_suara`  ->  <DATA>/train.jsonl + <DATA>/wavs/*.wav (16 kHz mono)
           (hanya rekaman DISETUJUI dengan transkripsi dari kontributor/admin; draf Whisper tidak ikut)
Keluaran : model Whisper hasil latih (+ processor) di --out, siap dikonversi untuk faster-whisper (lihat docs/MELATIH_SUARA.md)

Contoh (Colab/Kaggle dengan GPU T4 gratis, model small):
    pip install -U transformers accelerate soundfile peft
    python finetune_whisper.py --data data_suara/whisper --out hasil/whisper-tet --model openai/whisper-small --epochs 8

GPU kecil / model lebih besar:  tambahkan --lora (melatih adapter kecil; jauh lebih hemat memori)

STATUS JUJUR: logika data/metrik diuji otomatis; bagian pelatihan penuh BELUM pernah dijalankan pada GPU dan model asli di
lingkungan pembuatan. Jalankan dulu dengan --max-steps 20 untuk memastikan semuanya jalan di mesin Anda.
"""
import argparse
import hashlib
import json
import os
import random
import sys
import unicodedata

SR = 16000
MAKS_DETIK = 30.0            # batas Whisper: 30 detik per potongan


# ====================================================================== bagian murni (tanpa PyTorch; diuji otomatis)
def normalisasi(teks):
	"""Untuk menghitung WER: huruf kecil, tanpa tanda baca, spasi rapi. Apostrof Tetun (ha'u) tetap dihitung bagian kata."""
	teks = unicodedata.normalize('NFKC', teks).lower().replace('’', "'").replace('`', "'")
	keluar = []
	for ch in teks:
		keluar.append(ch if (ch.isalnum() or ch == "'") else ' ')
	return ' '.join(''.join(keluar).split())


def _jarak(a, b):
	"""Jarak edit (Levenshtein) antar dua daftar kata."""
	if not a:
		return len(b)
	sebelum = list(range(len(b) + 1))
	for i, x in enumerate(a, 1):
		now = [i]
		for j, y in enumerate(b, 1):
			now.append(min(sebelum[j] + 1, now[j - 1] + 1, sebelum[j - 1] + (x != y)))
		sebelum = now
	return sebelum[-1]


def wer(acuan, hipotesis):
	"""Word Error Rate (persen) untuk daftar kalimat. Acuan kosong diabaikan."""
	salah = total = 0
	for r, h in zip(acuan, hipotesis):
		kata_r, kata_h = normalisasi(r).split(), normalisasi(h).split()
		if not kata_r:
			continue
		salah += _jarak(kata_r, kata_h)
		total += len(kata_r)
	return 100.0 * salah / total if total else 0.0


def baca_manifest(folder):
	"""Baca train.jsonl -> daftar {'audio': path mutlak, 'text': str}. Baris rusak/berkas hilang dilewati dan dihitung."""
	jalur = os.path.join(folder, 'train.jsonl')
	if not os.path.exists(jalur):
		raise SystemExit(f'{jalur} tidak ada. Jalankan dulu: python manage.py export_suara --out ...')
	data, lewat = [], 0
	with open(jalur, encoding='utf-8') as f:
		for baris in f:
			baris = baris.strip()
			if not baris:
				continue
			try:
				d = json.loads(baris)
				audio, teks = os.path.join(folder, d['audio']), str(d['text']).strip()
			except (ValueError, KeyError, TypeError):
				lewat += 1
				continue
			if not teks or not os.path.exists(audio):
				lewat += 1
				continue
			data.append({'audio': audio, 'text': teks})
	return data, lewat


def bagi(data, persen_dev=10, benih=13):
	"""
	Bagi train/dev berdasarkan ISI KALIMAT (bukan acak per rekaman): kalimat yang sama yang diucapkan beberapa orang
	harus masuk ke sisi yang sama, kalau tidak WER dev akan terlalu bagus (kebocoran). Nama penutur sengaja tidak disimpan
	(privasi), jadi ini cara terbaik yang tersedia. Minimal 1 contoh dev bila data cukup.
	"""
	def kunci(d):
		return int(hashlib.sha1((str(benih) + normalisasi(d['text'])).encode()).hexdigest(), 16) % 100
	dev = [d for d in data if kunci(d) < persen_dev]
	latih = [d for d in data if kunci(d) >= persen_dev]
	if not dev and len(latih) >= 2:                      # data sangat sedikit: ambil satu kalimat unik sebagai dev
		pilih = sorted({normalisasi(d['text']) for d in latih})[0]
		dev = [d for d in latih if normalisasi(d['text']) == pilih]
		latih = [d for d in latih if normalisasi(d['text']) != pilih]
	return latih, dev


def ringkas(data):
	n = len(data)
	unik = len({normalisasi(d['text']) for d in data})
	return f'{n} rekaman, {unik} kalimat berbeda'


# ====================================================================== bagian pelatihan (butuh PyTorch + transformers)
def muat_audio(jalur):
	import numpy as np
	import soundfile as sf
	suara, sr = sf.read(jalur, dtype='float32', always_2d=False)
	if suara.ndim > 1:
		suara = suara.mean(axis=1)
	if sr != SR:
		raise ValueError(f'{jalur}: harus {SR} Hz (hasil export_suara). Dapat {sr} Hz.')
	return np.asarray(suara[: int(SR * MAKS_DETIK)], dtype='float32')


def jalankan(args):
	import torch
	from transformers import (Seq2SeqTrainer, Seq2SeqTrainingArguments, WhisperForConditionalGeneration, WhisperProcessor)

	data, lewat = baca_manifest(args.data)
	print(f'Dibaca: {ringkas(data)} (dilewati: {lewat})')
	if len(data) < args.minimal and not args.paksa:
		raise SystemExit(f'Hanya {len(data)} rekaman (< {args.minimal}). Kumpulkan lebih banyak, atau pakai --paksa HANYA untuk uji alur.')
	latih, dev = bagi(data, args.persen_dev)
	if not latih or not dev:
		raise SystemExit('Data terlalu sedikit untuk dibagi latih/dev. Tambah data.')
	print(f'Latih: {ringkas(latih)}  |  Dev: {ringkas(dev)}')
	if len(data) < 2000:
		print('PERINGATAN: data masih sedikit; hasil belum bisa dipakai pengguna. Ini baik untuk uji alur / bukti konsep.', file=sys.stderr)

	random.seed(13); torch.manual_seed(13)
	processor = WhisperProcessor.from_pretrained(args.model)
	tok = processor.tokenizer
	# Whisper tidak punya token bahasa Tetun. Pakai token bahasa terdekat (bawaan: portuguese) atau tanpa token bahasa.
	if args.bahasa_token != 'tanpa':
		tok.set_prefix_tokens(language=args.bahasa_token, task='transcribe')
	else:
		tok.set_prefix_tokens(task='transcribe')

	class Set(torch.utils.data.Dataset):
		def __init__(self, daftar):
			self.d = daftar

		def __len__(self):
			return len(self.d)

		def __getitem__(self, i):
			x = self.d[i]
			fitur = processor.feature_extractor(muat_audio(x['audio']), sampling_rate=SR).input_features[0]
			return {'input_features': fitur, 'labels': tok(x['text']).input_ids}

	class Kolator:
		def __call__(self, batch):
			fitur = processor.feature_extractor.pad([{'input_features': b['input_features']} for b in batch], return_tensors='pt')
			label = tok.pad([{'input_ids': b['labels']} for b in batch], return_tensors='pt')
			ids = label['input_ids'].masked_fill(label['attention_mask'].ne(1), -100)
			if (ids[:, 0] == token_awal).all().item():     # token awal ditambahkan lagi oleh model
				ids = ids[:, 1:]
			fitur['labels'] = ids
			return fitur

	model = WhisperForConditionalGeneration.from_pretrained(args.model)
	token_awal = model.config.decoder_start_token_id
	model.generation_config.language = None if args.bahasa_token == 'tanpa' else args.bahasa_token
	model.generation_config.task = 'transcribe'
	model.generation_config.forced_decoder_ids = None
	model.config.forced_decoder_ids = None
	model.config.use_cache = False
	if args.lora:
		from peft import LoraConfig, get_peft_model
		model.enable_input_require_grads()
		model = get_peft_model(model, LoraConfig(r=32, lora_alpha=64, target_modules=['q_proj', 'v_proj'], lora_dropout=0.05, bias='none'))
		model.print_trainable_parameters()

	def metrik(pred):
		ids = pred.predictions
		ids = ids[0] if isinstance(ids, tuple) else ids
		label = pred.label_ids.copy()
		label[label == -100] = tok.pad_token_id
		return {'wer': wer(tok.batch_decode(label, skip_special_tokens=True), tok.batch_decode(ids, skip_special_tokens=True))}

	gpu = torch.cuda.is_available()
	import dataclasses
	nama_sah = {f.name for f in dataclasses.fields(Seq2SeqTrainingArguments)}
	kw = dict(
		output_dir=args.out, per_device_train_batch_size=args.batch, per_device_eval_batch_size=args.batch,
		gradient_accumulation_steps=max(1, 16 // args.batch), learning_rate=args.lr,
		num_train_epochs=args.epochs, max_steps=args.max_steps if args.max_steps else -1,
		fp16=gpu, gradient_checkpointing=gpu and not args.lora, save_strategy='epoch',
		predict_with_generate=True, generation_max_length=225, logging_steps=10, save_total_limit=2,
		load_best_model_at_end=True, metric_for_best_model='wer', greater_is_better=False,
		report_to='none', remove_unused_columns=False, label_names=['labels'], dataloader_num_workers=2 if gpu else 0)
	# Nama argumen berbeda antar versi transformers: pilih yang dikenal versi Anda
	kw['eval_strategy' if 'eval_strategy' in nama_sah else 'evaluation_strategy'] = 'epoch'
	if 'warmup_ratio' in nama_sah:
		kw['warmup_ratio'] = 0.1
	else:
		kw['warmup_steps'] = 0.1                       # versi baru: pecahan < 1 = rasio dari total langkah
	argumen = Seq2SeqTrainingArguments(**kw)
	trainer = Seq2SeqTrainer(model=model, args=argumen, train_dataset=Set(latih), eval_dataset=Set(dev),
	                         data_collator=Kolator(), compute_metrics=metrik)
	if args.baseline:
		print('WER dev SEBELUM latihan:', trainer.evaluate()['eval_wer'])
	trainer.train()
	hasil = trainer.evaluate()
	print(f"WER dev SETELAH latihan: {hasil['eval_wer']:.1f}%  (kalimat dev tidak ada di data latih, tapi penuturnya mungkin sama)")
	if args.lora:
		model = model.merge_and_unload()                  # gabungkan adapter agar bisa dikonversi untuk faster-whisper
	os.makedirs(args.out, exist_ok=True)
	model.save_pretrained(args.out)
	processor.save_pretrained(args.out)
	print(f'Model tersimpan di {args.out}\nKonversi untuk faster-whisper:\n'
	      f'  pip install ctranslate2 && ct2-transformers-converter --model {args.out} --output_dir {args.out}-ct2 --quantization float16 --copy_files tokenizer.json preprocessor_config.json')


def main():
	a = argparse.ArgumentParser(description='Fine-tune Whisper dengan data LAFEX (hasil export_suara).')
	a.add_argument('--data', required=True, help='folder berisi train.jsonl dan wavs/ (mis. data_suara/whisper)')
	a.add_argument('--out', required=True)
	a.add_argument('--model', default='openai/whisper-small', help='tiny/base/small/medium. T4 gratis: small (atau medium dengan --lora)')
	a.add_argument('--bahasa-token', default='portuguese', help="token bahasa Whisper terdekat (Tetun tidak ada). 'tanpa' = tanpa token bahasa")
	a.add_argument('--epochs', type=float, default=8)
	a.add_argument('--max-steps', type=int, default=0, help='untuk uji cepat, mis. 20')
	a.add_argument('--batch', type=int, default=8)
	a.add_argument('--lr', type=float, default=1e-5)
	a.add_argument('--persen-dev', type=int, default=10)
	a.add_argument('--lora', action='store_true')
	a.add_argument('--baseline', action='store_true', help='hitung WER model asli sebelum latihan')
	a.add_argument('--minimal', type=int, default=200, help='jumlah rekaman minimal agar mau jalan')
	a.add_argument('--paksa', action='store_true', help='abaikan --minimal (hanya uji alur)')
	jalankan(a.parse_args())


if __name__ == '__main__':
	main()
