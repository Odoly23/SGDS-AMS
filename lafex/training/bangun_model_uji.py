"""Bangun model Whisper MINI ACAK + tokenizer + processor lokal (tanpa unduhan), dan data uji sintetis."""
import json, math, os, struct, sys, wave
import numpy as np
from tokenizers import Tokenizer, models, trainers, pre_tokenizers, decoders
from transformers import (GenerationConfig, WhisperConfig, WhisperFeatureExtractor, WhisperForConditionalGeneration, WhisperProcessor, WhisperTokenizerFast)
from transformers.models.whisper.tokenization_whisper import LANGUAGES

d = sys.argv[1]; os.makedirs(d, exist_ok=True)
kata = ["bondia ha'u naran ana", "obrigadu barak", "ita diak ka lae", "ha'u hakarak sosa modo", "fraze ida ne'e", "mai ita aprende hamutuk"] * 20
tk = Tokenizer(models.BPE()); tk.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False); tk.decoder = decoders.ByteLevel()
spesial = ["<|endoftext|>", "<|startoftranscript|>"] + [f"<|{l}|>" for l in LANGUAGES] + ["<|translate|>", "<|transcribe|>", "<|startoflm|>", "<|startofprev|>", "<|nocaptions|>", "<|notimestamps|>"]
tk.train_from_iterator(kata, trainers.BpeTrainer(vocab_size=500, special_tokens=spesial, initial_alphabet=pre_tokenizers.ByteLevel.alphabet()))
tk.save(os.path.join(d, 'tokenizer.json'))
tok = WhisperTokenizerFast(tokenizer_file=os.path.join(d, 'tokenizer.json'), unk_token="<|endoftext|>", bos_token="<|endoftext|>", eos_token="<|endoftext|>", pad_token="<|endoftext|>")
tok.add_special_tokens({'additional_special_tokens': spesial[1:]})
WhisperProcessor(feature_extractor=WhisperFeatureExtractor(), tokenizer=tok).save_pretrained(d)
ids = tok.convert_tokens_to_ids
cfg = WhisperConfig(vocab_size=len(tok), d_model=32, encoder_layers=1, decoder_layers=1, encoder_attention_heads=2, decoder_attention_heads=2, encoder_ffn_dim=64, decoder_ffn_dim=64,
                    num_mel_bins=80, max_source_positions=1500, max_target_positions=64, decoder_start_token_id=ids("<|startoftranscript|>"), pad_token_id=ids("<|endoftext|>"),
                    bos_token_id=ids("<|endoftext|>"), eos_token_id=ids("<|endoftext|>"), suppress_tokens=[], begin_suppress_tokens=[])
m = WhisperForConditionalGeneration(cfg)
m.generation_config = GenerationConfig(decoder_start_token_id=cfg.decoder_start_token_id, eos_token_id=cfg.eos_token_id, pad_token_id=cfg.pad_token_id, max_length=40,
    lang_to_id={f"<|{l}|>": ids(f"<|{l}|>") for l in LANGUAGES}, task_to_id={"transcribe": ids("<|transcribe|>"), "translate": ids("<|translate|>")},
    is_multilingual=True, no_timestamps_token_id=ids("<|notimestamps|>"))
m.save_pretrained(d)
# data uji
data = os.path.join(d, 'data'); os.makedirs(os.path.join(data, 'wavs'), exist_ok=True)
with open(os.path.join(data, 'train.jsonl'), 'w', encoding='utf-8') as f:
    for i in range(24):
        teks = ["Bondia, ha'u naran Ana.", "Obrigadu barak!", "Ita diak ka lae?", "Ha'u hakarak sosa modo.", "Fraze ida ne'e.", "Mai ita aprende hamutuk."][i % 6]
        x = (np.sin(2 * math.pi * (200 + 40 * (i % 6)) * np.arange(16000) / 16000) * 12000).astype('<i2')
        with wave.open(os.path.join(data, 'wavs', f'r{i}.wav'), 'wb') as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000); w.writeframes(x.tobytes())
        f.write(json.dumps({'audio': f'wavs/r{i}.wav', 'text': teks, 'bahasa': 'fataluku'}) + '\n')
print('siap', d)
