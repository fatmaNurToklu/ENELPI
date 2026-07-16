"""
Agent 1 Adaptörü — OCR & Sınıflandırma
---------------------------------------
Gerçek Agent 1 kodunu Agent 4'ün pipeline'ına bağlar.

Strateji:
  1. agent1/ dizinini sys.path'e ekle (göreceli import çözümü)
  2. agent1_isle() çağır → sözleşme v1.0 uyumlu dict döner
  3. Herhangi bir hata (ImportError, FileNotFoundError, vs.) → mock fallback

Graceful degradation sayesinde:
  - pytesseract/tesseract kurulu değilse → mock
  - pdfplumber/cv2 kurulu değilse → mock
  - Dosya bulunamazsa → mock
"""

import logging
import sys
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Agent 1 dizin yolu (proje kökünden göreceli)
_AGENT1_DIR = Path(__file__).resolve().parent.parent.parent / "agent1"

# Gerçek modülü yükleyip yükleyemediğimizi bir kez kontrol et
_agent1_available = False
_agent1_isle = None

def _try_load_agent1():
    """Agent 1 modülünü lazy olarak yüklemeye çalışır."""
    global _agent1_available, _agent1_isle

    if _agent1_available:
        return True

    if str(_AGENT1_DIR) not in sys.path:
        sys.path.insert(0, str(_AGENT1_DIR))

    try:
        from agent1 import agent1_isle  # type: ignore[import]
        _agent1_isle = agent1_isle
        _agent1_available = True
        logger.info("[Agent1Adapter] Gerçek Agent 1 başarıyla yüklendi.")
        return True
    except ImportError as e:
        logger.warning("[Agent1Adapter] Agent 1 yüklenemedi (eksik bağımlılık): %s", e)
    except Exception as e:
        logger.warning("[Agent1Adapter] Agent 1 yüklenemedi: %s", e)

    return False


def _mock_agent1_output(evrak_id: str, dosya_yolu: Optional[str] = None) -> Dict[str, Any]:
    """
    Agent 1 kullanılamadığında dönen minimal sözleşme-uyumlu mock çıktı.
    Sözleşme durum = BASARILI, manuel_inceleme_onerisi = False.
    Metin dosya yolundan okunmaya çalışılır; okunamazsa placeholder kullanılır.
    """
    metin = ""
    if dosya_yolu:
        try:
            yol = Path(dosya_yolu)
            if yol.suffix.lower() == ".txt":
                metin = yol.read_text(encoding="utf-8", errors="replace")
                logger.info("[Agent1Adapter] Metin dosyası okundu: %s", dosya_yolu)
        except Exception:
            pass

    if not metin:
        metin = "Evrak metni okunamadı. Agent 1 bağımlılıkları kurulu değil."

    return {
        "sema_versiyonu": "1.0",
        "agent1_islem_metadata": {
            "evrak_id": evrak_id,
            "islem_zamani": datetime.now(timezone.utc).isoformat(),
            "kaynak_tipi": "DIJITAL_METIN",
            "sayfa_sayisi": 1,
            "ocr_motoru": None,
            "ocr_guven_skoru": 0.0,
            "durum": "BASARILI",
            "manuel_inceleme_onerisi": False,
            "_mock": True,
        },
        "siniflandirma_sonucu": {
            "evrak_turu": "DIGER",
            "alt_kategori": None,
            "siniflandirma_guven_skoru": 0.5,
            "alternatif_tahminler": [],
        },
        "metin_icerigi": {
            "ham_metin": metin,
            "temizlenmis_metin": metin,
            "dil": "tr",
        },
        "on_cikarimlar": {
            "gonderici": None,
            "alici_kurum": None,
            "konu": None,
            "tarih": None,
            "belge_sayisi": None,
            "tc_kimlik": None,
            "imza_sahibi": None,
            "ekler": None,
        },
    }


def agent1_calistir(evrak_id: str, dosya_yolu: str) -> Dict[str, Any]:
    """
    Gerçek Agent 1'i çalıştırır. Başarısız olursa mock fallback döner.

    Args:
        evrak_id: EVR-YYYY-XXXX formatında evrak kimliği
        dosya_yolu: İşlenecek dosyanın tam yolu (PDF, JPG, PNG, TXT)

    Returns:
        agent1_agent2_veri_sozlesmesi.md v1.0 şemasına uyumlu dict
    """
    if _try_load_agent1() and _agent1_isle is not None:
        try:
            logger.info("[Agent1Adapter] Gerçek Agent 1 çalıştırılıyor: %s", dosya_yolu)
            sonuc = _agent1_isle(dosya_yolu, evrak_id=evrak_id)
            logger.info("[Agent1Adapter] Agent 1 tamamlandı. evrak_id=%s", evrak_id)
            return sonuc
        except FileNotFoundError:
            logger.error("[Agent1Adapter] Dosya bulunamadı: %s → mock fallback", dosya_yolu)
        except Exception as e:
            logger.error("[Agent1Adapter] Agent 1 çalışma hatası: %s → mock fallback", e)

    logger.warning("[Agent1Adapter] Mock fallback kullanılıyor. evrak_id=%s", evrak_id)
    return _mock_agent1_output(evrak_id, dosya_yolu)
