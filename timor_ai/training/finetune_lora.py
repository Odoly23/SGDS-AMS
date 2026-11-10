"""
Fine-tuning LoRA untuk Gemma 2 (2B / 9B) memakai data dari `export_finetune`.

Jalankan (butuh GPU NVIDIA 8GB+ untuk 2B; Colab/Kaggle gratis cukup):
  python manage.py export_finetune --out training/train.jsonl
  python training/finetune_lora.py --data training/train.jsonl --out training/output/lora-gemma2-2b

Lalu di .env:  LLM_BACKEND=hf   LLM_LORA_PATH=training/output/lora-gemma2-2b

Apa itu LoRA? Alih-alih melatih seluruh model (miliaran parameter), kita hanya melatih
"adapter" kecil (beberapa juta parameter). Jauh lebih murah dan file hasilnya hanya puluhan MB.

STATUS: script ini belum diuji pada GPU di lingkungan pembuatan; uji dulu dengan --max-steps 20.
"""
import argparse
import json
import os

import torch
from peft import LoraConfig, get_peft_model
from torch.utils.data import Dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    DataCollatorForSeq2Seq,
    Trainer,
    TrainingArguments,
)


class InstructionData(Dataset):
    """Mengubah baris JSONL menjadi token. Loss hanya dihitung pada bagian JAWABAN (label -100 untuk prompt)."""

    def __init__(self, path, tokenizer, max_len=384):
        self.items = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                row = json.loads(line)
                user = f"{row['instruction']}\n\n{row['input']}"
                prompt = tokenizer.apply_chat_template(
                    [{"role": "user", "content": user}], tokenize=False, add_generation_prompt=True
                )
                answer = row["output"] + "<end_of_turn>\n"
                p_ids = tokenizer(prompt, add_special_tokens=False)["input_ids"]
                a_ids = tokenizer(answer, add_special_tokens=False)["input_ids"]
                ids = (p_ids + a_ids)[:max_len]
                labels = ([-100] * len(p_ids) + a_ids)[:max_len]
                self.items.append({"input_ids": ids, "attention_mask": [1] * len(ids), "labels": labels})

    def __len__(self):
        return len(self.items)

    def __getitem__(self, i):
        return self.items[i]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="training/train.jsonl")
    ap.add_argument("--out", default="training/output/lora-gemma2-2b")
    ap.add_argument("--model", default="google/gemma-2-2b-it")
    ap.add_argument("--epochs", type=float, default=3)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--max-steps", type=int, default=-1, help="Untuk uji cepat, mis. 20")
    args = ap.parse_args()

    token = os.getenv("HF_TOKEN") or None
    tok = AutoTokenizer.from_pretrained(args.model, token=token)
    use_cuda = torch.cuda.is_available()
    model = AutoModelForCausalLM.from_pretrained(
        args.model, token=token, torch_dtype=torch.bfloat16 if use_cuda else torch.float32
    )
    lora = LoraConfig(
        r=16, lora_alpha=32, lora_dropout=0.05, task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    )
    model = get_peft_model(model, lora)
    model.print_trainable_parameters()

    train_ds = InstructionData(args.data, tok)
    if len(train_ds) == 0:
        raise SystemExit("Data kosong. Jalankan export_finetune dulu (atau pakai --include-draft untuk uji).")

    trainer = Trainer(
        model=model,
        train_dataset=train_ds,
        data_collator=DataCollatorForSeq2Seq(tok, padding=True, label_pad_token_id=-100),
        args=TrainingArguments(
            output_dir=args.out,
            num_train_epochs=args.epochs,
            max_steps=args.max_steps,
            per_device_train_batch_size=4,
            gradient_accumulation_steps=4,
            learning_rate=args.lr,
            logging_steps=10,
            save_strategy="no",
            bf16=use_cuda,
            report_to="none",
        ),
    )
    trainer.train()
    model.save_pretrained(args.out)   # hanya adapter LoRA (kecil)
    tok.save_pretrained(args.out)
    print("Adapter LoRA tersimpan di", args.out)


if __name__ == "__main__":
    main()
