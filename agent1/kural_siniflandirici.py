# -*- coding: utf-8 -*-
"""
Kural tabanlı hızlı sınıflandırıcı.

Her evrak türü için, metnin başında veya tamamında aranacak
ayırt edici desenler ve karşılık güven skorları tanımlanır.
Desen eşleşirse ML'e gerek kalmadan yüksek güvenle tahmin döner.

Tasarım ilkesi (veri sözleşmesi §1'den):
  "kural tabanlı kısımda net eşleşirse yüksek güvenle sınıflandır —
   ucuz ve hızlı; aksi halde ML yedek yola düş."
"""
import re
from dataclasses import dataclass, field


@dataclass
class _Kural:
    tur: str
    desenler: list[re.Pattern]
    guven: float          # eşleşirse verilecek güven skoru
    oncelik: int = 0      # düşük sayı = önce kontrol et


_KURALLAR: list[_Kural] = [
    # ── Fatura ──────────────────────────────────────────────────────────────
    _Kural(
        tur="FATURA",
        desenler=[
            re.compile(r"FATURA", re.I),
            re.compile(r"fatura\s*(no|numaras)", re.I),
        ],
        guven=0.95, oncelik=1,
    ),

    # ── Resmi üst yazı ──────────────────────────────────────────────────────
    # "Sayı: E-..." + "Konu:" ikilisi güçlü sinyal
    _Kural(
        tur="RESMI_UST_YAZI",
        desenler=[
            re.compile(r"Say[ıi]\s*:\s*E-\d+", re.I),
            re.compile(r"arz\s*/\s*rica\s+ederim", re.I),
        ],
        guven=0.92, oncelik=2,
    ),

    # ── Cevap yazısı ────────────────────────────────────────────────────────
    _Kural(
        tur="CEVAP_YAZISI",
        desenler=[
            re.compile(r"(ilgi|ilgi\s*[:\-])\s*.{5,60}(tarih|say[ıi])", re.I),
            re.compile(r"arz\s+ederim", re.I),
            re.compile(r"Konu\s*:.{3,60}[Hh]k\.", re.I),
        ],
        guven=0.85, oncelik=3,
    ),

    # ── Talimat yazısı ──────────────────────────────────────────────────────
    _Kural(
        tur="TALIMAT_YAZISI",
        desenler=[
            re.compile(r"(ivedilikle|acilen).{0,40}(yerine\s+getirilmesi|yap[ıi]lmas[ıi])", re.I),
            re.compile(r"gere[gğ]ini\s+rica\s+ederim", re.I),
        ],
        guven=0.88, oncelik=3,
    ),

    # ── Bilgilendirme yazısı ─────────────────────────────────────────────────
    _Kural(
        tur="BILGILENDIRME_YAZISI",
        desenler=[
            re.compile(r"bilgilerinize\s+sunulur", re.I),
            re.compile(r"bilgi\s+(amaçl[ıi]|için)\s+iletilmektedir", re.I),
        ],
        guven=0.88, oncelik=3,
    ),

    # ── Bilgi edinme başvurusu ───────────────────────────────────────────────
    _Kural(
        tur="BILGI_EDINME_BASVURUSU",
        desenler=[
            re.compile(r"4982\s*say[ıi]l[ıi]\s*bilgi\s+edinme", re.I),
            re.compile(r"bilgi\s+edinme\s*(hakk[ıi]\s*kanunu|talebi)", re.I),
        ],
        guven=0.95, oncelik=1,
    ),

    # ── Şikayet başvurusu ───────────────────────────────────────────────────
    _Kural(
        tur="SIKAYET_BASVURUSU",
        desenler=[
            re.compile(r"[sş]ikayet\s*(ba[sş]vurusu|etmek\s+istiyor)", re.I),
            re.compile(r"[sş]ikayetimi\s+(bildirmek|iletmek)", re.I),
        ],
        guven=0.90, oncelik=2,
    ),

    # ── Dilekçe ─────────────────────────────────────────────────────────────
    # En geniş vatandaş belgesi — diğerlerinden sonra kontrol et
    _Kural(
        tur="DILEKCE",
        desenler=[
            re.compile(r"gere[gğ]ini\s+sayg[ıi]lar[ıi]mla\s+arz\s+ederim", re.I),
            re.compile(r"ba[sş]kanl[ıiığ]+[ga]\s*$", re.I | re.MULTILINE),
        ],
        guven=0.82, oncelik=4,
    ),

    # ── Sözleşme / protokol ─────────────────────────────────────────────────
    _Kural(
        tur="SOZLESME_PROTOKOL",
        desenler=[
            re.compile(r"(i[sş]birli[gğ]i\s*protokol[üu]|hizmet\s+al[ıi]m\s+s[öo]zle[sş]mesi)", re.I),
            re.compile(r"taraf\s*1\s*[:.]", re.I),
            re.compile(r"imzalanm[ıi][sş]t[ıi]r", re.I),
        ],
        guven=0.90, oncelik=2,
    ),

    # ── Tutanak / rapor ─────────────────────────────────────────────────────
    _Kural(
        tur="TUTANAK_RAPOR",
        desenler=[
            re.compile(r"^TUTANAK\b", re.I | re.MULTILINE),
            re.compile(r"(teslim\s*-\s*tesell[üu]m|denetim\s+raporu)", re.I),
            re.compile(r"taraflarca\s+okunarak\s+imza", re.I),
        ],
        guven=0.92, oncelik=2,
    ),
]

# Önceliğe göre sırala (küçük sayı önce)
_KURALLAR.sort(key=lambda k: k.oncelik)


def kural_siniflandir(metin: str) -> tuple[str | None, float, list[dict]]:
    """
    Metni kural tabanlı olarak sınıflandırmayı dener.

    Dönüş:
      (evrak_turu | None, guven_skoru, eslesen_kurallar)
      - None: net eşleşme yok → ML'e düşmeli
    """
    eslesmeler: list[dict] = []

    for kural in _KURALLAR:
        eslesen_desenler = [d.pattern for d in kural.desenler if d.search(metin)]
        if len(eslesen_desenler) >= 2:
            # Birden fazla desen eşleşti → güçlü sinyal
            eslesmeler.append({
                "tur": kural.tur,
                "guven": kural.guven,
                "eslesen": eslesen_desenler,
                "guc": "CIFT",
            })
        elif len(eslesen_desenler) == 1 and kural.guven >= 0.90:
            # Tek desen ama çok ayırt edici (yüksek guven eşiği)
            eslesmeler.append({
                "tur": kural.tur,
                "guven": kural.guven * 0.85,   # tek eşleşmede güveni indir
                "eslesen": eslesen_desenler,
                "guc": "TEK_YUKSEK",
            })

    if not eslesmeler:
        return None, 0.0, []

    # En yüksek güvenli eşleşmeyi seç
    en_iyi = max(eslesmeler, key=lambda x: (x["guven"], x["guc"] == "CIFT"))
    return en_iyi["tur"], en_iyi["guven"], eslesmeler
