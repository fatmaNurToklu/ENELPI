"""
Agent 4 — Merkezi Durum Tanımı (State Definition)
Sözleşme referansı: agent4_orkestrasyon_sozlesmesi.md §2
"""

from typing import TypedDict, List, Optional, Dict, Any

# ─── Orkestrasyon Sabitleri ────────────────────────────────────────────────────
MAX_RETRY = 2          # Agent 3 için maksimum yeniden deneme sayısı
MAX_LOOPBACK = 3       # Eksik bilgi döngüsü için maksimum geri besleme sayısı

# Ollama model: gemma3:4b is installed on the local system
OLLAMA_MODEL = "gemma3:4b"
OLLAMA_BASE_URL = "http://localhost:11434"

# ─── Yönlendirme Birimleri ────────────────────────────────────────────────────
# agent4_orkestrasyon_sozlesmesi.md §4 — 6 sabit birim + belirsiz durumu
HEDEF_BIRIMLER = [
    "INSAN_KAYNAKLARI",
    "BILGI_ISLEM",
    "HUKUK_MUSAVIRLIGI",
    "YAZI_ISLERI",
    "DESTEK_HIZMETLERI",
    "STRATEJI_GELISTIRME",
    "MANUEL_BELIRSIZ",
]

# ─── Sistem Durumları ─────────────────────────────────────────────────────────
SISTEM_DURUMLARI = [
    "OTOMATIK_ONAYLANABILIR",
    "INSAN_ONAYI_BEKLIYOR",
    "EKSIK_BILGI_TALEBI",
    "KRITIK_HATA_MANUEL_KUYRUK",
]

# ─── Pipeline Modları ─────────────────────────────────────────────────────────
PIPELINE_MODU_DEMO   = "DEMO"    # Mock JSON ile senaryo tabanlı demo
PIPELINE_MODU_GERCEK = "GERCEK"  # Gerçek Agent 1/2/3 ile dosya tabanlı pipeline

# ─── LangGraph AgentState ────────────────────────────────────────────────────
class AgentState(TypedDict):
    """
    Tüm multi-agent pipeline boyunca taşınan merkezi durum nesnesi.
    Her alan agent4_orkestrasyon_sozlesmesi.md §2'deki sözleşmeyle uyumludur.
    """

    # Temel Evrak Bilgileri
    evrak_id: str                           # Format: EVR-YYYY-XXXX
    ham_metin: Optional[str]                # OCR öncesi ham metin (hata ayıklama)
    temizlenmis_metin: Optional[str]        # Agent 1'den gelen temiz metin

    # Ajan Girdi/Çıktı Blokları (Sözleşme Nesneleri)
    agent1_output: Optional[Dict[str, Any]]  # agent1_agent2_veri_sozlesmesi şeması
    agent2_output: Optional[Dict[str, Any]]  # agent2_agent3_veri_sozlesmesi şeması
    agent3_output: Optional[Dict[str, Any]]  # agent3_agent4_veri_sozlesmesi şeması

    # Orkestrasyon Kontrol Metrikleri
    retry_count: int                        # Agent 3 için yeniden deneme sayısı (maks: MAX_RETRY)
    loopback_count: int                     # Eksik bilgi geri besleme sayısı (maks: MAX_LOOPBACK)
    eksik_alanlar_gecmisi: List[str]        # Kullanıcıdan tamamlanan eksik alanların takibi

    # Nihai Karar ve Sistem Çıktıları
    nihai_yonlendirme: Optional[Dict[str, Any]]  # Hedef birim, gerekçe, güven skoru
    sistem_durumu: str                       # Bkz. SISTEM_DURUMLARI listesi
    nihai_cikti: Optional[Dict[str, Any]]    # Agent4_Nihai_Cikti_Semasi_v1 JSON çıktısı

    # Hata & İzlenebilirlik
    hata_log: List[str]                      # Pipeline boyunca toplanan hata ve uyarı mesajları

    # Demo/Gerçek pipeline kontrolü
    senaryo: Optional[str]                   # Demo için senaryo adı (gerçek sistemde None)
    pipeline_modu: Optional[str]             # "DEMO" | "GERCEK" — bkz. PIPELINE_MODU_* sabitleri
    dosya_yolu: Optional[str]                # Gerçek modda yüklenen evrak dosyasının yolu (PDF/JPG/PNG)
