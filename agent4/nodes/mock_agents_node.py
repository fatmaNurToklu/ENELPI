"""
Agent 4 — Mock Agent Stub'ları (Agent 1, 2, 3)
Gerçek entegrasyon yapılana kadar JSON dosyalarından okur.
Sözleşme referansı: agent1_agent2, agent2_agent3, agent3_agent4 veri sözleşmeleri
"""

import json
import os
from datetime import datetime, timezone
from typing import Dict, Any

from agent4.state import AgentState

# Mock çıktı dosyalarının konumu
MOCK_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "tests", "mock_outputs")

# Mock Agent 1 çıktısı — Agent 2'ye gider
MOCK_AGENT1_TEMPLATE = {
    "sema_versiyonu": "1.0",
    "agent1_islem_metadata": {
        "evrak_id": "EVR-2026-0001",
        "islem_zamani": "",
        "kaynak_tipi": "DIJITAL_METIN",
        "sayfa_sayisi": 1,
        "ocr_motoru": None,
        "ocr_guven_skoru": 0.92,
        "durum": "BASARILI",
        "manuel_inceleme_onerisi": False,
    },
    "siniflandirma_sonucu": {
        "evrak_turu": "BILGI_EDINME_BASVURUSU",
        "alt_kategori": None,
        "siniflandirma_guven_skoru": 0.91,
        "alternatif_tahminler": [],
    },
    "metin_icerigi": {
        "ham_metin": None,
        "temizlenmis_metin": "Sayın Yönetim Kurulu, bilgi edinme talebimiz hakkında bilgi almak istiyoruz.",
        "dil": "tr",
    },
    "on_cikarimlar": {
        "tarih_adaylari": ["2026-07-10"],
        "gonderici_adayi": None,
        "konu_adayi": "Bilgi edinme talebi",
    },
}


def _load_mock_agent3(senaryo: str) -> Dict[str, Any]:
    """Senaryo adına göre Agent 3 mock JSON dosyasını yükler."""
    senaryo_map = {
        "TASLAK_HAZIR": "agent3_mock_taslak_hazir.json",
        "EKSIK_BILGI": "agent3_mock_eksik_bilgi.json",
        "MANUEL": "agent3_mock_manuel.json",
        "URETILEMEDI": "agent3_mock_uretilemedi.json",
    }
    dosya_adi = senaryo_map.get(senaryo, "agent3_mock_taslak_hazir.json")
    dosya_yolu = os.path.join(MOCK_DIR, dosya_adi)

    with open(dosya_yolu, encoding="utf-8") as f:
        return json.load(f)


# ─── Node: Agent 1 Mock ───────────────────────────────────────────────────────
def mock_agent1_node(state: AgentState) -> Dict[str, Any]:
    """
    Agent 1 stub: OCR ve sınıflandırma simüle eder.
    Gerçek Agent 1 (Yusuf) entegrasyonunda bu node değiştirilecektir.
    """
    senaryo = state.get("senaryo", "TASLAK_HAZIR")
    mock_data = MOCK_AGENT1_TEMPLATE.copy()
    mock_data["agent1_islem_metadata"] = dict(mock_data["agent1_islem_metadata"])
    mock_data["agent1_islem_metadata"]["evrak_id"] = state["evrak_id"]
    mock_data["agent1_islem_metadata"]["islem_zamani"] = datetime.now(timezone.utc).isoformat()

    # MANUEL senaryosu için OCR güven skoru düşük
    if senaryo == "MANUEL":
        mock_data["agent1_islem_metadata"]["ocr_guven_skoru"] = 0.58
        mock_data["agent1_islem_metadata"]["manuel_inceleme_onerisi"] = True
    elif senaryo == "URETILEMEDI":
        mock_data["siniflandirma_sonucu"]["evrak_turu"] = "SOZLESME_PROTOKOL"

    temizlenmis_metin = mock_data["metin_icerigi"]["temizlenmis_metin"]

    return {
        "agent1_output": mock_data,
        "temizlenmis_metin": temizlenmis_metin,
        "hata_log": state.get("hata_log", []),
    }


# ─── Node: Agent 2 Mock ───────────────────────────────────────────────────────
def mock_agent2_node(state: AgentState) -> Dict[str, Any]:
    """
    Agent 2 stub: NER + RAG mevzuat eşleştirme simüle eder.
    Loopback durumunda (eksik bilgi tamamlandıktan sonra) TAMAMLANDI döndürür.
    Gerçek Agent 2 (Nur) entegrasyonunda bu node değiştirilecektir.
    """
    senaryo = state.get("senaryo", "TASLAK_HAZIR")
    loopback = state.get("loopback_count", 0)

    # Loopback sonrası eksik bilgi tamamlandı → TAMAMLANDI döndür
    if loopback > 0:
        senaryo_for_agent2 = "TASLAK_HAZIR"
    else:
        senaryo_for_agent2 = senaryo

    mock_agent3_data = _load_mock_agent3(senaryo_for_agent2)
    agent2_data = mock_agent3_data.get("_mock_agent2", {})

    # Metadata ekle
    agent2_output = {
        "sema_versiyonu": "1.0",
        "agent2_islem_metadata": {
            "evrak_id": state["evrak_id"],
            "islem_zamani": datetime.now(timezone.utc).isoformat(),
            "durum": "EKSIK_BILGI" if (senaryo == "EKSIK_BILGI" and loopback == 0)
                     else "MANUEL_INCELEME" if senaryo == "MANUEL"
                     else "TAMAMLANDI",
            "manuel_inceleme_onerisi": senaryo == "MANUEL",
            "agent1_durum": "BASARILI",
            "agent1_siniflandirma_skoru": 0.91,
        },
        **agent2_data,
    }

    return {
        "agent2_output": agent2_output,
        "hata_log": state.get("hata_log", []),
    }


# ─── Node: Agent 3 Mock ───────────────────────────────────────────────────────
def mock_agent3_node(state: AgentState) -> Dict[str, Any]:
    """
    Agent 3 stub: Slot-filling taslak üretimi simüle eder.
    retry_count > 0 ise TASLAK_HAZIR döndürür (yeniden deneme başarılı varsayımı).
    Gerçek Agent 3 (Can) entegrasyonunda bu node değiştirilecektir.
    """
    senaryo = state.get("senaryo", "TASLAK_HAZIR")
    retry_count = state.get("retry_count", 0)
    loopback_count = state.get("loopback_count", 0)

    # Retry veya loopback durumunda başarı varsayımı
    effective_senaryo = senaryo
    if retry_count > 0 or loopback_count > 0:
        effective_senaryo = "TASLAK_HAZIR"

    mock_data = _load_mock_agent3(effective_senaryo)
    mock_data["evrak_id"] = state["evrak_id"]

    # Retry ise temperature artırıldı (simülasyon notu)
    hata_log = list(state.get("hata_log", []))
    if retry_count > 0:
        hata_log.append(
            f"[Agent3] Yeniden deneme #{retry_count} — temperature artırıldı. Taslak başarıyla üretildi."
        )

    return {
        "agent3_output": mock_data,
        "hata_log": hata_log,
    }
