# -*- coding: utf-8 -*-
"""
OCR ön işleme modülü.
Ham görüntüyü Tesseract'a girmeden önce kalitesini artıran adımları uygular.
Sadece TARANMIS_GORUNTU kayıt tipinde çalışır; PDF_METIN_KATMANI için atlanır.
"""
import cv2
import numpy as np
from PIL import Image
from pathlib import Path


def _gri_donustur(img_bgr: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)


def _adaptif_esikleme(gri: np.ndarray) -> np.ndarray:
    """
    Adaptif eşikleme: yerel parlaklık farklarına dayanır.
    Taranmış belgelerdeki gölge/leke etkisini bastırır.
    Gaussian yöntemi + ince blok boyutu (31) Türkçe karakter
    detaylarını (ş, ğ, ı, ç, ö, ü) daha iyi ayırt eder.
    """
    return cv2.adaptiveThreshold(
        gri, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        blockSize=31, C=10
    )


def _gurultu_gider(ikili: np.ndarray) -> np.ndarray:
    """Morfolojik açma + kapama ile tuz-biber gürültüsünü temizler."""
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    acma = cv2.morphologyEx(ikili, cv2.MORPH_OPEN, kernel)
    kapama = cv2.morphologyEx(acma, cv2.MORPH_CLOSE, kernel)
    return kapama


def _egiklik_duzelt(ikili: np.ndarray) -> tuple[np.ndarray, float]:
    """
    Hough dönüşümü ile sayfanın eğiklik açısını tahmin edip düzeltir.
    Döndürme sonrası kenar piksellerini beyaz (arka plan) ile doldurur.
    """
    kenarlar = cv2.Canny(ikili, 50, 150, apertureSize=3)
    cizgiler = cv2.HoughLinesP(kenarlar, 1, np.pi / 180,
                                threshold=80, minLineLength=100, maxLineGap=10)
    if cizgiler is None:
        return ikili, 0.0

    acilar = []
    for cizgi in cizgiler:
        x1, y1, x2, y2 = cizgi[0]
        if x2 != x1:
            aci = np.degrees(np.arctan2(y2 - y1, x2 - x1))
            if abs(aci) < 20:     # yalnızca yatay çizgileri dikkate al
                acilar.append(aci)

    if not acilar:
        return ikili, 0.0

    medyan_aci = float(np.median(acilar))
    h, w = ikili.shape
    merkez = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(merkez, medyan_aci, 1.0)
    duzeltilmis = cv2.warpAffine(
        ikili, M, (w, h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=255
    )
    return duzeltilmis, round(medyan_aci, 2)


def on_isle(goruntu_yolu: Path, debug_kaydet: bool = False) -> tuple[np.ndarray, dict]:
    """
    Tam ön işleme zinciri. Dönüş:
      - işlenmiş numpy dizisi (Tesseract'a verilecek)
      - uygulanan adımların özet metadatası
    """
    img_bgr = cv2.imread(str(goruntu_yolu))
    if img_bgr is None:
        raise FileNotFoundError(f"Görüntü açılamadı: {goruntu_yolu}")

    gri = _gri_donustur(img_bgr)
    ikili = _adaptif_esikleme(gri)
    temiz = _gurultu_gider(ikili)
    duzeltilmis, tespit_edilen_aci = _egiklik_duzelt(temiz)

    meta = {
        "giris_boyutu": list(img_bgr.shape[:2]),  # [yükseklik, genişlik]
        "tespit_edilen_egiklik_aci": tespit_edilen_aci,
        "uygulanan_adimlar": ["gri_donusum", "adaptif_esikleme",
                              "gurultu_giderme", "egiklik_duzeltme"],
    }

    if debug_kaydet:
        hata_yolu = goruntu_yolu.parent / f"_debug_{goruntu_yolu.stem}.png"
        cv2.imwrite(str(hata_yolu), duzeltilmis)

    return duzeltilmis, meta
