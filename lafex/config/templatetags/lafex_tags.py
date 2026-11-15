"""
Template tag untuk teks 4 bahasa.

  {% load lafex_tags %}
  {% t "rekam" %}                         teks antarmuka dari lian/i18n.py
  {% t "kalimat_n" n=20 %}                dengan variabel
  {% ml level "judul" %}                  teks dari kolom judul_tet / judul_en / judul_pt / judul_id milik objek
  <button {% tattr "record" %}>           aria-label (untuk tombol yang hanya berisi ikon) ikut berganti bahasa
"""
import json

from django import template
from django.utils.html import escape, format_html
from django.utils.safestring import mark_safe

from config import i18n

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


@register.simple_tag
def pesan(teks):
    """
    Tampilkan pesan sistem / kesalahan form. Bila isinya adalah KUNCI teks (mis. 'err_login_fail')
    dirender dalam 4 bahasa; selain itu ditampilkan apa adanya (sudah di-escape).
    """
    teks = str(teks)
    if teks in i18n.TEKS:
        return _spans(i18n.TEKS[teks])
    return escape(teks)


@register.simple_tag
def tpl(kunci, **awal):
    """
    Teks 4 bahasa dengan tempat kosong yang diisi JavaScript, mis. "{n} suara untuk {lian}".
    Isi awal dari kwargs (dirender server); atribut data-tpl menyimpan templatnya untuk diisi ulang.
    """
    bagian = []
    for kode in i18n.KODE:
        templat = i18n.TEKS[kunci].get(kode) or i18n.TEKS[kunci]["tet"]
        isi = templat.format(**awal) if awal else templat
        bagian.append(format_html('<span class="tx" data-l="{}" data-tpl="{}">{}</span>', kode, templat, isi))
    return mark_safe("".join(bagian))
