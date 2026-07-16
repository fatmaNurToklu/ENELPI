"""
Agent 3 Şablon İskeletleri
--------------------------
Can'ın veri sözleşmesi §0 gereği: Şablon iskeleti (hitap/kapanış/eksik-bilgi
bloğu/uyarı) tamamen deterministik olarak kod tarafından eklenir. LLM sadece
{GOVDE} yer tutucusuna paragraf yazar.

Her şablon üç parça halinde:
- ust_blok:   hitap + şablon-özgü giriş cümlesi (LLM öncesi)
- alt_blok:   eksik-bilgi bloğu + kapanış (LLM sonrası)
"""

# Evrak türü → Şablon türü haritalaması
# (Can'ın sözleşmesi §2: sablon_turu enum'una göre)
EVRAK_TURU_SABLON_HARITASI = {
    "DILEKCE": "DILEKCE_CEVABI",
    "BILGI_EDINME_BASVURUSU": "BILGI_EDINME_CEVABI",
    "SIKAYET_BASVURUSU": "SIKAYET_CEVABI",
    "RESMI_UST_YAZI": "UST_YAZI",
    "CEVAP_YAZISI": "CEVAP_YAZISI",
    "BILGILENDIRME_YAZISI": "BILGILENDIRME_YAZISI",
    "TALIMAT_YAZISI": "TALIMAT_YAZISI",
    "FATURA": "GENEL_AMACLI",
    "SOZLESME_PROTOKOL": "GENEL_AMACLI",
    "TUTANAK_RAPOR": "GENEL_AMACLI",
    "DIGER": "GENEL_AMACLI",
}


# --- ŞABLON İSKELETLERİ ---
# Her şablon: (ust_blok_template, alt_blok_template)
# Placeholder'lar: {hitap}, {konu}, {ilk_mevzuat_atfi}, {alici_kurum}

SABLONLAR = {
    "DILEKCE_CEVABI": {
        "ust_blok": (
            "Sayın {hitap},\n\n"
            "{alici_kurum_atfi} tarafımıza iletmiş olduğunuz "
            "\"{konu}\" konulu dilekçeniz değerlendirilmeye alınmıştır. "
            "{ilk_mevzuat_atfi} 30 gün içerisinde tarafınıza yazılı olarak "
            "bilgi verilecektir.\n\n"
        ),
        "alt_blok": (
            "\nSaygılarımızla,\n"
            "[Yetkili Birim İmzası]"
        ),
    },
    "BILGI_EDINME_CEVABI": {
        "ust_blok": (
            "Sayın {hitap},\n\n"
            "{alici_kurum_atfi} yapmış olduğunuz bilgi edinme talebiniz "
            "tarafımızca kayıt altına alınmıştır. "
            "{ilk_mevzuat_atfi} başvurunuz 15 iş günü içerisinde "
            "sonuçlandırılacaktır.\n\n"
        ),
        "alt_blok": (
            "\nSaygılarımızla,\n"
            "[Yetkili Birim İmzası]"
        ),
    },
    "SIKAYET_CEVABI": {
        "ust_blok": (
            "Sayın {hitap},\n\n"
            "Tarafımıza iletilen şikayet başvurunuz değerlendirilmeye "
            "alınmıştır. {ilk_mevzuat_atfi} gerekli inceleme yapılarak "
            "sonuç tarafınıza bildirilecektir.\n\n"
        ),
        "alt_blok": (
            "\nSaygılarımızla,\n"
            "[Yetkili Birim İmzası]"
        ),
    },
    "UST_YAZI": {
        "ust_blok": (
            "T.C.\n"
            "[Gönderen Kurum]\n\n"
            "Sayı: [Belge Numarası]\n"
            "Konu: {konu}\n\n"
            "{alici_kurum_hitap}\n\n"
        ),
        "alt_blok": (
            "\nBilgilerinizi ve gereğini arz/rica ederim.\n\n"
            "[Yetkili Amir]\n"
            "[Unvan]"
        ),
    },
    "CEVAP_YAZISI": {
        "ust_blok": (
            "T.C.\n"
            "[Gönderen Kurum]\n\n"
            "Sayı: [Belge Numarası]\n"
            "Konu: {konu}\n\n"
            "İlgi: [İlgili Yazı Tarihi ve Sayısı]\n\n"
            "{alici_kurum_hitap}\n\n"
        ),
        "alt_blok": (
            "\nBilgilerinizi arz/rica ederim.\n\n"
            "[Yetkili Amir]\n"
            "[Unvan]"
        ),
    },
    "BILGILENDIRME_YAZISI": {
        "ust_blok": (
            "T.C.\n"
            "[Gönderen Kurum]\n\n"
            "Konu: {konu}\n\n"
            "{alici_kurum_hitap}\n\n"
        ),
        "alt_blok": (
            "\nBilgilerinize sunulur.\n\n"
            "[Yetkili Amir]\n"
            "[Unvan]"
        ),
    },
    "TALIMAT_YAZISI": {
        "ust_blok": (
            "T.C.\n"
            "[Gönderen Kurum]\n\n"
            "Konu: {konu}\n\n"
            "{alici_kurum_hitap}\n\n"
        ),
        "alt_blok": (
            "\nGereğini önemle rica ederim.\n\n"
            "[Yetkili Amir]\n"
            "[Unvan]"
        ),
    },
    "GENEL_AMACLI": {
        "ust_blok": (
            "Sayın İlgili,\n\n"
        ),
        "alt_blok": (
            "\nSaygılarımızla,"
        ),
    },
}


# --- SABIT BLOKLAR (üslup açısından değişmez) ---

UYARI_BLOGU = (
    "[UYARI: Bu evrak düşük güven skoruyla işlenmiştir, "
    "insan denetimi önerilir]\n\n"
)

EKSIK_BILGI_BLOGU_BASLIK = (
    "\n\nBaşvurunuzun işleme alınabilmesi için aşağıdaki bilgi(ler) "
    "tarafımıza iletilmelidir:\n"
)


def sablon_turu_sec(evrak_turu: str) -> str:
    """Evrak türüne göre şablon türünü belirle."""
    return EVRAK_TURU_SABLON_HARITASI.get(evrak_turu, "GENEL_AMACLI")


def hitap_belirle(cikartilan: dict, evrak_turu: str) -> str:
    """
    Şablonun {hitap} placeholder'ı için isim belirle.
    Öncelik: gonderici > imza_sahibi > "İlgili"
    """
    gonderici = cikartilan.get("gonderici")
    imza_sahibi = cikartilan.get("imza_sahibi")

    if gonderici:
        return gonderici
    if imza_sahibi:
        return imza_sahibi
    return "İlgili"


def alici_kurum_atfi_olustur(cikartilan: dict) -> str:
    """
    Vatandaş yazışmalarında: "Kurumumuza" veya "T.C. X Başkanlığına"
    """
    alici = cikartilan.get("alici_kurum")
    if alici:
        return f"{alici} adresine"
    return "Kurumumuza"


def alici_kurum_hitap_olustur(cikartilan: dict) -> str:
    """
    Resmi üst yazılarda alıcı kurum satırı olarak kullanılır.
    """
    alici = cikartilan.get("alici_kurum")
    if alici:
        return alici.upper()
    return "[ALICI KURUM]"


def ilk_mevzuat_atfi_olustur(mevzuat_listesi: list) -> str:
    """
    Sözleşme §5: prompt'a en fazla 2-3 mevzuat gitmeli.
    Şablonda ise sadece EN İLGİLİ tek maddeye atıf yapılır.
    """
    if not mevzuat_listesi:
        return ""
    m = mevzuat_listesi[0]
    return f"{m['kanun']} {m['madde']} uyarınca"


def eksik_bilgi_blogu_olustur(eksik_alanlar: list) -> str:
    """
    Sözleşme §2: her eksik alan için '[BİLGİ EKSİK: <alan>]' yer tutucusu
    Şablondan deterministik gelir.
    """
    if not eksik_alanlar:
        return ""
    satirlar = [f"[BİLGİ EKSİK: {alan}]" for alan in eksik_alanlar]
    return EKSIK_BILGI_BLOGU_BASLIK + "\n".join(satirlar)
