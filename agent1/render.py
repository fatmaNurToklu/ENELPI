# -*- coding: utf-8 -*-
"""
Render katmanı: dolu_metin -> PDF -> (opsiyonel) sahte-taranmış PNG.

İki çıktı modu:
  - "DIJITAL_METIN" / "PDF_METIN_KATMANI": temiz PDF, OCR'a gerek yok.
  - "TARANMIS_GORUNTU": PDF'ten görüntüye çevrilip hafif gürültü/eğiklik/
    kontrast bozulması eklenir; Agent 1'in OCR + güven skoru mantığını
    gerçekçi koşullarda test etmek için kullanılır.
"""
import random
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from pdf2image import convert_from_path
from PIL import Image, ImageFilter
import numpy as np

FONT_YOLU = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD_YOLU = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
pdfmetrics.registerFont(TTFont("DejaVuSans", FONT_YOLU))
pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", FONT_BOLD_YOLU))


def metni_pdfe_yaz(metin: str, cikti_yolu: Path, font_boyutu: int = 11):
    """Düz metni A4 sayfaya basit satır kaydırmalı şekilde yazar."""
    c = canvas.Canvas(str(cikti_yolu), pagesize=A4)
    genislik, yukseklik = A4
    sol_kenar = 25 * mm
    sag_kenar = genislik - 20 * mm
    ust_y = yukseklik - 25 * mm
    satir_araligi = font_boyutu * 1.4

    c.setFont("DejaVuSans", font_boyutu)
    y = ust_y
    max_genislik = sag_kenar - sol_kenar

    for paragraf in metin.split("\n"):
        if paragraf.strip() == "":
            y -= satir_araligi
            continue
        kelimeler = paragraf.split(" ")
        satir = ""
        for kelime in kelimeler:
            aday = (satir + " " + kelime).strip()
            if pdfmetrics.stringWidth(aday, "DejaVuSans", font_boyutu) <= max_genislik:
                satir = aday
            else:
                c.drawString(sol_kenar, y, satir)
                y -= satir_araligi
                satir = kelime
                if y < 20 * mm:
                    c.showPage()
                    c.setFont("DejaVuSans", font_boyutu)
                    y = ust_y
        if satir:
            c.drawString(sol_kenar, y, satir)
            y -= satir_araligi
        if y < 20 * mm:
            c.showPage()
            c.setFont("DejaVuSans", font_boyutu)
            y = ust_y

    c.save()


def _gurultu_ekle(img: Image.Image, yogunluk: float = 0.02) -> Image.Image:
    arr = np.array(img.convert("L")).astype(np.float32)
    gurultu = np.random.normal(0, 255 * yogunluk, arr.shape)
    arr = np.clip(arr + gurultu, 0, 255).astype(np.uint8)
    return Image.fromarray(arr).convert("RGB")


def _kontrast_boz(img: Image.Image, faktor: float = 0.85) -> Image.Image:
    arr = np.array(img.convert("L")).astype(np.float32)
    ortalama = arr.mean()
    arr = (arr - ortalama) * faktor + ortalama
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert("RGB")


def pdf_to_taranmis_gorsel(pdf_yolu: Path, cikti_png_yolu: Path,
                            egiklik_derece_araligi=(-2.5, 2.5),
                            gurultu_yogunlugu_araligi=(0.01, 0.05),
                            bulaniklik_olasiligi=0.3,
                            dpi: int = 150,
                            jpeg_kalitesi: int = 82) -> dict:
    """
    PDF'in ilk sayfasını görüntüye çevirir ve "taranmış belge" görünümü
    için gerçekçi bozulmalar ekler. Dönen dict, OCR aşamasında
    karşılaştırma için uygulanan bozulma parametrelerini taşır
    (debug / değerlendirme amaçlı; kontrat şemasının parçası değildir).
    Çıktı JPEG olarak kaydedilir (gerçek taranmış evraklar da genelde JPEG'dir
    ve gürültülü PNG dosya boyutunu gereksiz şişirir).
    """
    sayfalar = convert_from_path(str(pdf_yolu), dpi=dpi)
    img = sayfalar[0]

    egiklik = random.uniform(*egiklik_derece_araligi)
    img = img.rotate(egiklik, expand=True, fillcolor="white", resample=Image.BICUBIC)

    gurultu_yogunlugu = random.uniform(*gurultu_yogunlugu_araligi)
    img = _gurultu_ekle(img, yogunluk=gurultu_yogunlugu)

    kontrast_faktoru = random.uniform(0.75, 0.95)
    img = _kontrast_boz(img, faktor=kontrast_faktoru)

    bulanik = False
    if random.random() < bulaniklik_olasiligi:
        img = img.filter(ImageFilter.GaussianBlur(radius=random.uniform(0.4, 1.0)))
        bulanik = True

    cikti_jpg_yolu = cikti_png_yolu.with_suffix(".jpg")
    img.save(cikti_jpg_yolu, format="JPEG", quality=jpeg_kalitesi, optimize=True)

    return {
        "dosya_yolu": str(cikti_jpg_yolu),
        "egiklik_derece": round(egiklik, 2),
        "gurultu_yogunlugu": round(gurultu_yogunlugu, 3),
        "kontrast_faktoru": round(kontrast_faktoru, 2),
        "bulaniklik_uygulandi": bulanik,
    }
