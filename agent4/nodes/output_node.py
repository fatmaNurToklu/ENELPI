"""
Agent 4 — Nihai Çıktı Üretim Node'u
Agent4_Nihai_Cikti_Semasi_v1 formatında JSON üretir.
Sözleşme referansı: agent4_orkestrasyon_sozlesmesi.md §3
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from agent4.state import AgentState
from agent4.validators.schema_validator import validate_agent4_output

logger = logging.getLogger(__name__)

# ─── Durum → Aksiyon Eşlemesi ────────────────────────────────────────────────
DURUM_AKSIYON_MAP = {
    "OTOMATIK_ONAYLANABILIR": "ARSIFLE_VE_GONDER",
    "INSAN_ONAYI_BEKLIYOR":   "UI_ONAY_EKRANINA_DUSUR",
    "EKSIK_BILGI_TALEBI":     "UI_INPUT_FORMU_AC",
    "KRITIK_HATA_MANUEL_KUYRUK": "MANUEL_INCELEME_MASASINA_AT",
}

# ─── Kullanıcı Mesajı Şablonları ─────────────────────────────────────────────
KULLANICI_MESAJLARI = {
    "OTOMATIK_ONAYLANABILIR": (
        "✅ Evrak başarıyla işlendi ve {hedef_birim} birimine yönlendirildi. "
        "Taslak otomatik olarak arşivleme kuyruğuna alındı. "
        "Güven skoru: %{guven}."
    ),
    "INSAN_ONAYI_BEKLIYOR": (
        "⚠️ Evrak insan denetimine alındı. "
        "Taslak {hedef_birim} birimine yönlendirilmek üzere hazır, ancak yetkili personelin "
        "onayı beklenmektedir. Lütfen taslağı inceleyip onaylayın veya düzeltin."
    ),
    "EKSIK_BILGI_TALEBI": (
        "📝 Evrakta eksik bilgiler tespit edildi: {eksik_alanlar}. "
        "Lütfen bu alanları doldurun; sistem bilgileri alır almaz taslak üretimini tamamlayacaktır."
    ),
    "KRITIK_HATA_MANUEL_KUYRUK": (
        "❌ Evrak otomatik olarak işlenemedi. "
        "Neden: {hata_neden}. "
        "Evrak manuel inceleme masasına yönlendirilmiştir."
    ),
}


def _belirle_sistem_durumu(state: AgentState) -> str:
    """
    Sözleşme §5 karar matrisine göre nihai sistem durumunu hesaplar.
    """
    # Önceki node'dan zaten belirlendiyse kullan
    mevcut_durum = state.get("sistem_durumu")
    if mevcut_durum in ["KRITIK_HATA_MANUEL_KUYRUK", "INSAN_ONAYI_BEKLIYOR"]:
        return mevcut_durum

    agent1: Dict = state.get("agent1_output") or {}
    agent3: Dict = state.get("agent3_output") or {}
    taslak = agent3.get("uretilen_taslak", {}) or {}
    uslup = taslak.get("resmi_uslup_kontrolu", {}) or {}
    agent3_durum = agent3.get("durum", "")

    # Agent 1 kritik hata
    meta = agent1.get("agent1_islem_metadata", {}) or {}
    if meta.get("durum") == "BASARISIZ":
        return "KRITIK_HATA_MANUEL_KUYRUK"

    # Agent 3 üretilemedi (retry sonrası da başarısız)
    if agent3_durum == "URETILEMEDI":
        return "KRITIK_HATA_MANUEL_KUYRUK"

    # Üslup ihlali (sözleşme §5: durum'dan bağımsız ayrı kapı)
    if not uslup.get("uygun_mu", True):
        return "INSAN_ONAYI_BEKLIYOR"

    # Manuel inceleme uyarılı
    if agent3_durum == "TASLAK_HAZIR_MANUEL_INCELEME_UYARILI":
        return "INSAN_ONAYI_BEKLIYOR"

    # Eksik bilgi
    if agent3_durum == "TASLAK_HAZIR_EKSIK_BILGI":
        return "EKSIK_BILGI_TALEBI"

    # Normal durum
    ocr_guven = meta.get("ocr_guven_skoru", 1.0) or 1.0
    if ocr_guven >= 0.70 and agent3_durum == "TASLAK_HAZIR":
        return "OTOMATIK_ONAYLANABILIR"

    return "INSAN_ONAYI_BEKLIYOR"


def output_node(state: AgentState) -> Dict[str, Any]:
    """
    Pipeline sonunda Agent4_Nihai_Cikti_Semasi_v1 formatında JSON üretir.

    Her durumda:
    - sistem_durumu hesaplar
    - sistem_aksiyonu belirler
    - taslak özetini çıkarır
    - yönlendirme kararını iletir
    - kullanıcı mesajı oluşturur
    - şema doğrulaması yapar
    """
    agent3: Dict = state.get("agent3_output") or {}
    taslak = agent3.get("uretilen_taslak", {}) or {}
    kaynak_baglam = agent3.get("kaynak_baglam", {}) or {}
    yonlendirme: Optional[Dict] = state.get("nihai_yonlendirme")
    hata_log = list(state.get("hata_log", []))

    # Sistem durumunu belirle
    sistem_durumu = _belirle_sistem_durumu(state)
    sistem_aksiyonu = DURUM_AKSIYON_MAP.get(sistem_durumu, "MANUEL_INCELEME_MASASINA_AT")

    # Yönlendirme bilgileri
    hedef_birim = (yonlendirme or {}).get("hedef_birim", "MANUEL_BELIRSIZ")
    guven_pct = int(((yonlendirme or {}).get("yonlendirme_guven_skoru", 0)) * 100)

    # Eksik alanlar
    eksik_alanlar = kaynak_baglam.get("eksik_alanlar", []) or []
    eksik_str = ", ".join(eksik_alanlar) if eksik_alanlar else "—"

    # Hata nedeni
    son_hata = hata_log[-1] if hata_log else "Bilinmeyen hata."

    # Kullanıcı mesajı oluştur
    mesaj_sablonu = KULLANICI_MESAJLARI.get(sistem_durumu, "Evrak işlendi.")
    kullanici_mesaji = mesaj_sablonu.format(
        hedef_birim=hedef_birim,
        guven=guven_pct,
        eksik_alanlar=eksik_str,
        hata_neden=son_hata,
    )

    # Taslak nesnesi (KRITIK_HATA durumunda None olabilir)
    if sistem_durumu == "KRITIK_HATA_MANUEL_KUYRUK" and not taslak.get("taslak_metni"):
        uretilen_taslak_obj = None
    else:
        uretilen_taslak_obj = {
            "taslak_metni": taslak.get("taslak_metni", ""),
            "sablon_turu": taslak.get("sablon_turu", "GENEL_AMACLI"),
            "uslup_uygun_mu": (taslak.get("resmi_uslup_kontrolu") or {}).get("uygun_mu", True),
        }

    # Nihai JSON çıktı
    nihai_cikti = {
        "sema_versiyonu": "1.0",
        "evrak_id": state["evrak_id"],
        "sistem_durumu": sistem_durumu,
        "sistem_aksiyonu": sistem_aksiyonu,
        "uretilen_taslak": uretilen_taslak_obj,
        "nihai_yonlendirme": yonlendirme,
        "kullanici_mesaji": kullanici_mesaji,
        "_meta": {
            "islem_zamani": datetime.now(timezone.utc).isoformat(),
            "retry_count": state.get("retry_count", 0),
            "loopback_count": state.get("loopback_count", 0),
            "hata_log": hata_log,
        },
    }

    # Şema doğrulaması
    gecerli, hata = validate_agent4_output(nihai_cikti)
    if not gecerli:
        logger.warning("[OutputNode] Şema doğrulama hatası: %s", hata)
        hata_log.append(f"[OutputNode] Şema uyarısı: {hata}")

    logger.info(
        "[OutputNode] Nihai çıktı: durum=%s, aksiyon=%s, birim=%s",
        sistem_durumu, sistem_aksiyonu, hedef_birim,
    )

    return {
        "sistem_durumu": sistem_durumu,
        "nihai_cikti": nihai_cikti,
        "hata_log": hata_log,
    }
