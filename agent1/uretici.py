# -*- coding: utf-8 -*-
"""
Agent 1 sentetik veri üretici - çekirdek mantık.
Çıktı: her evrak için (1) Jinja2 ile doldurulmuş tam metin, (2) agent1_agent2
veri sözleşmesi v1.0 şemasına uyan ground-truth JSON.
"""
import json
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from faker import Faker
from jinja2 import Template

import sys
sys.path.insert(0, str(Path(__file__).parent))
from govdeler import GOVDE_SABLONLARI

fake = Faker("tr_TR")

# --- Taksonomi: agent1_agent2_veri_sozlesmesi.md §4 ile birebir aynı ---
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

EVRAK_TURLERI = list(ZORUNLU_ALANLAR.keys())

# Kurum/birim isim havuzu (kurgu - gerçek kamu kurumu değil, şartname madde 6.5 gereği)
KURGU_KURUMLAR = [
    "Bilişim Vadisi Yönetim Kurulu Başkanlığı", "Anadolu Teknoloji Geliştirme Bölge Müdürlüğü",
    "Marmara Dijital Hizmetler Genel Müdürlüğü", "Kocaeli Kalkınma ve Yatırım Ajansı",
    "Ulusal Veri Yönetişimi Daire Başkanlığı", "Şehir Bilişim Koordinatörlüğü",
]
KURGU_BIRIMLER = [
    "İnsan Kaynakları Daire Başkanlığı", "Bilgi İşlem Daire Başkanlığı",
    "Strateji Geliştirme Daire Başkanlığı", "Hukuk Müşavirliği",
    "Ar-Ge ve Yenilik Daire Başkanlığı", "Mali Hizmetler Daire Başkanlığı",
]
UNVANLAR = ["Daire Başkanı", "Genel Müdür Yardımcısı", "Şube Müdürü", "Koordinatör"]

KONU_HAVUZU = {
    "DILEKCE": ["Hizmet talebi hakkında", "Bilgi talebi hakkında", "İtiraz başvurusu hakkında"],
    "BILGI_EDINME_BASVURUSU": ["Açık kaynak destekleri hakkında", "Proje bütçesi hakkında", "Personel alımı hakkında"],
    "SIKAYET_BASVURUSU": ["Hizmet aksaması hakkında", "Personel tutumu hakkında", "Süreç gecikmesi hakkında"],
    "RESMI_UST_YAZI": ["Stajyer alım süreçleri Hk.", "Bütçe revizyonu Hk.", "Eğitim programı Hk."],
    "CEVAP_YAZISI": ["Bilgi talebine cevaben", "Başvuru değerlendirmesi Hk.", "Talep sonucu Hk."],
    "BILGILENDIRME_YAZISI": ["Sistem bakım çalışması Hk.", "Toplantı duyurusu Hk.", "Süreç değişikliği Hk."],
    "TALIMAT_YAZISI": ["Acil eylem planı Hk.", "Veri güvenliği önlemleri Hk.", "Raporlama takvimi Hk."],
    "FATURA": ["Danışmanlık hizmet bedeli", "Yazılım lisans bedeli", "Eğitim hizmet bedeli"],
    "SOZLESME_PROTOKOL": ["İşbirliği Protokolü", "Hizmet Alım Sözleşmesi", "Veri Paylaşım Protokolü"],
    "TUTANAK_RAPOR": ["Teslim-tesellüm tutanağı", "Denetim raporu", "Toplantı tutanağı"],
    "DIGER": ["Genel duyuru", "Etkinlik daveti", "Çeşitli hususlar"],
}

GOVDE_CUMLE_HAVUZU = [
    "kurumunuz bünyesinde yürütülen çalışmalar kapsamında gerekli bilgilendirmenin yapılması talep edilmektedir.",
    "konu ile ilgili olarak tarafımıza ivedilikle dönüş sağlanması önem arz etmektedir.",
    "ilgili sürecin mevzuata uygun şekilde yürütülmesi beklenmektedir.",
    "yapılan başvuru sonucunda gerekli işlemlerin başlatılmasını saygılarımla rica ederim.",
    "bahse konu husus hakkında detaylı bilgi ve belge talep edilmektedir.",
    "söz konusu işlemin ilgili birimce değerlendirilerek sonuçlandırılması gerekmektedir.",
]


def _rastgele_tarih():
    gun = random.randint(0, 60)
    return (datetime(2026, 6, 30) - timedelta(days=gun)).strftime("%d.%m.%Y")


def _belge_sayisi_uret():
    return f"E-{random.randint(10000000,99999999)}-{random.randint(100,999)}.{random.randint(10,99)}.{random.randint(10,99)}-{random.randint(1000,9999)}"


def _govde_metni_uret(cumle_sayisi=3):
    return " ".join(random.sample(GOVDE_CUMLE_HAVUZU, k=min(cumle_sayisi, len(GOVDE_CUMLE_HAVUZU))))


def evrak_uret(evrak_turu: str, eksik_alan_olasiligi: float = 0.35, index: int = 1) -> dict:
    """
    Tek bir sentetik evrak üretir.
    eksik_alan_olasiligi: zorunlu olmayan/bazı zorunlu alanların kasıtlı olarak
    null bırakılma olasılığı (Agent 2'nin eksik bilgi tespitini test etmek için).
    Dönüş: {"dolu_metin": str, "ground_truth": dict (kontrat şemasına uygun)}
    """
    if evrak_turu not in GOVDE_SABLONLARI:
        raise ValueError(f"Tanımsız evrak_turu: {evrak_turu}")

    alici_kurum = random.choice(KURGU_KURUMLAR)
    gonderici_kurum = random.choice([k for k in KURGU_KURUMLAR if k != alici_kurum])
    gonderici_birim = random.choice(KURGU_BIRIMLER)
    konu = random.choice(KONU_HAVUZU[evrak_turu])
    govde_metni = _govde_metni_uret(random.randint(2, 4))

    # Kişi/kurum türevli alanlar evrak tipine göre değişir
    kisi_kaynakli = evrak_turu in {"DILEKCE", "BILGI_EDINME_BASVURUSU", "SIKAYET_BASVURUSU"}
    gonderici = fake.name() if kisi_kaynakli else gonderici_birim
    imza_sahibi = fake.name()
    imza_unvani = random.choice(UNVANLAR)
    tc_kimlik = fake.numerify("##########1") if kisi_kaynakli else None  # 11 hane, sahte
    tarih = _rastgele_tarih()
    belge_sayisi = _belge_sayisi_uret() if evrak_turu in {
        "RESMI_UST_YAZI", "CEVAP_YAZISI", "TALIMAT_YAZISI", "FATURA"
    } else None
    ilgi_yazi = f"{(datetime(2026,6,30)-timedelta(days=random.randint(5,30))).strftime('%d.%m.%Y')} tarih ve {_belge_sayisi_uret()} sayılı yazınız" \
        if evrak_turu == "CEVAP_YAZISI" else None
    tutar = f"{random.randint(500, 50000):,}".replace(",", ".") if evrak_turu == "FATURA" else None

    alan_degerleri = {
        "alici_kurum": alici_kurum,
        "gonderici_kurum": gonderici_kurum,
        "gonderici_birim": gonderici_birim,
        "gonderici": gonderici,
        "konu": konu,
        "govde_metni": govde_metni,
        "tarih": tarih,
        "tc_kimlik": tc_kimlik,
        "belge_sayisi": belge_sayisi,
        "imza_sahibi": imza_sahibi,
        "imza_unvani": imza_unvani,
        "ilgi_yazi": ilgi_yazi,
        "tutar": tutar,
    }

    # --- Kasıtlı eksik alan mantığı: sadece zorunlu alanlar listesinden seç ---
    zorunlular = ZORUNLU_ALANLAR[evrak_turu]
    eksik_birakilan = []
    for alan in zorunlular:
        if alan in alan_degerleri and alan_degerleri[alan] is not None:
            if random.random() < eksik_alan_olasiligi:
                alan_degerleri[alan] = None
                eksik_birakilan.append(alan)

    # Şablonu doldur (None alanlar Jinja'da {% if %} ile zaten satırı düşürür)
    sablon = Template(GOVDE_SABLONLARI[evrak_turu])
    dolu_metin = sablon.render(**alan_degerleri).strip()
    # fazla boş satırları sadeleştir
    dolu_metin = "\n".join(line for line in dolu_metin.splitlines())
    while "\n\n\n" in dolu_metin:
        dolu_metin = dolu_metin.replace("\n\n\n", "\n\n")

    evrak_id = f"EVR-2026-{index:04d}"
    alt_kategori = "VATANDAS_TALEBI" if kisi_kaynakli else (
        "KURUM_ICI_YAZISMA" if evrak_turu in {"RESMI_UST_YAZI", "CEVAP_YAZISI", "BILGILENDIRME_YAZISI", "TALIMAT_YAZISI"} else None
    )

    ground_truth = {
        "sema_versiyonu": "1.0",
        "agent1_islem_metadata": {
            "evrak_id": evrak_id,
            "islem_zamani": datetime(2026, 6, 30, random.randint(8, 17), random.randint(0, 59)).isoformat() + "+03:00",
            "kaynak_tipi": "DIJITAL_METIN",  # bu aşamada henüz görüntü/OCR yok; render_pdf.py bunu günceller
            "sayfa_sayisi": 1,
            "ocr_motoru": None,
            "ocr_guven_skoru": None,
            "durum": "BASARILI",
            "manuel_inceleme_onerisi": False,
        },
        "siniflandirma_sonucu": {
            "evrak_turu": evrak_turu,
            "alt_kategori": alt_kategori,
            "siniflandirma_guven_skoru": 1.0,  # ground truth - sentetik üretimde kesin
        },
        "metin_icerigi": {
            "ham_metin": None,
            "temizlenmis_metin": dolu_metin,
            "dil": "tr",
        },
        "on_cikarimlar": {
            "gonderici": alan_degerleri["gonderici"],
            "alici_kurum": alan_degerleri["alici_kurum"] if evrak_turu != "FATURA" else None,
            "konu": alan_degerleri["konu"],
            "tarih": _tarih_iso(alan_degerleri["tarih"]),
            "belge_sayisi": alan_degerleri["belge_sayisi"],
            "tc_kimlik": alan_degerleri["tc_kimlik"],
            "imza_sahibi": alan_degerleri["imza_sahibi"] if evrak_turu in {
                "RESMI_UST_YAZI", "CEVAP_YAZISI", "BILGILENDIRME_YAZISI", "TALIMAT_YAZISI", "SOZLESME_PROTOKOL"
            } else None,
            "ekler": None,
        },
        "_meta_eksik_birakilan_alanlar": eksik_birakilan,  # değerlendirme/test amaçlı, kontrat dışı yardımcı alan
    }
    return {"dolu_metin": dolu_metin, "ground_truth": ground_truth}


def _tarih_iso(tarih_str):
    if not tarih_str:
        return None
    try:
        return datetime.strptime(tarih_str, "%d.%m.%Y").strftime("%Y-%m-%d")
    except ValueError:
        return None


def veri_seti_uret(her_tur_icin_adet: int = 10, eksik_alan_olasiligi: float = 0.35, seed: int = 42):
    random.seed(seed)
    Faker.seed(seed)
    sonuclar = []
    index = 1
    for tur in EVRAK_TURLERI:
        for _ in range(her_tur_icin_adet):
            kayit = evrak_uret(tur, eksik_alan_olasiligi=eksik_alan_olasiligi, index=index)
            sonuclar.append(kayit)
            index += 1
    return sonuclar


if __name__ == "__main__":
    veri = veri_seti_uret(her_tur_icin_adet=2)
    print(f"{len(veri)} sentetik evrak üretildi (önizleme için {len(EVRAK_TURLERI)} tür x 2 adet).")
    print("\n--- ÖRNEK 1 ---\n")
    print(veri[0]["dolu_metin"])
    print("\n--- GROUND TRUTH ---\n")
    print(json.dumps(veri[0]["ground_truth"], ensure_ascii=False, indent=2))
