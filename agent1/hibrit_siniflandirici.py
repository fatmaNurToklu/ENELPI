# -*- coding: utf-8 -*-
"""
Hibrit sınıflandırıcı — Agent 1'in sınıflandırma katmanı.

Karar akışı:
  1. Kural tabanlı: güçlü desen eşleşmesi varsa → hızlı ve yüksek güvenle döner
  2. ML yedek: kural net sonuç üretemezse → TF-IDF + SGD olasılıkları
  3. Kontrat §güven eşiği: siniflandirma_guven_skoru < 0.70 → manuel_inceleme_onerisi

Dışarıya açık tek fonksiyon: siniflandir(metin) → siniflandirma_sonucu_dict
"""
from kural_siniflandirici import kural_siniflandir
from ml_siniflandirici import tahmin_et as ml_tahmin

# Kontrat §5'teki güven eşiğiyle aynı
SINIFLANDIRMA_GUVEN_ESIGI = 0.70

# Kural tabanlının ML'e "devretmesi" için gereken minimum güven
KURAL_DEVIR_ESIGI = 0.75


def siniflandir(metin: str) -> dict:
    """
    Metni sınıflandırır. Dönüş, agent1_agent2_veri_sozlesmesi.md §2
    şemasındaki siniflandirma_sonucu bloğuyla doğrudan birleştirilebilir.

    {
        "evrak_turu": str,
        "alt_kategori": str | None,
        "siniflandirma_guven_skoru": float,
        "alternatif_tahminler": [...],
        "_siniflandirma_yontemi": "KURAL" | "ML" | "KURAL+ML_DOGRULAMA"
    }
    """
    # ── Adım 1: Kural tabanlı ──────────────────────────────────────────────
    kural_tur, kural_guven, kural_eslesmeleri = kural_siniflandir(metin)

    if kural_tur and kural_guven >= KURAL_DEVIR_ESIGI:
        # Kural güçlü: ML ile doğrula ama kurala öncelik ver
        ml_tur, ml_guven, ml_alternatifler = ml_tahmin(metin)

        yontem = "KURAL"
        if ml_tur == kural_tur:
            # İkisi de aynı fikir → güveni hafifçe yükselt
            final_guven = min(0.99, (kural_guven + ml_guven) / 2 + 0.05)
            yontem = "KURAL+ML_DOGRULAMA"
        else:
            # Anlaşmazlık → kural kazanır ama güveni indirgenmiş tut
            final_guven = kural_guven * 0.90
            ml_alternatifler = [{"tur": ml_tur, "skor": ml_guven}] + ml_alternatifler

        return {
            "evrak_turu": kural_tur,
            "alt_kategori": _alt_kategori(kural_tur),
            "siniflandirma_guven_skoru": round(final_guven, 4),
            "alternatif_tahminler": [
                a for a in ml_alternatifler if a["tur"] != kural_tur
            ][:2],
            "_siniflandirma_yontemi": yontem,
        }

    # ── Adım 2: ML yedek yol ───────────────────────────────────────────────
    ml_tur, ml_guven, ml_alternatifler = ml_tahmin(metin)

    # Kural zayıf ama bir ipucu verdiyse ve ML farklıysa alternatife ekle
    if kural_tur and kural_tur != ml_tur:
        ml_alternatifler = [{"tur": kural_tur, "skor": round(kural_guven, 4)}] + ml_alternatifler

    return {
        "evrak_turu": ml_tur,
        "alt_kategori": _alt_kategori(ml_tur),
        "siniflandirma_guven_skoru": round(ml_guven, 4),
        "alternatif_tahminler": ml_alternatifler[:2],
        "_siniflandirma_yontemi": "ML",
    }


def _alt_kategori(tur: str) -> str | None:
    """Evrak türünden alt kategoriyi türetir (kontrat §2 şemasına göre)."""
    VATANDAS = {"DILEKCE", "BILGI_EDINME_BASVURUSU", "SIKAYET_BASVURUSU"}
    KURUM_ICI = {"RESMI_UST_YAZI", "CEVAP_YAZISI", "BILGILENDIRME_YAZISI", "TALIMAT_YAZISI"}
    if tur in VATANDAS:
        return "VATANDAS_TALEBI"
    if tur in KURUM_ICI:
        return "KURUM_ICI_YAZISMA"
    return None


if __name__ == "__main__":
    # Hızlı manuel test
    ornekler = [
        ("FATURA", "FATURA\nFatura No: 12345\nGenel Toplam: 5.000 TL"),
        ("BILGI_EDINME", "4982 sayılı Bilgi Edinme Hakkı Kanunu kapsamında tarafıma bilgi verilmesini arz ederim."),
        ("TUTANAK", "TUTANAK\nTarih: 15.06.2026\nTaraflarca okunarak imza altına alınmıştır."),
        ("BELIRSIZ", "Merhaba, bir şeyler sormak istiyorum."),
    ]
    for ad, metin in ornekler:
        sonuc = siniflandir(metin)
        print(f"[{ad}] → {sonuc['evrak_turu']} "
              f"(güven: {sonuc['siniflandirma_guven_skoru']:.3f}, "
              f"yöntem: {sonuc['_siniflandirma_yontemi']})")
