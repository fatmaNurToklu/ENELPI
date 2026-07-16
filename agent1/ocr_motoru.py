# -*- coding: utf-8 -*-
"""
Agent 1 OCR motoru.
Bir evrak dosyasını (PDF veya görüntü) alır, kaynak tipine göre
doğru metin çıkarım yolunu seçer, temizler ve kontrat şemasındaki
metin_icerigi + agent1_islem_metadata alanlarını doldurur.

Dışarıdan çağrı arayüzü:
    sonuc = ocr_isle(kaynak_yolu, evrak_id)
    # sonuc: (temizlenmis_metin, ham_metin, metadata_guncelleme_dict)
"""
import json
import re
from pathlib import Path

import cv2
import numpy as np
import pytesseract
import pdfplumber

from on_isleme import on_isle
from temizleme import temizle

# Güven skoru eşiği — bu değerin altında manuel_inceleme_onerisi = True
GUVEN_ESIGI = 0.70
TESSERACT_DILI = "tur"
TESSERACT_CONFIG = "--psm 6"   # psm 6: tek tip metin bloğu (belgeler için optimal)


# ─── Yol 1: PDF metin katmanı ───────────────────────────────────────────────

def _pdf_metin_katmani_oku(pdf_yolu: Path) -> tuple[str, int]:
    """
    pdfplumber ile PDF'in gömülü metin katmanını çıkarır.
    Dönüş: (birleşik metin, sayfa sayısı)
    """
    sayfalar_metin = []
    with pdfplumber.open(str(pdf_yolu)) as pdf:
        sayfa_sayisi = len(pdf.pages)
        for i, sayfa in enumerate(pdf.pages, start=1):
            metin = sayfa.extract_text() or ""
            if sayfa_sayisi > 1 and metin.strip():
                metin = f"[SAYFA {i}]\n{metin}"
            sayfalar_metin.append(metin)
    return "\n\n".join(s for s in sayfalar_metin if s.strip()), sayfa_sayisi


def _pdf_metin_var_mi(pdf_yolu: Path, min_karakter: int = 20) -> bool:
    """PDF'de gerçek metin katmanı var mı? (taranmış PDF tuzağı)"""
    try:
        metin, _ = _pdf_metin_katmani_oku(pdf_yolu)
        return len(metin.strip()) >= min_karakter
    except Exception:
        return False


# ─── Yol 2: OCR (görüntü) ───────────────────────────────────────────────────

def _guven_skoru_hesapla(data: dict) -> float:
    """
    pytesseract.image_to_data çıktısından ağırlıklı güven skoru hesaplar.
    Kısa/tek karakterli kelimeleri daha az ağırlıklandırır.
    """
    kelimeler = [
        (str(w), int(c))
        for w, c in zip(data["text"], data["conf"])
        if int(c) >= 0 and str(w).strip()
    ]
    if not kelimeler:
        return 0.0
    # uzunluk ağırlıklı ortalama
    toplam_agirlik = sum(len(w) for w, _ in kelimeler)
    toplam_skor = sum(len(w) * c for w, c in kelimeler)
    return round(toplam_skor / toplam_agirlik / 100.0, 4) if toplam_agirlik > 0 else 0.0


def _goruntu_ocr(goruntu_yolu: Path, debug: bool = False) -> tuple[str, float, dict]:
    """
    Görüntü dosyasını ön işlemden geçirip Tesseract ile okur.
    Dönüş: (ham_metin, guven_skoru, on_isleme_meta)
    """
    islenm_arr, on_isleme_meta = on_isle(goruntu_yolu, debug_kaydet=debug)
    pil_img = __import__("PIL.Image", fromlist=["Image"]).fromarray(islenm_arr)

    data = pytesseract.image_to_data(
        pil_img, lang=TESSERACT_DILI,
        config=TESSERACT_CONFIG,
        output_type=pytesseract.Output.DICT
    )
    ham_metin = "\n".join(
        " ".join(
            str(data["text"][j])
            for j in range(len(data["text"]))
            if data["block_num"][j] == blok and str(data["text"][j]).strip()
        )
        for blok in sorted(set(data["block_num"]))
    ).strip()

    guven = _guven_skoru_hesapla(data)
    on_isleme_meta["ocr_motoru"] = f"Tesseract {pytesseract.get_tesseract_version()}"
    return ham_metin, guven, on_isleme_meta


# ─── Birleşik giriş noktası ─────────────────────────────────────────────────

def ocr_isle(kaynak_yolu: str | Path, evrak_id: str,
             debug: bool = False) -> tuple[str, str | None, dict]:
    """
    Ana fonksiyon. Kaynak tipini otomatik belirler ve uygun yolu çalıştırır.

    Dönüş:
      temizlenmis_metin  : str
      ham_metin          : str | None (yalnızca OCR yolunda dolu)
      meta_guncelleme    : dict  (agent1_islem_metadata'ya merge edilecek alanlar)
    """
    yol = Path(kaynak_yolu)
    uzanti = yol.suffix.lower()

    # ── PDF yolu ──
    if uzanti == ".pdf":
        if _pdf_metin_var_mi(yol):
            metin, sayfa_sayisi = _pdf_metin_katmani_oku(yol)
            temiz = temizle(metin)
            return temiz, None, {
                "kaynak_tipi": "PDF_METIN_KATMANI",
                "sayfa_sayisi": sayfa_sayisi,
                "ocr_motoru": None,
                "ocr_guven_skoru": None,
                "durum": "BASARILI" if temiz else "BASARISIZ",
                "manuel_inceleme_onerisi": not bool(temiz),
            }
        else:
            # PDF'i görüntüye çevirip OCR'a düşür (taranmış PDF)
            from pdf2image import convert_from_path
            sayfalar = convert_from_path(str(yol), dpi=150)
            parcalar = []
            toplam_guven = []
            on_isleme_meta = {}
            for i, pil_sayfa in enumerate(sayfalar, start=1):
                gecici = yol.parent / f"_gecici_{evrak_id}_s{i}.jpg"
                pil_sayfa.save(str(gecici), "JPEG", quality=85)
                ham, guven, meta = _goruntu_ocr(gecici, debug=debug)
                gecici.unlink(missing_ok=True)
                parcalar.append(f"[SAYFA {i}]\n{ham}" if len(sayfalar) > 1 else ham)
                toplam_guven.append(guven)
                on_isleme_meta = meta
            ham_metin = "\n\n".join(parcalar)
            ort_guven = round(sum(toplam_guven) / len(toplam_guven), 4)
            temiz = temizle(ham_metin)
            durum = "BASARILI" if ort_guven >= GUVEN_ESIGI else (
                "KISMI_BASARILI" if temiz else "BASARISIZ"
            )
            return temiz, ham_metin, {
                "kaynak_tipi": "TARANMIS_GORUNTU",
                "sayfa_sayisi": len(sayfalar),
                **on_isleme_meta,
                "ocr_guven_skoru": ort_guven,
                "durum": durum,
                "manuel_inceleme_onerisi": ort_guven < GUVEN_ESIGI,
            }

    # ── Görüntü yolu (jpg/png) ──
    elif uzanti in {".jpg", ".jpeg", ".png", ".tiff", ".bmp"}:
        ham_metin, guven, on_isleme_meta = _goruntu_ocr(yol, debug=debug)
        temiz = temizle(ham_metin)
        durum = "BASARILI" if guven >= GUVEN_ESIGI else (
            "KISMI_BASARILI" if temiz else "BASARISIZ"
        )
        return temiz, ham_metin, {
            "kaynak_tipi": "TARANMIS_GORUNTU",
            "sayfa_sayisi": 1,
            **on_isleme_meta,
            "ocr_guven_skoru": guven,
            "durum": durum,
            "manuel_inceleme_onerisi": guven < GUVEN_ESIGI,
        }

    # ── Düz metin yolu ──
    elif uzanti in {".txt"}:
        metin = yol.read_text(encoding="utf-8")
        temiz = temizle(metin)
        return temiz, None, {
            "kaynak_tipi": "DIJITAL_METIN",
            "sayfa_sayisi": 1,
            "ocr_motoru": None,
            "ocr_guven_skoru": None,
            "durum": "BASARILI",
            "manuel_inceleme_onerisi": False,
        }

    else:
        raise ValueError(f"Desteklenmeyen dosya uzantısı: {uzanti}")
