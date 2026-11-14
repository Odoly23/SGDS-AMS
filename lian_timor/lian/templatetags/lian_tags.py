"""
Template tag untuk teks 4 bahasa.

  {% load lian_tags %}
  {% t "rekam" %}                         teks antarmuka dari lian/i18n.py
  {% t "kalimat_n" n=20 %}                dengan variabel
  {% ml level "judul" %}                  teks dari kolom judul_tet / judul_en / judul_pt / judul_id milik objek
  <button {% tattr "record" %}>           aria-label (untuk tombol yang hanya berisi ikon) ikut berganti bahasa
"""
import json

from django import template
from django.utils.html import escape, format_html
from django.utils.safestring import mark_safe

from lian import i18n

register = template.Library()


def _spans(teks_per_bahasa):
    bagian = []
    for kode in i18n.KODE:
        isi = teks_per_bahasa.get(kode) or teks_per_bahasa.get("tet", "")
        bagian.append(f'<span class="tx" data-l="{kode}">{escape(isi)}</span>')
    return mark_safe("".join(bagian))


@register.simple_tag
def t(kunci, **variabel):
    data = {k: v for k, v in i18n.TEKS[kunci].items()}
    if variabel:
        data = {k: v.format(**variabel) for k, v in data.items()}
    return _spans(data)


@register.simple_tag
def ml(obj, awalan):
    return _spans({kode: getattr(obj, f"{awalan}_{kode}", "") for kode in i18n.KODE})


@register.simple_tag
def tattr(kunci):
    data = i18n.TEKS[kunci]
    return format_html('aria-label="{}" data-aria="{}"', data["tet"], json.dumps(data, ensure_ascii=False))
