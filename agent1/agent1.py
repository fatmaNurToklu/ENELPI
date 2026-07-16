# -*- coding: utf-8 -*-
"""
Agent 1 — ana giriş noktası.

Bir evrak dosyası alır, tüm pipeline'ı çalıştırır ve
agent1_agent2_veri_sozlesmesi.md v1.0 şemasına tam uyumlu
JSON çıktısı üretir.

Kullanım:
  python3 agent1.py --dosya cikti/pdf/EVR-2026-0001.pdf
  python3 agent1.py --dosya cikti/gorsel/EVR-2026-0008.jpg
"""
import argparse
import json
import re
import uuid
from datetime import datetime
from pathlib import Path

from ocr_motoru import ocr_isle
from hibrit_siniflandirici import siniflandir
from ml_siniflandirici import yukle as ml_yukle

GUVEN_ESIGI = 0.70            # kontrat §5 ile senkron
SINIFLANDIRMA_GUVEN_ESIGI = GUVEN_ESIGI


# ── Yapısal ön çıkarım (regex tabanlı) ────────────────────────────────────────

_TARIH_DESENI = re.compile(
    r"\b(\d{1,2})[./](\d{1,2})[./](\d{2,4})\b"
    r"|\b(\d{1,2})\s+"
    r"(Ocak|Şubat|Mart|Nisan|Mayıs|Haziran|Temmuz|Ağustos|Eylül|Ekim|Kasım|Aralık)"
    r"\s+(\d{4})\b",
    re.I
)
_AY_SAYISI = {
    "ocak": 1, "şubat": 2, "mart": 3, "nisan": 4, "mayıs": 5, "haziran": 6,
    "temmuz": 7, "ağustos": 8, "eylül": 9, "ekim": 10, "kasım": 11, "aralık": 12,
}
_BELGE_SAYISI_DESENI = re.compile(r"[Ss]ay[ıi]\s*:\s*(E-[\d\-\.]+)", re.I)
_TC_DESENI = re.compile(r"\b([1-9]\d{10})\b")
_KONU_DESENI = re.compile(r"[Kk]onu\s*:\s*([^\n\.]{3,120})")
_ALICI_DESENI = re.compile(r"^(.+?)\s*(BAŞKANLIĞINA|MÜDÜRLÜĞÜNE|MÜDÜRLÜĞܒNE|BAŞKANLIĞINA)\s*$",
                             re.MULTILINE | re.I)
_IMZA_DESENI = re.compile(
    r"(?:Daire Başkanı|Genel Müdür|Şube Müdürü|Koordinatör|Müdür)\s*\n\s*([A-ZÇĞİÖŞÜa-zçğıöşü\s]+)\n",
    re.I
)


def _tarih_coz(metin: str) -> str | None:
    eslesme = _TARIH_DESENI.search(metin)
    if not eslesme:
        return None
    g = eslesme.groups()
    if g[0]:   # sayısal format
        gun, ay, yil = int(g[0]), int(g[1]), int(g[2])
        yil = 2000 + yil if yil < 100 else yil
        try:
            return f"{yil:04d}-{ay:02d}-{gun:02d}"
        except ValueError:
            return None
    elif g[3]:  # yazılı ay formatı
        gun = int(g[3])
        ay = _AY_SAYISI.get(g[4].lower(), 0)
        yil = int(g[5])
        return f"{yil:04d}-{ay:02d}-{gun:02d}" if ay else None
    return None


def _tc_dogrula(numara: str) -> bool:
    """Basit TC kimlik algoritma doğrulaması."""
    if len(numara) != 11 or numara[0] == "0":
        return False
    d = [int(c) for c in numara]
    return (
        (d[0]+d[2]+d[4]+d[6]+d[8])*7 - (d[1]+d[3]+d[5]+d[7]) ) % 10 == d[9] \
        and sum(d[:10]) % 10 == d[10]


def yapisal_cikar(metin: str) -> dict:
    """Metin üzerinde yüzeysel regex tabanlı alan çıkarımı."""
    sonuc = {
        "gonderici": None, "alici_kurum": None, "konu": None,
        "tarih": None, "belge_sayisi": None, "tc_kimlik": None,
        "imza_sahibi": None, "ekler": None,
    }

    # Konu
    konu_m = _KONU_DESENI.search(metin)
    if konu_m:
        konu_tam = konu_m.group(1).strip()
        # İlk satır kırılmasında dur (tek satırlık konu alanı beklenir)
        konu_tek = konu_tam.splitlines()[0].strip()
        sonuc["konu"] = konu_tek[:120] if konu_tek else None

    # Alıcı kurum
    alici_m = _ALICI_DESENI.search(metin)
    if alici_m:
        sonuc["alici_kurum"] = alici_m.group(1).strip()

    # Belge sayısı
    belge_m = _BELGE_SAYISI_DESENI.search(metin)
    if belge_m:
        sonuc["belge_sayisi"] = belge_m.group(1).strip()

    # Tarih
    sonuc["tarih"] = _tarih_coz(metin)

    # TC Kimlik — sadece geçerli olanı al
    tc_adaylar = _TC_DESENI.findall(metin)
    for aday in tc_adaylar:
        if _tc_dogrula(aday):
            sonuc["tc_kimlik"] = aday
            break

    # Gönderici / imza sahibi — son 4 satırdan tahmin et
    son_satirlar = [s.strip() for s in metin.strip().splitlines()[-5:] if s.strip()]
    for satir in reversed(son_satirlar):
        if re.match(r"^[A-ZÇĞİÖŞÜ][a-zçğıöşü]+([\s\-][A-ZÇĞİÖŞÜa-zçğıöşü]+){1,4}$", satir):
            if not any(k in satir.lower() for k in ["başkanlığı", "müdürlüğü", "kurumu", "ajansı"]):
                sonuc["gonderici"] = satir
                break

    return sonuc


# ── Ana pipeline ──────────────────────────────────────────────────────────────

def agent1_isle(dosya_yolu: str | Path, evrak_id: str | None = None) -> dict:
    """
    Tam Agent 1 pipeline'ı. Dönüş: kontrat şeması v1.0 uyumlu dict.
    """
    yol = Path(dosya_yolu)
    if evrak_id is None:
        evrak_id = f"EVR-CANLI-{str(uuid.uuid4())[:8].upper()}"

    # 1. OCR / metin çıkarımı
    temizlenmis, ham, ocr_meta = ocr_isle(yol, evrak_id)

    # 2. Sınıflandırma (boş metin → doğrudan BASARISIZ)
    if not temizlenmis.strip():
        sinif = {
            "evrak_turu": "DIGER",
            "alt_kategori": None,
            "siniflandirma_guven_skoru": 0.0,
            "alternatif_tahminler": [],
            "_siniflandirma_yontemi": "ATLANDI_BOS_METIN",
        }
    else:
        sinif = siniflandir(temizlenmis)

    # 3. Yapısal ön çıkarım
    on_cikarimlar = yapisal_cikar(temizlenmis) if temizlenmis else {
        k: None for k in ["gonderici","alici_kurum","konu","tarih",
                           "belge_sayisi","tc_kimlik","imza_sahibi","ekler"]
    }

    # 4. Manuel inceleme kararı
    # OCR'dan veya sınıflandırmadan gelen düşük güven → manuel öner
    sinif_guven = sinif["siniflandirma_guven_skoru"]
    ocr_guven = ocr_meta.get("ocr_guven_skoru")  # None olabilir (PDF yolunda)
    manuel_oneri = (
        ocr_meta.get("manuel_inceleme_onerisi", False)
        or sinif_guven < SINIFLANDIRMA_GUVEN_ESIGI
    )

    # 5. Kontrat JSON montajı
    cikti = {
        "sema_versiyonu": "1.0",
        "agent1_islem_metadata": {
            "evrak_id": evrak_id,
            "islem_zamani": datetime.now().astimezone().isoformat(),
            "kaynak_tipi": ocr_meta["kaynak_tipi"],
            "sayfa_sayisi": ocr_meta.get("sayfa_sayisi", 1),
            "ocr_motoru": ocr_meta.get("ocr_motoru"),
            "ocr_guven_skoru": ocr_guven,
            "durum": ocr_meta["durum"],
            "manuel_inceleme_onerisi": manuel_oneri,
        },
        "siniflandirma_sonucu": {
            "evrak_turu": sinif["evrak_turu"],
            "alt_kategori": sinif["alt_kategori"],
            "siniflandirma_guven_skoru": sinif_guven,
            "alternatif_tahminler": sinif.get("alternatif_tahminler", []),
        },
        "metin_icerigi": {
            "ham_metin": ham,
            "temizlenmis_metin": temizlenmis,
            "dil": "tr",
        },
        "on_cikarimlar": on_cikarimlar,
    }

    return cikti


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Agent 1 — Evrak OCR & Sınıflandırma")
    parser.add_argument("--dosya", required=True, help="İşlenecek dosya yolu (PDF, JPG, PNG, TXT)")
    parser.add_argument("--evrak-id", default=None, help="Evrak ID (boş bırakılırsa otomatik üretilir)")
    parser.add_argument("--guzel", action="store_true", help="JSON çıktısını girintili yazdır")
    args = parser.parse_args()

    ml_yukle()   # modeli önceden yükle (ilk çağrıda gecikmeyi önle)
    sonuc = agent1_isle(args.dosya, evrak_id=args.evrak_id)

    girinti = 2 if args.guzel else None
    print(json.dumps(sonuc, ensure_ascii=False, indent=girinti))

