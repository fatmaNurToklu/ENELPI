"""
Agent 3 Adaptörü — Slot-Filling Resmi Yazı Taslaklama
------------------------------------------------------
Gerçek Agent 3 kodunu Agent 4'ün pipeline'ına bağlar.

Strateji:
  1. agent3/ dizinini sys.path'e ekle
  2. taslak_uret() lazy import et (LLM modül seviyesinde init'i önle)
  3. taslak_uret(agent2_cikti) → sözleşme v1.0 uyumlu dict döner
  4. Ollama/ImportError → graceful mock fallback

Agent 3 zaten iyi tasarlanmış — taslak_uret() wrapper fonksiyon.
Ana sorun: `llm = ChatOllama(...)` agent3.py'de modül seviyesinde init.
Bu adaptör, agent3'ü cwd değiştirip import ederek çözer.
"""

import logging
import sys
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

# Agent 3 dizin yolu
_AGENT3_DIR = Path(__file__).resolve().parent.parent.parent / "agent3"

# Lazy-loaded fonksiyon
_a3_loaded = False
_taslak_uret = None


def _try_load_agent3() -> bool:
    """Agent 3 modülünü lazy olarak yükler."""
    global _a3_loaded, _taslak_uret

    if _a3_loaded:
        return True

    if str(_AGENT3_DIR) not in sys.path:
        sys.path.insert(0, str(_AGENT3_DIR))

    _orijinal_cwd = os.getcwd()
    try:
        os.chdir(str(_AGENT3_DIR))
        from agent3 import taslak_uret  # type: ignore[import]
        _taslak_uret = taslak_uret
        _a3_loaded = True
        logger.info("[Agent3Adapter] Gerçek Agent 3 başarıyla yüklendi.")
    except ImportError as e:
        logger.warning("[Agent3Adapter] Agent 3 yüklenemedi (eksik bağımlılık): %s", e)
    except Exception as e:
        logger.warning("[Agent3Adapter] Agent 3 yüklenemedi: %s", e)
    finally:
        os.chdir(_orijinal_cwd)

    return _a3_loaded


def _mock_agent3_output(agent2_cikti: Dict[str, Any]) -> Dict[str, Any]:
    """
    Agent 3 kullanılamadığında dönen minimal sözleşme-uyumlu mock çıktı.
    agent3_agent4_veri_sozlesmesi.md v1.0 şeması.
    """
    meta = agent2_cikti.get("agent2_islem_metadata", {})
    evrak_id  = meta.get("evrak_id", "EVR-0000-0000")
    evrak_turu = agent2_cikti.get("evrak_turu", "DIGER")
    a2_durum  = meta.get("durum", "TAMAMLANDI")
    eksikler: List[str] = agent2_cikti.get("eksik_alanlar", [])
    cikartilan = agent2_cikti.get("cikartilan_bilgiler", {}) or {}

    # Basit bir taslak metni oluştur
    gonderici = cikartilan.get("gonderici") or "İlgili"
    konu = cikartilan.get("konu") or "(konu belirtilmemiş)"
    hitap = f"Sayın {gonderici}," if gonderici != "İlgili" else "Sayın İlgili,"

    eksik_blok = ""
    if eksikler:
        satirlar = "\n".join(f"[BİLGİ EKSİK: {a}]" for a in eksikler)
        eksik_blok = f"\n\nBaşvurunuzun işleme alınabilmesi için aşağıdaki bilgilerin tarafımıza iletilmesi gerekmektedir:\n{satirlar}"

    taslak_metni = (
        f"{hitap}\n\n"
        f"{konu} konulu başvurunuz tarafımızca değerlendirilmeye alınmıştır. "
        f"Başvurunuz en kısa sürede sonuçlandırılacaktır."
        f"{eksik_blok}\n\nSaygılarımızla,"
    )

    # durum haritası (Agent 3 sözleşmesi §3)
    durum_harita = {
        "TAMAMLANDI":       "TASLAK_HAZIR",
        "EKSIK_BILGI":      "TASLAK_HAZIR_EKSIK_BILGI",
        "MANUEL_INCELEME":  "TASLAK_HAZIR_MANUEL_INCELEME_UYARILI",
    }
    durum = durum_harita.get(a2_durum, "TASLAK_HAZIR")

    return {
        "sema_versiyonu": "1.0",
        "evrak_id": evrak_id,
        "kaynak_baglam": {
            "evrak_turu": evrak_turu,
            "agent2_durum": a2_durum,
            "eksik_alanlar": eksikler,
            "mevzuat_sayisi": len(agent2_cikti.get("ilgili_mevzuat", [])),
        },
        "uretilen_taslak": {
            "sablon_turu": "GENEL_AMACLI",
            "taslak_metni": taslak_metni,
            "eksik_alan_yer_tutucular": list(eksikler),
            "resmi_uslup_kontrolu": {
                "uygun_mu": True,
                "tespit_edilen_sorunlar": [],
                "_mock": True,
            },
        },
        "durum": durum,
    }


def agent3_calistir(agent2_cikti: Dict[str, Any]) -> Dict[str, Any]:
    """
    Gerçek Agent 3'ü çalıştırır. Başarısız olursa mock fallback döner.

    Args:
        agent2_cikti: agent2_agent3_veri_sozlesmesi.md v1.0 şemasına uyumlu dict

    Returns:
        agent3_agent4_veri_sozlesmesi.md v1.0 şemasına uyumlu dict
    """
    if _try_load_agent3() and _taslak_uret is not None:
        _orijinal_cwd = os.getcwd()
        try:
            os.chdir(str(_AGENT3_DIR))
            logger.info(
                "[Agent3Adapter] Gerçek Agent 3 çalıştırılıyor. evrak_id=%s",
                agent2_cikti.get("agent2_islem_metadata", {}).get("evrak_id"),
            )
            sonuc = _taslak_uret(agent2_cikti)  # type: ignore[misc]
            durum = sonuc.get("durum", "?")
            logger.info("[Agent3Adapter] Agent 3 tamamlandı. durum=%s", durum)
            return sonuc
        except Exception as e:
            logger.error("[Agent3Adapter] Agent 3 çalışma hatası: %s → mock fallback", e)
        finally:
            os.chdir(_orijinal_cwd)

    logger.warning("[Agent3Adapter] Mock fallback kullanılıyor.")
    return _mock_agent3_output(agent2_cikti)
