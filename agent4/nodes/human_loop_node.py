"""
Agent 4 — Human-in-the-Loop (İnsan Döngüsü) Node'u
LangGraph interrupt mekanizmasıyla eksik bilgi toplama ve geri besleme döngüsü.
Sözleşme referansı: agent4_orkestrasyon_sozlesmesi.md §6
"""

import logging
from typing import Dict, Any

from langgraph.types import interrupt

from agent4.state import AgentState, MAX_LOOPBACK

logger = logging.getLogger(__name__)


def request_missing_info_node(state: AgentState) -> Dict[str, Any]:
    """
    Eksik bilgi durumunda LangGraph grafiğini dondurur (interrupt).

    Akış (sözleşme §6):
    1. agent3_output'taki eksik_alan_yer_tutucular'ı belirle
    2. interrupt() ile grafiği dondur → UI'a eksik alanları + taslağı gönder
    3. Kullanıcı veriyi girince, resume ile bu node'dan devam et
    4. Girilen verileri temizlenmis_metin'e ekle (Agent 2 loopback için)
    5. loopback_count artır (maks: MAX_LOOPBACK)

    Not: interrupt() çağrısı bu fonksiyonu iki kez çalıştırır:
    - İlk çağrı: interrupt() ile durur, UI'a veri gönderir
    - Resume sonrası: interrupt() döngüsünden gelen değeri alır ve devam eder
    """
    agent3: Dict = state.get("agent3_output") or {}
    taslak = agent3.get("uretilen_taslak", {}) or {}
    eksik_alanlar = taslak.get("eksik_alan_yer_tutucular", []) or []
    taslak_metni = taslak.get("taslak_metni", "") or ""
    loopback_count = state.get("loopback_count", 0)
    hata_log = list(state.get("hata_log", []))

    # Maksimum loopback kontrolü
    if loopback_count >= MAX_LOOPBACK:
        hata_mesaji = (
            f"[HumanLoop] Maksimum loopback sınırına ulaşıldı ({MAX_LOOPBACK}). "
            "Evrak manuel kuyruğa yönlendiriliyor."
        )
        logger.warning(hata_mesaji)
        hata_log.append(hata_mesaji)
        return {
            "sistem_durumu": "KRITIK_HATA_MANUEL_KUYRUK",
            "hata_log": hata_log,
            "loopback_count": loopback_count,
        }

    # ─── LangGraph Interrupt ─────────────────────────────────────────────────
    # Grafik burada durur. UI'a eksik alanları ve taslağı gönderir.
    # Kullanıcı formu doldurduğunda resume edilir.
    logger.info(
        "[HumanLoop] Interrupt tetiklendi. Eksik alanlar: %s",
        eksik_alanlar
    )

    kullanici_girdisi: Dict[str, str] = interrupt({
        "tip": "EKSIK_BILGI_FORMU",
        "mesaj": "Aşağıdaki alanlar eksik tespit edilmiştir. Lütfen bilgileri girin:",
        "eksik_alanlar": eksik_alanlar,
        "taslak_metni": taslak_metni,
        "evrak_id": state["evrak_id"],
    })

    # ─── Resume Sonrası: Kullanıcı Girişini İşle ─────────────────────────────
    logger.info("[HumanLoop] Kullanıcı girdisi alındı: %s", kullanici_girdisi)

    # Temizlenmiş metne kullanıcı girdisini ekle (Agent 2 loopback için)
    mevcut_metin = state.get("temizlenmis_metin") or ""
    ek_bilgi_str = "\n\n--- Kullanıcı Tarafından Tamamlanan Eksik Bilgiler ---\n"
    for alan, deger in kullanici_girdisi.items():
        if deger and deger.strip():
            ek_bilgi_str += f"{alan}: {deger}\n"

    guncellenmis_metin = mevcut_metin + ek_bilgi_str

    # Geçmiş listesine yeni alanları ekle
    gecmis = list(state.get("eksik_alanlar_gecmisi", []))
    gecmis.extend(kullanici_girdisi.keys())

    hata_log.append(
        f"[HumanLoop] Loopback #{loopback_count + 1}: "
        f"{list(kullanici_girdisi.keys())} alanları tamamlandı. Agent 2'ye geri besleniyor."
    )

    return {
        "temizlenmis_metin": guncellenmis_metin,
        "eksik_alanlar_gecmisi": gecmis,
        "loopback_count": loopback_count + 1,
        "hata_log": hata_log,
    }


def human_approval_node(state: AgentState) -> Dict[str, Any]:
    """
    Manuel inceleme / üslup ihlali durumunda insan onayı bekler.

    TASLAK_HAZIR_MANUEL_INCELEME_UYARILI ve resmi_uslup_kontrolu.uygun_mu=False
    durumlarında taslak otomatik olarak gönderilemez; insan onayı zorunludur.

    Sözleşme §5: "resmi_uslup_kontrolu.uygun_mu: false geldiğinde durum ne olursa
    olsun Agent 4 taslağı otomatik gönderilebilir olarak işaretlememelidir."
    """
    agent3: Dict = state.get("agent3_output") or {}
    taslak = agent3.get("uretilen_taslak", {}) or {}
    taslak_metni = taslak.get("taslak_metni", "")
    uslup_kontrolu = taslak.get("resmi_uslup_kontrolu", {}) or {}
    uslup_sorunlari = uslup_kontrolu.get("tespit_edilen_sorunlar", [])

    durum = agent3.get("durum", "")
    hata_log = list(state.get("hata_log", []))

    # Onay bilgisi hazırla
    sebep = (
        "Düşük OCR güven skoru nedeniyle manuel inceleme önerilmektedir."
        if durum == "TASLAK_HAZIR_MANUEL_INCELEME_UYARILI"
        else f"Resmî üslup ihlalleri tespit edildi: {', '.join(uslup_sorunlari)}"
    )

    logger.info("[HumanApproval] İnsan onayı bekleniyor. Sebep: %s", sebep)

    # Interrupt: kamu personelinin onayını bekle
    onay_karari: Dict[str, Any] = interrupt({
        "tip": "INSAN_ONAYI_FORMU",
        "mesaj": f"Bu taslak otomatik olarak gönderilemez. Sebep: {sebep}",
        "taslak_metni": taslak_metni,
        "uslup_sorunlari": uslup_sorunlari,
        "evrak_id": state["evrak_id"],
        "eylemler": ["ONAYLA", "REDDET", "DUZENLE"],
    })

    karar = onay_karari.get("karar", "REDDET")
    logger.info("[HumanApproval] Karar: %s", karar)

    hata_log.append(f"[HumanApproval] Kamu personeli kararı: {karar}. Sebep: {sebep}")

    if karar == "ONAYLA":
        sistem_durumu = "INSAN_ONAYI_BEKLIYOR"  # Onaylandı ama insan onaylı olarak işaretli
    else:
        sistem_durumu = "KRITIK_HATA_MANUEL_KUYRUK"

    res_dict = {
        "sistem_durumu": sistem_durumu,
        "hata_log": hata_log,
    }

    if karar == "ONAYLA" and "edited_draft" in onay_karari:
        yeni_agent3 = dict(agent3)
        yeni_taslak = dict(taslak)
        yeni_taslak["taslak_metni"] = onay_karari["edited_draft"]
        yeni_agent3["uretilen_taslak"] = yeni_taslak
        res_dict["agent3_output"] = yeni_agent3

    return res_dict
