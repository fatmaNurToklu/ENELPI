# -*- coding: utf-8 -*-
"""
OCR pipeline değerlendirme scripti.
Üretilen veri setinin görüntü dosyaları üzerinde OCR çalıştırır,
ground-truth metin ile karşılaştırır; CER ve WER raporlar.

Çalıştırma: python3 ocr_degerlendir.py [--max-evrak 30]
"""
import argparse
import json
from pathlib import Path
from collections import defaultdict

from ocr_motoru import ocr_isle

BASE = Path(__file__).parent
JSON_DIR = BASE / "cikti" / "json"

# ─── Hata metrikleri ────────────────────────────────────────────────────────

def _edit_mesafesi(a: str, b: str) -> int:
    """Levenshtein edit mesafesi — CER/WER için."""
    m, n = len(a), len(b)
    dp = list(range(n + 1))
    for i in range(1, m + 1):
        onceki, dp[0] = dp[0], i
        for j in range(1, n + 1):
            gecici = dp[j]
            dp[j] = onceki if a[i-1] == b[j-1] else 1 + min(onceki, dp[j], dp[j-1])
            onceki = gecici
    return dp[n]


def cer(tahmin: str, gercek: str) -> float:
    """Karakter Hata Oranı (Character Error Rate)."""
    if not gercek:
        return 0.0 if not tahmin else 1.0
    return round(_edit_mesafesi(tahmin, gercek) / len(gercek), 4)


def wer(tahmin: str, gercek: str) -> float:
    """Kelime Hata Oranı (Word Error Rate)."""
    t_k = tahmin.split()
    g_k = gercek.split()
    if not g_k:
        return 0.0 if not t_k else 1.0
    return round(_edit_mesafesi(t_k, g_k) / len(g_k), 4)


# ─── Ana değerlendirme ───────────────────────────────────────────────────────

def degerlendir(max_evrak: int = 50):
    dosyalar = sorted(JSON_DIR.glob("*.json"))[:max_evrak]
    sonuclar = []

    tur_cer = defaultdict(list)
    tur_wer = defaultdict(list)
    kaynak_cer = defaultdict(list)
    basarisiz = []

    print(f"{'Evrak ID':<18} {'Tür':<28} {'Kaynak':<22} {'Güven':>6}  {'CER':>6}  {'WER':>6}  Durum")
    print("-" * 100)

    for json_dosya in dosyalar:
        gt = json.load(open(json_dosya, encoding="utf-8"))
        evrak_id = gt["agent1_islem_metadata"]["evrak_id"]
        kaynak_tipi = gt["agent1_islem_metadata"]["kaynak_tipi"]
        tur = gt["siniflandirma_sonucu"]["evrak_turu"]
        gercek_metin = gt["metin_icerigi"]["temizlenmis_metin"]
        kaynak_dosya = gt.get("_meta_kaynak_dosya", "")

        tam_yol = BASE / kaynak_dosya if kaynak_dosya else None

        if not tam_yol or not tam_yol.exists():
            basarisiz.append((evrak_id, "dosya bulunamadı"))
            continue

        try:
            tahmin_metin, _, meta = ocr_isle(tam_yol, evrak_id)
        except Exception as e:
            basarisiz.append((evrak_id, str(e)))
            continue

        guven = meta.get("ocr_guven_skoru") or 1.0
        c = cer(tahmin_metin, gercek_metin)
        w = wer(tahmin_metin, gercek_metin)
        durum = meta.get("durum", "?")
        manuel = "⚠ MANUEL" if meta.get("manuel_inceleme_onerisi") else ""

        tur_cer[tur].append(c)
        tur_wer[tur].append(w)
        kaynak_cer[kaynak_tipi].append(c)

        sonuclar.append({
            "evrak_id": evrak_id, "tur": tur, "kaynak_tipi": kaynak_tipi,
            "guven_skoru": guven, "cer": c, "wer": w, "durum": durum,
        })

        print(f"{evrak_id:<18} {tur:<28} {kaynak_tipi:<22} {guven:>6.3f}  {c:>6.3f}  {w:>6.3f}  {durum} {manuel}")

    print("\n" + "=" * 100)
    print("── TÜR BAZLI ORTALAMA CER ─────────────────────────────────────────────────")
    for tur, cerler in sorted(tur_cer.items(), key=lambda x: sum(x[1])/len(x[1])):
        ort = sum(cerler) / len(cerler)
        print(f"  {tur:<32} CER: {ort:.4f}  WER: {sum(tur_wer[tur])/len(tur_wer[tur]):.4f}  (n={len(cerler)})")

    print("\n── KAYNAK TİPİ BAZLI ORTALAMA CER ────────────────────────────────────────")
    for kaynak, cerler in sorted(kaynak_cer.items()):
        ort = sum(cerler) / len(cerler)
        print(f"  {kaynak:<30} CER: {ort:.4f}  (n={len(cerler)})")

    if sonuclar:
        tum_cer = [s["cer"] for s in sonuclar]
        tum_wer = [s["wer"] for s in sonuclar]
        print(f"\n── GENEL ──────────────────────────────────────────────────────────────────")
        print(f"  Değerlendirilen evrak : {len(sonuclar)}")
        print(f"  Ortalama CER          : {sum(tum_cer)/len(tum_cer):.4f}")
        print(f"  Ortalama WER          : {sum(tum_wer)/len(tum_wer):.4f}")
        print(f"  Mükemmel (CER=0)      : {sum(1 for c in tum_cer if c==0)}")
        print(f"  Manuel inceleme (>eşik): {sum(1 for s in sonuclar if s['guven_skoru'] < 0.70)}")

    if basarisiz:
        print(f"\n⚠  Atlanan: {basarisiz}")

    return sonuclar


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-evrak", type=int, default=50)
    args = parser.parse_args()
    degerlendir(max_evrak=args.max_evrak)
