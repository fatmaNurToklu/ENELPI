"""
Agent 3 Resmi Üslup Kontrolü
----------------------------
Can'ın sözleşmesi §2: Sadece MODELİN ürettiği gövde paragrafına uygulanır.
Şablon iskeleti (hitap/kapanış) kontrol dışıdır çünkü zaten deterministik.

Yaklaşım: Kural tabanlı (regex + kelime listesi), LLM-judge DEĞİL.
Bu sayede hızlı, tekrarlanabilir ve açıklanabilir.
"""

import re


# --- YASAKLI İFADE LİSTELERİ ---

# İkinci tekil şahıs kullanımı (resmi yazışmada yasak)
IKINCI_TEKIL_SAHIS = [
    r"\bsen\b", r"\bseni\b", r"\bsana\b", r"\bsende\b", r"\bsenden\b",
    r"\bsenin\b", r"\bsensin\b",
    # Fiil çekimleri: -sın/-sın/-sun/-sün
    r"\b\w+(sın|sin|sun|sün)\b(?!\.)",  # örn: "geldin", "gittin"
]

# Argo/gündelik/uygunsuz ifadeler
ARGO_KELIMELER = {
    "bok", "sik", "amına", "aq", "amk", "orospu", "piç", "kaltak",
    "salak", "gerizekalı", "aptal", "mal", "moron",
    # Gündelik/samimi
    "abi", "abla", "kardeş", "yeğen", "hacı", "kanka", "kanki",
    "reis", "üstat", "koçum", "adamım",
    # İnternet dili
    "lol", "wtf", "omg", "bruh", "sus",
}

# Emoji regex (temel unicode aralıkları)
EMOJI_REGEX = re.compile(
    r"[\U0001F300-\U0001F9FF]|[\U0001F600-\U0001F64F]|[\U0001F680-\U0001F6FF]|"
    r"[\U00002600-\U000027BF]|[\U0001F1E0-\U0001F1FF]|[\U0001F900-\U0001F9FF]"
)

# Aşırı noktalama (birden fazla ! veya ?)
ASIRI_NOKTALAMA = re.compile(r"[!?]{2,}")

# Gövdenin çok kısa olması (LLM boş üretmiş)
MIN_KELIME_SAYISI = 8

# İngilizce sızıntısı (yaygın kelimeler)
INGILIZCE_SIZINTI = {
    "please", "thank you", "regards", "hello", "hi", "hey",
    "email", "meeting", "update", "team", "check",
    "asap", "fyi", "btw", "ok", "okay",
}


def uslup_kontrol_et(govde: str) -> dict:
    """
    LLM'in ürettiği gövde paragrafını kural tabanlı kontrolden geçirir.
    Sözleşme §2'deki resmi_uslup_kontrolu şemasına uygun döner.

    Döner:
        {
            "uygun_mu": bool,
            "tespit_edilen_sorunlar": [str, ...]
        }
    """
    sorunlar = []
    govde_lower = govde.lower()

    # 1. Gövde boş veya çok kısa mı?
    if not govde or not govde.strip():
        sorunlar.append("bos_cikti")
        return {"uygun_mu": False, "tespit_edilen_sorunlar": sorunlar}

    kelime_sayisi = len(govde.split())
    if kelime_sayisi < MIN_KELIME_SAYISI:
        sorunlar.append(f"cok_kisa_govde ({kelime_sayisi} kelime)")

    # 2. Argo/gündelik ifade
    bulunan_argo = []
    for kelime in ARGO_KELIMELER:
        if re.search(rf"\b{re.escape(kelime)}\b", govde_lower):
            bulunan_argo.append(kelime)
    if bulunan_argo:
        sorunlar.append(f"argo_veya_gundelik_ifade: {', '.join(bulunan_argo)}")

    # 3. İkinci tekil şahıs
    ikinci_tekil_bulundu = False
    for pattern in IKINCI_TEKIL_SAHIS[:6]:  # doğrudan zamirler
        if re.search(pattern, govde_lower):
            ikinci_tekil_bulundu = True
            break
    if ikinci_tekil_bulundu:
        sorunlar.append("ikinci_tekil_sahis_kullanimi")

    # 4. Emoji
    emojiler = EMOJI_REGEX.findall(govde)
    if emojiler:
        sorunlar.append(f"emoji_tespit_edildi ({len(emojiler)} adet)")

    # 5. Aşırı noktalama
    if ASIRI_NOKTALAMA.search(govde):
        sorunlar.append("asiri_noktalama")

    # 6. İngilizce sızıntı
    bulunan_ingilizce = []
    for kelime in INGILIZCE_SIZINTI:
        if re.search(rf"\b{re.escape(kelime)}\b", govde_lower):
            bulunan_ingilizce.append(kelime)
    if bulunan_ingilizce:
        sorunlar.append(f"ingilizce_kelime: {', '.join(bulunan_ingilizce)}")

    # 7. Sadece placeholder içeriyor mu? ([BİLGİ EKSİK: ...] gibi)
    metinsiz_govde = re.sub(r"\[.*?\]", "", govde).strip()
    if len(metinsiz_govde.split()) < MIN_KELIME_SAYISI:
        sorunlar.append("govde_sadece_yer_tutuculardan_olusuyor")

    return {
        "uygun_mu": len(sorunlar) == 0,
        "tespit_edilen_sorunlar": sorunlar,
    }


if __name__ == "__main__":
    # Kısa self-test
    ornekler = [
        (
            "Kurumumuza yapılan başvurunuz değerlendirilerek en kısa sürede "
            "cevap verilecektir. Süreç mevzuata uygun şekilde yürütülmektedir.",
            True,
        ),
        ("Selam abi, işini hemen halledicez :))", False),
        ("Please check the attached document.", False),
        ("", False),
        ("Kısa metin.", False),  # çok kısa
        (
            "Sen dilekçe göndermişsin, sana cevap vereceğiz.",  # 2. tekil şahıs
            False,
        ),
    ]
    for govde, beklenen in ornekler:
        sonuc = uslup_kontrol_et(govde)
        durum = "✓" if sonuc["uygun_mu"] == beklenen else "✗"
        print(f"{durum} beklenen={beklenen} sonuc={sonuc['uygun_mu']}")
        if sonuc["tespit_edilen_sorunlar"]:
            print(f"  Sorunlar: {sonuc['tespit_edilen_sorunlar']}")
