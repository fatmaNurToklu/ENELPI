"""
Agent 2 Adaptörü — NER & RAG Mevzuat Eşleştirme
-------------------------------------------------
Gerçek Agent 2 kodunu Agent 4'ün pipeline'ına bağlar.

Strateji:
  1. agent2/ dizinini sys.path'e ekle
  2. ChatOllama'yı lazy init et (import sırasında crash önlenir)
  3. agent2_isle(agent1_json) → sözleşme uyumlu dict döner
  4. ChromaDB/Ollama/ImportError → graceful mock fallback

Kritik sorunlar çözüldü:
  - agent2.py: `llm = ChatOllama(...)` modül seviyesinde → lazy init sarıcısı
  - chromadb path: './chroma_veri' → proje kökü göreceli mutlak path
  - göreceli importlar: `from mevzuat_db import ...` → sys.path eklenince çalışır
"""

import logging
import sys
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

# Agent 2 dizin yolu
_AGENT2_DIR = Path(__file__).resolve().parent.parent.parent / "agent2"

# Lazy-loaded fonksiyonlar
_a2_loaded = False
_bilgi_cikar = None
_mevzuat_ara = None
_eksik_bilgi_tespit = None
_ozetle = None
_cikti_olustur = None
_agent1_girdisini_isle = None


def _try_load_agent2() -> bool:
    """Agent 2 modüllerini lazy olarak yükler. ChromaDB + Ollama bağlantısı olmadan da çalışır."""
    global _a2_loaded, _bilgi_cikar, _mevzuat_ara, _eksik_bilgi_tespit
    global _ozetle, _cikti_olustur, _agent1_girdisini_isle

    if _a2_loaded:
        return True

    if str(_AGENT2_DIR) not in sys.path:
        sys.path.insert(0, str(_AGENT2_DIR))

    # chromadb PersistentClient path'ini agent2/ klasörüne ayarla
    # agent2.py içindeki `chromadb.PersistentClient(path="./chroma_veri")`
    # agent2/ dizininden çalışılıyormuş gibi çözülmesi için cwd geçici değiştiriyoruz
    # Alternatif: monkeypatching (tercih etmiyoruz) — burada import sırası yeterli
    _orijinal_cwd = os.getcwd()
    try:
        os.chdir(str(_AGENT2_DIR))
        import agent2 as _a2_mod  # type: ignore[import]
        _bilgi_cikar          = _a2_mod.bilgi_cikar
        _mevzuat_ara          = _a2_mod.mevzuat_ara
        _eksik_bilgi_tespit   = _a2_mod.eksik_bilgi_tespit
        _ozetle               = _a2_mod.ozetle
        _cikti_olustur        = _a2_mod.cikti_olustur
        _agent1_girdisini_isle = _a2_mod.agent1_girdisini_isle
        _a2_loaded = True
        logger.info("[Agent2Adapter] Gerçek Agent 2 başarıyla yüklendi.")
    except ImportError as e:
        logger.warning("[Agent2Adapter] Agent 2 yüklenemedi (eksik bağımlılık): %s", e)
    except RuntimeError as e:
        # ChromaDB koleksiyonu bulunamadı → chroma_yukle.py çalıştırılmamış
        logger.warning("[Agent2Adapter] ChromaDB hazır değil: %s", e)
    except Exception as e:
        logger.warning("[Agent2Adapter] Agent 2 yüklenemedi: %s", e)
    finally:
        os.chdir(_orijinal_cwd)

    return _a2_loaded


def _mock_agent2_output(agent1_json: Dict[str, Any]) -> Dict[str, Any]:
    """
    Agent 2 kullanılamadığında dönen minimal sözleşme-uyumlu mock çıktı.
    Agent 1 çıktısındaki mevcut alanları mümkün olduğunca yansıtır.
    """
    meta = agent1_json.get("agent1_islem_metadata", {})
    evrak_id = meta.get("evrak_id", "EVR-0000-0000")
    sinif = agent1_json.get("siniflandirma_sonucu", {})
    evrak_turu = sinif.get("evrak_turu", "DIGER")
    on_cik = agent1_json.get("on_cikarimlar", {}) or {}

    # on_cikarimlar → cikartilan_bilgiler (alanlar örtüşüyor)
    cikartilan = {
        "gonderici":      on_cik.get("gonderici"),
        "gonderici_kurum": None,
        "alici_kurum":    on_cik.get("alici_kurum"),
        "konu":           on_cik.get("konu"),
        "tarih":          on_cik.get("tarih"),
        "belge_sayisi":   on_cik.get("belge_sayisi"),
        "tc_kimlik":      on_cik.get("tc_kimlik"),
        "imza_sahibi":    on_cik.get("imza_sahibi"),
        "ekler":          on_cik.get("ekler"),
    }

    manuel_oneri = meta.get("manuel_inceleme_onerisi", False)
    durum = "MANUEL_INCELEME" if manuel_oneri else "TAMAMLANDI"

    return {
        "sema_versiyonu": "1.0",
        "agent2_islem_metadata": {
            "evrak_id": evrak_id,
            "islem_zamani": datetime.now(timezone.utc).isoformat(),
            "durum": durum,
            "manuel_inceleme_onerisi": manuel_oneri,
            "agent1_durum": meta.get("durum", "BASARILI"),
            "agent1_siniflandirma_skoru": sinif.get("siniflandirma_guven_skoru", 0.5),
            "_mock": True,
        },
        "evrak_turu": evrak_turu,
        "cikartilan_bilgiler": cikartilan,
        "ilgili_mevzuat": [],
        "eksik_alanlar": [],
        "ozet": "Evrak analizi tamamlandı (Agent 2 bağımlılıkları kurulu değil, özet atlandı).",
    }


def agent2_calistir(agent1_json: Dict[str, Any]) -> Dict[str, Any]:
    """
    Gerçek Agent 2'yi çalıştırır. Başarısız olursa mock fallback döner.

    Args:
        agent1_json: agent1_agent2_veri_sozlesmesi.md v1.0 şemasına uyumlu dict

    Returns:
        agent2_agent3_veri_sozlesmesi.md v1.0 şemasına uyumlu dict
    """
    if _try_load_agent2():
        _orijinal_cwd = os.getcwd()
        try:
            os.chdir(str(_AGENT2_DIR))

            # Agent 1 girdisini parse et
            metin, evrak_turu, on_cikarimlar = _agent1_girdisini_isle(agent1_json)  # type: ignore[misc]
            if metin is None:
                # BASARISIZ durum — sözleşme §5: doğrudan mock döndür
                logger.warning("[Agent2Adapter] Agent 1 BASARISIZ → fallback")
                return _mock_agent2_output(agent1_json)

            # Bilgi çıkarımı (Agent 1 + Regex + LLM)
            cikartilan = _bilgi_cikar(metin, evrak_turu, on_cikarimlar)  # type: ignore[misc]

            # Mevzuat RAG
            mevzuat: List[Dict] = _mevzuat_ara(  # type: ignore[misc]
                cikartilan.get("konu") or metin[:80],
                evrak_turu,
            )

            # Eksik alan tespiti
            eksikler: List[str] = _eksik_bilgi_tespit(cikartilan, evrak_turu)  # type: ignore[misc]

            # Özetleme
            ozet: str = _ozetle(metin, cikartilan, mevzuat, eksikler)  # type: ignore[misc]

            # Çıktı montajı
            sonuc: Dict[str, Any] = _cikti_olustur(  # type: ignore[misc]
                agent1_json, evrak_turu, cikartilan, mevzuat, eksikler, ozet
            )

            logger.info(
                "[Agent2Adapter] Agent 2 tamamlandı. evrak_id=%s durum=%s",
                sonuc["agent2_islem_metadata"]["evrak_id"],
                sonuc["agent2_islem_metadata"]["durum"],
            )
            return sonuc

        except Exception as e:
            logger.error("[Agent2Adapter] Agent 2 çalışma hatası: %s → mock fallback", e)
        finally:
            os.chdir(_orijinal_cwd)

    logger.warning("[Agent2Adapter] Mock fallback kullanılıyor.")
    return _mock_agent2_output(agent1_json)
