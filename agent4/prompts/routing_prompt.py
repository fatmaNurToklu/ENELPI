"""
Agent 4 — Few-Shot Yönlendirme Prompt Şablonu
Sözleşme referansı: agent4_orkestrasyon_sozlesmesi.md §4
"""

# ─── Sistem Prompt ────────────────────────────────────────────────────────────
ROUTING_SYSTEM_PROMPT = """Sen bir kamu kurumu akıllı evrak yönlendirme ajanısın. Görevin, gelen evrakın içeriğini, konusunu ve ilişkili mevzuatı analiz ederek belgeyi incelemesi gereken en doğru iç birimi seçmek ve gerekçelendirmektir.

Seçebileceğin Hedef Birimler ve Görev Alanları:
1. INSAN_KAYNAKLARI: Personel alımı, özlük hakları, izinler, tayinler ve eğitim süreçleri.
2. BILGI_ISLEM: Yazılım, donanım, ağ altyapısı, siber güvenlik, sistem erişim talepleri.
3. HUKUK_MUSAVIRLIGI: Dava dosyaları, ihtarnameler, sözleşme ve protokol incelemeleri.
4. YAZI_ISLERI: Vatandaş dilekçeleri, genel bilgi edinme başvuruları, kurumlar arası resmi üst yazılar.
5. DESTEK_HIZMETLERI: Fatura ödemeleri, bina bakım-onarım, malzeme tedariki, lojistik.
6. STRATEJI_GELISTIRME: Stratejik plan, performans değerlendirme, kurumsal gelişim projeleri.

Kurallar:
- Yanıtını SADECE aşağıdaki JSON formatında üret, başka hiçbir şey yazma.
- Gerekçe alanında evrak içeriği ile seçilen birimin görev alanını doğrudan ilişkilendir (1-2 cümle, Türkçe).
- Eğer evrak içeriği hiçbir birime uymuyorsa veya çok belirsizse hedef_birim olarak 'MANUEL_BELIRSIZ' seç ve güven skorunu 0.3'ün altında tut.
- yonlendirme_guven_skoru 0.0 ile 1.0 arasında ondalık bir sayı olmalıdır."""

# ─── Few-Shot Örnekler ────────────────────────────────────────────────────────
FEW_SHOT_EXAMPLES = [
    {
        "girdi": {
            "evrak_turu": "BILGI_EDINME_BASVURUSU",
            "alici_kurum": "T.C. Sağlık Bakanlığı",
            "konu": "Doktor kadro talepleri hakkında bilgi edinme",
            "ozet": "Vatandaş, kurumda açık doktor kadrolarının sayısı ve başvuru koşulları hakkında bilgi talep etmektedir.",
            "ilgili_mevzuat": "4982 Sayılı Bilgi Edinme Hakkı Kanunu Madde 5",
        },
        "cikti": {
            "hedef_birim": "INSAN_KAYNAKLARI",
            "gerekce": "Evrak, doktor kadro talepleri ve başvuru koşullarına ilişkin bilgi edinme başvurusudur. Bu konu doğrudan personel ve kadro yönetimi süreçleriyle ilgili olduğundan İnsan Kaynakları birimine yönlendirilmelidir.",
            "yonlendirme_guven_skoru": 0.91,
        },
    },
    {
        "girdi": {
            "evrak_turu": "SIKAYET_BASVURUSU",
            "alici_kurum": "T.C. Ulaştırma Bakanlığı",
            "konu": "Kurumsal e-posta sistemine erişilememesi",
            "ozet": "Personel, kurumsal e-posta ve VPN sistemine erişimin kesildiğini bildirmekte ve teknik destek talep etmektedir.",
            "ilgili_mevzuat": "",
        },
        "cikti": {
            "hedef_birim": "BILGI_ISLEM",
            "gerekce": "Evrak, kurumsal e-posta ve VPN erişimiyle ilgili teknik bir sorunu kapsamaktadır. Bu tür sistem erişim ve altyapı sorunları Bilgi İşlem biriminin sorumluluk alanına girmektedir.",
            "yonlendirme_guven_skoru": 0.95,
        },
    },
    {
        "girdi": {
            "evrak_turu": "RESMI_UST_YAZI",
            "alici_kurum": "T.C. Hazine ve Maliye Bakanlığı",
            "konu": "2026 yılı bütçe sarf malzemesi fatura onayı",
            "ozet": "Kurum, 2026 yılı birinci çeyrek sarf malzemeleri alımına ait faturaların ödeme onayı için Maliye Bakanlığına başvurmaktadır.",
            "ilgili_mevzuat": "4734 Sayılı Kamu İhale Kanunu Madde 22",
        },
        "cikti": {
            "hedef_birim": "DESTEK_HIZMETLERI",
            "gerekce": "Evrak, sarf malzeme alımına ait fatura ödeme onayı talebini içermektedir. Malzeme tedariki ve fatura işlemleri Destek Hizmetleri biriminin görev kapsamındadır.",
            "yonlendirme_guven_skoru": 0.88,
        },
    },
]

# ─── Kullanıcı (Dinamik) Prompt Şablonu ──────────────────────────────────────
ROUTING_USER_TEMPLATE = """Aşağıdaki evrak verilerini analiz et ve yönlendirme kararını JSON formatında üret:

Evrak Türü: {evrak_turu}
Belirtilen Muhatap: {alici_kurum}
Konu: {konu}
İçerik Özeti: {ozet}
Eşleşen Mevzuat: {ilgili_mevzuat}

Yanıtın SADECE şu JSON formatında olsun:
{{
  "hedef_birim": "<BİRİM_ADI>",
  "gerekce": "<1-2 cümle Türkçe gerekçe>",
  "yonlendirme_guven_skoru": <0.0-1.0 arası sayı>
}}"""


def build_few_shot_messages(evrak_turu: str, alici_kurum: str, konu: str,
                             ozet: str, ilgili_mevzuat: str) -> list:
    """
    Ollama/LangChain için Few-Shot mesaj listesi oluşturur.
    İlk 3 örneği kullanır; mevzuat listesini metne dönüştürür.
    """
    import json

    messages = [{"role": "system", "content": ROUTING_SYSTEM_PROMPT}]

    # Few-shot örnekler ekle
    for ex in FEW_SHOT_EXAMPLES:
        user_msg = ROUTING_USER_TEMPLATE.format(
            evrak_turu=ex["girdi"]["evrak_turu"],
            alici_kurum=ex["girdi"]["alici_kurum"],
            konu=ex["girdi"]["konu"],
            ozet=ex["girdi"]["ozet"],
            ilgili_mevzuat=ex["girdi"]["ilgili_mevzuat"],
        )
        assistant_msg = json.dumps(ex["cikti"], ensure_ascii=False, indent=2)
        messages.append({"role": "user", "content": user_msg})
        messages.append({"role": "assistant", "content": assistant_msg})

    # Gerçek istek
    real_msg = ROUTING_USER_TEMPLATE.format(
        evrak_turu=evrak_turu,
        alici_kurum=alici_kurum or "Belirtilmemiş",
        konu=konu or "Belirtilmemiş",
        ozet=ozet or "Özet mevcut değil.",
        ilgili_mevzuat=ilgili_mevzuat or "Mevzuat eşleşmesi yapılamamıştır.",
    )
    messages.append({"role": "user", "content": real_msg})
    return messages
