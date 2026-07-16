# -*- coding: utf-8 -*-
"""
Uçtan uca veri seti üretim scripti.
Çalıştırma: python3 olustur_veri_seti.py [--adet N] [--seed S] [--taranmis-oran 0.4]

Çıktılar:
  cikti/pdf/EVR-2026-XXXX.pdf          -> her evrak için temiz PDF
  cikti/gorsel/EVR-2026-XXXX.png       -> sadece "taranmış" olarak işaretlenenler
  cikti/json/EVR-2026-XXXX.json        -> ground truth (Agent 1 kontrat şeması)
  cikti/veri_seti_ozet.json            -> tüm kayıtların tek dosyada listesi + istatistik
"""
import argparse
import json
from pathlib import Path

from uretici import veri_seti_uret
from render import metni_pdfe_yaz, pdf_to_taranmis_gorsel

BASE = Path(__file__).parent
PDF_DIR = BASE / "cikti" / "pdf"
GORSEL_DIR = BASE / "cikti" / "gorsel"
JSON_DIR = BASE / "cikti" / "json"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--adet", type=int, default=15, help="Her evrak türü için kaç adet üretilecek")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--eksik-oran", type=float, default=0.35, help="Zorunlu alanların kasıtlı eksik bırakılma olasılığı")
    parser.add_argument("--taranmis-oran", type=float, default=0.4, help="Evrakların ne kadarının 'taranmış görüntü' olarak simüle edileceği")
    args = parser.parse_args()

    for d in (PDF_DIR, GORSEL_DIR, JSON_DIR):
        d.mkdir(parents=True, exist_ok=True)

    kayitlar = veri_seti_uret(her_tur_icin_adet=args.adet, eksik_alan_olasiligi=args.eksik_oran, seed=args.seed)

    import random as _r
    _r.seed(args.seed + 1)  # taranmış/temiz ayrımı için ayrı bir akış

    ozet = []
    tur_dagilimi = {}
    taranmis_sayisi = 0

    for kayit in kayitlar:
        gt = kayit["ground_truth"]
        evrak_id = gt["agent1_islem_metadata"]["evrak_id"]
        metin = kayit["dolu_metin"]
        tur = gt["siniflandirma_sonucu"]["evrak_turu"]
        tur_dagilimi[tur] = tur_dagilimi.get(tur, 0) + 1

        pdf_yolu = PDF_DIR / f"{evrak_id}.pdf"
        metni_pdfe_yaz(metin, pdf_yolu)

        taranmis_mi = _r.random() < args.taranmis_oran
        if taranmis_mi:
            taranmis_sayisi += 1
            gecici_yol = GORSEL_DIR / f"{evrak_id}.jpg"  # render içinde .jpg olarak kaydedilir
            bozulma_parametreleri = pdf_to_taranmis_gorsel(pdf_yolu, gecici_yol)
            gt["agent1_islem_metadata"]["kaynak_tipi"] = "TARANMIS_GORUNTU"
            # Gerçek OCR çalışmadığı için bu alanlar burada doldurulmaz;
            # Agent 1'in OCR adımı bu görüntüyü okuyup KENDİ ocr_guven_skoru'nu üretecek.
            # Ground truth'ta sadece üretim sırasında uygulanan bozulma parametreleri tutulur.
            gt["_meta_taranmis_bozulma_parametreleri"] = bozulma_parametreleri
            kaynak_dosya = bozulma_parametreleri["dosya_yolu"]
        else:
            gt["agent1_islem_metadata"]["kaynak_tipi"] = "PDF_METIN_KATMANI"
            kaynak_dosya = str(pdf_yolu.relative_to(BASE))

        gt["_meta_kaynak_dosya"] = kaynak_dosya

        json_yolu = JSON_DIR / f"{evrak_id}.json"
        with open(json_yolu, "w", encoding="utf-8") as f:
            json.dump(gt, f, ensure_ascii=False, indent=2)

        ozet.append(gt)

    with open(BASE / "cikti" / "veri_seti_ozet.json", "w", encoding="utf-8") as f:
        json.dump({
            "toplam_evrak": len(kayitlar),
            "tur_dagilimi": tur_dagilimi,
            "taranmis_goruntu_sayisi": taranmis_sayisi,
            "pdf_metin_katmani_sayisi": len(kayitlar) - taranmis_sayisi,
            "uretim_parametreleri": vars(args),
            "kayitlar": ozet,
        }, f, ensure_ascii=False, indent=2)

    print(f"Toplam {len(kayitlar)} evrak üretildi.")
    print(f"Tür dağılımı: {tur_dagilimi}")
    print(f"Taranmış görüntü (OCR testi için): {taranmis_sayisi}")
    print(f"PDF metin katmanı (doğrudan okunabilir): {len(kayitlar) - taranmis_sayisi}")
    print(f"Çıktılar: {PDF_DIR}, {GORSEL_DIR}, {JSON_DIR}")


if __name__ == "__main__":
    main()
