# -*- coding: utf-8 -*-
"""
Metin temizleme modülü.
OCR çıktısındaki gürültüleri (karakter karışıklıkları, fazla boşluklar,
anlamsız satırlar) temizler; temizlenmis_metin'e giden son metni üretir.
"""
import re
import unicodedata


# --- Türkçe karakter düzeltme tablosu ---
# Tesseract sık sık bu karakterleri karıştırır:
OCR_DUZELTME_TABLOSU = str.maketrans({
    "\u0131": "ı",   # zaten doğru — ama bazen yanlış kod noktasında gelebilir
    "\u0049": "İ",   # büyük I → bazen İ yerine gelir (bağlama göre — dikkatli kullan)
    # Yaygın yanlış tanımalar (Tesseract tur modeli)
    "0": "0",         # placeholder — gerekirse 'O'/'o' düzeltmesi eklenebilir
})

# Anlamsız/tamamen gürültü satırları için filtre deseni
GURULTU_SATIR_DESENI = re.compile(
    r"^[\s\-_=\|\.,:;!#\*\~\^\/\\]{3,}$"  # yalnızca çizgi/nokta/özel karakter içeren satır
)

# Birden fazla boşluğu tek boşluğa indir (ama satır sonlarına dokunma)
COK_BOSLUK = re.compile(r"[ \t]{2,}")

# Art arda 3'ten fazla boş satırı 2'ye indir
COK_BOSLUK_SATIR = re.compile(r"\n{3,}")


def _unicode_normalizasyon(metin: str) -> str:
    """NFC normalizasyonu: birleşik Türkçe karakterleri tek kod noktasına indirir."""
    return unicodedata.normalize("NFC", metin)


_OCR_ARTIFACT = re.compile(r"\bNone\b")   # Python None'un metin çıktısı

def _satir_temizle(metin: str) -> str:
    """Her satırı ayrı ayrı işler: gürültülü satırları sil, kenar boşluklarını kırp."""
    satirlar = metin.splitlines()
    temiz = []
    for satir in satirlar:
        satir = satir.strip()
        # OCR artifact: template'ten sızan "None" string'ini kaldır
        satir = _OCR_ARTIFACT.sub("", satir).strip()
        if GURULTU_SATIR_DESENI.match(satir):
            continue          # tamamen gürültü satırı → at
        if len(satir) == 1 and not satir.isalnum():
            continue          # tek özel karakter satırı → at
        if not satir:
            temiz.append("")  # boş satırı paragraf ayraç olarak koru
            continue
        temiz.append(satir)
    return "\n".join(temiz)


def _bosluk_normalize(metin: str) -> str:
    metin = COK_BOSLUK.sub(" ", metin)
    metin = COK_BOSLUK_SATIR.sub("\n\n", metin)
    return metin.strip()


def temizle(ham_metin: str) -> str:
    """
    Tam temizleme zinciri. Sıra önemli:
    1. Unicode normalizasyonu
    2. Satır bazlı gürültü filtreleme
    3. Boşluk normalizasyonu
    """
    if not ham_metin:
        return ""
    metin = _unicode_normalizasyon(ham_metin)
    metin = _satir_temizle(metin)
    metin = _bosluk_normalize(metin)
    return metin
