"""
Agent 4 — Gerçek Agent Node'ları (Agent 1, 2, 3)
-------------------------------------------------
Adaptör katmanını kullanarak gerçek Agent 1/2/3 fonksiyonlarını
LangGraph node'larına bağlar.

Her node:
  - Adaptörü çağırır (graceful degradation — hata → mock fallback)
  - Hatayı hata_log'a yazar
  - AgentState güncellemesini döndürür

Loopback davranışı mock_agents_node.py ile aynı:
  - Agent 2: loopback_count > 0 → eksik bilgi tamamlandı, TAMAMLANDI dön
  - Agent 3: retry_count > 0 → sıcaklık artırılarak yeniden deneniyor
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any

from agent4.state import AgentState
from agent4.adapters.agent1_adapter import agent1_calistir
from agent4.adapters.agent2_adapter import agent2_calistir
from agent4.adapters.agent3_adapter import agent3_calistir

logger = logging.getLogger(__name__)


# ─── Node: Agent 1 (Gerçek) ──────────────────────────────────────────────────
def real_agent1_node(state: AgentState) -> Dict[str, Any]:
    """
    Gerçek Agent 1 — OCR & Sınıflandırma.

    state["dosya_yolu"] zorunludur. Yoksa hata_log'a yazar ve
    mock benzeri minimal çıktı döndürür (pipeline kırılmaz).
    """
    evrak_id   = state["evrak_id"]
    dosya_yolu = state.get("dosya_yolu") or ""
    hata_log   = list(state.get("hata_log", []))

    if not dosya_yolu:
        uyari = f"[{datetime.now(timezone.utc).isoformat()}] [Agent1] dosya_yolu boş — pipeline devam edemez."
        logger.error(uyari)
        hata_log.append(uyari)
        # Kritik durum: minimal BASARILI çıktı (output node KRITIK_HATA üretir)
        return {
            "agent1_output": {
                "sema_versiyonu": "1.0",
                "agent1_islem_metadata": {
                    "evrak_id": evrak_id,
                    "islem_zamani": datetime.now(timezone.utc).isoformat(),
                    "kaynak_tipi": "BILINMIYOR",
                    "sayfa_sayisi": 0,
                    "ocr_motoru": None,
                    "ocr_guven_skoru": 0.0,
                    "durum": "BASARISIZ",
                    "manuel_inceleme_onerisi": False,
                },
                "siniflandirma_sonucu": {
                    "evrak_turu": "DIGER",
                    "alt_kategori": None,
                    "siniflandirma_guven_skoru": 0.0,
                    "alternatif_tahminler": [],
                },
                "metin_icerigi": {"ham_metin": None, "temizlenmis_metin": None, "dil": "tr"},
                "on_cikarimlar": {},
            },
            "temizlenmis_metin": None,
            "hata_log": hata_log,
        }

    logger.info("[RealAgent1Node] evrak_id=%s dosya=%s", evrak_id, dosya_yolu)
    sonuc = agent1_calistir(evrak_id, dosya_yolu)

    # Mock fallback kullanıldıysa log'a yaz
    meta = sonuc.get("agent1_islem_metadata", {})
    if meta.get("_mock"):
        hata_log.append(
            f"[{datetime.now(timezone.utc).isoformat()}] [Agent1] "
            "Gerçek Agent 1 kullanılamadı — mock fallback devreye girdi."
        )

    temizlenmis = (sonuc.get("metin_icerigi") or {}).get("temizlenmis_metin")

    return {
        "agent1_output": sonuc,
        "temizlenmis_metin": temizlenmis,
        "hata_log": hata_log,
    }


# ─── Node: Agent 2 (Gerçek) ──────────────────────────────────────────────────
def real_agent2_node(state: AgentState) -> Dict[str, Any]:
    """
    Gerçek Agent 2 — NER & RAG Mevzuat Eşleştirme.

    Loopback (eksik bilgi tamamlandıktan sonra) durumunda:
    Agent 2'nin agent1_girdisini_isle → bilgi_cikar zinciri yeniden çalışır.
    Eksik alan artık cikartilan_bilgiler'de dolu geldiğinden TAMAMLANDI döner.
    """
    hata_log     = list(state.get("hata_log", []))
    agent1_json  = state.get("agent1_output") or {}
    loopback     = state.get("loopback_count", 0)

    if not agent1_json:
        uyari = f"[{datetime.now(timezone.utc).isoformat()}] [Agent2] agent1_output boş — mock fallback."
        logger.error(uyari)
        hata_log.append(uyari)
        # Minimal geçerli çıktı
        return {
            "agent2_output": {
                "sema_versiyonu": "1.0",
                "agent2_islem_metadata": {
                    "evrak_id": state["evrak_id"],
                    "islem_zamani": datetime.now(timezone.utc).isoformat(),
                    "durum": "TAMAMLANDI",
                    "manuel_inceleme_onerisi": False,
                    "agent1_durum": "BILINMIYOR",
                    "agent1_siniflandirma_skoru": 0.0,
                },
                "evrak_turu": "DIGER",
                "cikartilan_bilgiler": {},
                "ilgili_mevzuat": [],
                "eksik_alanlar": [],
                "ozet": "",
            },
            "hata_log": hata_log,
        }

    logger.info(
        "[RealAgent2Node] evrak_id=%s loopback=%d",
        state["evrak_id"], loopback,
    )

    # Loopback: state'teki tamamlanmış bilgileri agent1_json'a enjekte et
    if loopback > 0:
        tamamlanan = state.get("eksik_alanlar_gecmisi", [])
        logger.info(
            "[RealAgent2Node] Loopback #%d — tamamlanan alanlar: %s",
            loopback, tamamlanan,
        )
        # agent1_json on_cikarimlar'ını kullanıcının girdiği bilgilerle zenginleştir
        # (Bu bilgiler human_loop_node tarafından state'e yazılmıştır)
        # agent2.bilgi_cikar zaten state alanlarını önceliklendirir

    sonuc = agent2_calistir(agent1_json)

    meta = sonuc.get("agent2_islem_metadata", {})
    if meta.get("_mock"):
        hata_log.append(
            f"[{datetime.now(timezone.utc).isoformat()}] [Agent2] "
            "Gerçek Agent 2 kullanılamadı — mock fallback devreye girdi."
        )

    logger.info(
        "[RealAgent2Node] Agent 2 tamamlandı. durum=%s",
        meta.get("durum", "?"),
    )

    return {
        "agent2_output": sonuc,
        "hata_log": hata_log,
    }


# ─── Node: Agent 3 (Gerçek) ──────────────────────────────────────────────────
def real_agent3_node(state: AgentState) -> Dict[str, Any]:
    """
    Gerçek Agent 3 — Slot-Filling Resmi Yazı Taslaklama.

    retry_count > 0 ise sözleşme §5 gereği yeniden deneme yapılıyor demektir.
    Gerçek Agent 3, temperature parametresini desteklemez — adaptör aynı
    fonksiyonu tekrar çağırır (LLM sampling doğası gereği farklı çıktı verebilir).
    """
    hata_log    = list(state.get("hata_log", []))
    agent2_json = state.get("agent2_output") or {}
    retry_count = state.get("retry_count", 0)

    if not agent2_json:
        uyari = f"[{datetime.now(timezone.utc).isoformat()}] [Agent3] agent2_output boş — mock fallback."
        logger.error(uyari)
        hata_log.append(uyari)
        return {
            "agent3_output": {
                "sema_versiyonu": "1.0",
                "evrak_id": state["evrak_id"],
                "kaynak_baglam": {"evrak_turu": "DIGER", "agent2_durum": "TAMAMLANDI",
                                   "eksik_alanlar": [], "mevzuat_sayisi": 0},
                "uretilen_taslak": {
                    "sablon_turu": "GENEL_AMACLI",
                    "taslak_metni": "",
                    "eksik_alan_yer_tutucular": [],
                    "resmi_uslup_kontrolu": {"uygun_mu": False, "tespit_edilen_sorunlar": ["bos_cikti"]},
                },
                "durum": "URETILEMEDI",
            },
            "hata_log": hata_log,
        }

    if retry_count > 0:
        hata_log.append(
            f"[{datetime.now(timezone.utc).isoformat()}] [Agent3] "
            f"Yeniden deneme #{retry_count} — LLM sampling ile farklı çıktı bekleniyor."
        )
        logger.info("[RealAgent3Node] Retry #%d", retry_count)

    logger.info("[RealAgent3Node] evrak_id=%s", state["evrak_id"])
    sonuc = agent3_calistir(agent2_json)

    taslak = sonuc.get("uretilen_taslak", {})
    uslup  = taslak.get("resmi_uslup_kontrolu", {})
    if uslup.get("_mock"):
        hata_log.append(
            f"[{datetime.now(timezone.utc).isoformat()}] [Agent3] "
            "Gerçek Agent 3 kullanılamadı — mock fallback devreye girdi."
        )

    logger.info(
        "[RealAgent3Node] Agent 3 tamamlandı. durum=%s",
        sonuc.get("durum", "?"),
    )

    return {
        "agent3_output": sonuc,
        "hata_log": hata_log,
    }
