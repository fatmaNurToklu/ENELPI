# -*- coding: utf-8 -*-
"""
Üretilen veri setini veri sözleşmesi açısından doğrular.
Çıktı: tür dağılımı, eksik alan istatistikleri, kaynak tipi dağılımı.
"""
import json
from pathlib import Path
from collections import defaultdict

JSON_DIR = Path(__file__).parent / "cikti" / "json"
ZORUNLU_ALANLAR = {
    "DILEKCE": ["gonderici", "tc_kimlik", "konu", "tarih"],
    "BILGI_EDINME_BASVURUSU": ["gonderici", "tc_kimlik", "alici_kurum", "konu"],
    "SIKAYET_BASVURUSU": ["gonderici", "tc_kimlik", "konu"],
    "RESMI_UST_YAZI": ["gonderici", "alici_kurum", "belge_sayisi", "konu", "tarih", "imza_sahibi"],
    "CEVAP_YAZISI": ["gonderici", "alici_kurum", "belge_sayisi", "konu", "tarih"],
    "BILGILENDIRME_YAZISI": ["gonderici", "alici_kurum", "konu", "tarih"],
    "TALIMAT_YAZISI": ["gonderici", "alici_kurum", "konu", "tarih", "imza_sahibi"],
    "FATURA": ["gonderici", "tarih", "belge_sayisi"],
    "SOZLESME_PROTOKOL": ["gonderici", "alici_kurum", "tarih", "konu"],
    "TUTANAK_RAPOR": ["tarih", "konu"],
    "DIGER": [],
}

tur_sayac = defaultdict(int)
kaynak_sayac = defaultdict(int)
eksik_alan_sayac = defaultdict(int)   # hangi alan kaç kez eksik
tam_eksiksiz = 0
en_az_bir_eksik = 0
sema_hatasi = []

dosyalar = sorted(JSON_DIR.glob("*.json"))
for f in dosyalar:
    veri = json.load(open(f, encoding="utf-8"))

    # Şema zorunlu alan kontrolü
    for ust_alan in ["sema_versiyonu", "agent1_islem_metadata", "siniflandirma_sonucu",
                     "metin_icerigi", "on_cikarimlar"]:
        if ust_alan not in veri:
            sema_hatasi.append((f.name, f"'{ust_alan}' eksik"))

    tur = veri["siniflandirma_sonucu"]["evrak_turu"]
    kaynak = veri["agent1_islem_metadata"]["kaynak_tipi"]
    tur_sayac[tur] += 1
    kaynak_sayac[kaynak] += 1

    # Eksik alan analizi (ground truth'taki _meta alanından)
    eksikler = veri.get("_meta_eksik_birakilan_alanlar", [])
    if eksikler:
        en_az_bir_eksik += 1
        for alan in eksikler:
            eksik_alan_sayac[alan] += 1
    else:
        tam_eksiksiz += 1

print("=" * 55)
print(f"TOPLAM EVRAK       : {len(dosyalar)}")
print(f"Şema hatası        : {len(sema_hatasi)} (hedef: 0)")
print()
print("── TÜR DAĞILIMI ──────────────────────────────────")
for tur, sayi in sorted(tur_sayac.items()):
    print(f"  {tur:<30} {sayi:>3}")
print()
print("── KAYNAK TİPİ ────────────────────────────────────")
for k, v in sorted(kaynak_sayac.items()):
    print(f"  {k:<30} {v:>3}")
print()
print("── EKSİK ALAN ANALİZİ (Agent 2 testi için) ────────")
print(f"  En az 1 zorunlu alan eksik  : {en_az_bir_eksik}")
print(f"  Tüm zorunlu alanlar tam     : {tam_eksiksiz}")
print(f"  Eksik alan dağılımı:")
for alan, sayi in sorted(eksik_alan_sayac.items(), key=lambda x: -x[1]):
    print(f"    {alan:<20} {sayi:>3} evrakta eksik")
print("=" * 55)
if sema_hatasi:
    print("HATALAR:", sema_hatasi)
else:
    print("Tüm kayıtlar veri sözleşmesi v1.0 şemasına uygun ✓")
