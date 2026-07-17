"""
Agent 4 — LangGraph Orkestrasyon Grafiği
Tüm pipeline'ı yöneten StateGraph tanımı ve conditional edges.
Sözleşme referansı: agent4_orkestrasyon_sozlesmesi.md §5
"""

import logging
from typing import Literal

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from agent4.state import AgentState, MAX_RETRY
from agent4.nodes.mock_agents_node import mock_agent1_node, mock_agent2_node, mock_agent3_node
from agent4.nodes.real_agents_node import real_agent1_node, real_agent2_node, real_agent3_node
from agent4.nodes.routing_node import routing_node
from agent4.nodes.human_loop_node import request_missing_info_node, human_approval_node
from agent4.nodes.output_node import output_node

logger = logging.getLogger(__name__)


# ─── Koşullu Yönlendirme Fonksiyonları ───────────────────────────────────────

def after_agent1_router(state: AgentState) -> Literal["agent2", "output"]:
    """
    Agent 1 sonrası yönlendirme.
    Sözleşme §5: agent1_output.durum == 'BASARISIZ' → KRITIK_HATA_MANUEL_KUYRUK
    """
    agent1 = state.get("agent1_output") or {}
    meta = agent1.get("agent1_islem_metadata", {}) or {}
    durum = meta.get("durum", "BASARILI")

    if durum == "BASARISIZ":
        logger.warning("[Router] Agent1 BASARISIZ → output (kritik hata)")
        return "output"  # Doğrudan output → KRITIK_HATA

    return "agent2"


def after_agent3_router(
    state: AgentState,
) -> Literal["routing", "missing_info", "retry_agent3", "output"]:
    """
    Agent 3 sonrası ana yönlendirme kararı.
    Sözleşme §5 karar matrisi birebir uygulanmıştır.
    """
    agent3 = state.get("agent3_output") or {}
    durum = agent3.get("durum", "")
    retry_count = state.get("retry_count", 0)

    # ── URETILEMEDI + retry < MAX_RETRY → yeniden dene ────────────────────────
    if durum == "URETILEMEDI" and retry_count < MAX_RETRY:
        logger.info("[Router] URETILEMEDI — retry #%d başlatılıyor.", retry_count + 1)
        return "retry_agent3"

    # ── URETILEMEDI + retry >= MAX_RETRY → kritik hata ────────────────────────
    if durum == "URETILEMEDI" and retry_count >= MAX_RETRY:
        logger.warning("[Router] URETILEMEDI — max retry aşıldı. Kritik hata.")
        return "output"

    # ── Eksik bilgi → interrupt döngüsü ──────────────────────────────────────
    if durum == "TASLAK_HAZIR_EKSIK_BILGI":
        logger.info("[Router] EKSIK_BILGI → missing_info interrupt")
        return "missing_info"

    # ── Taslak Hazır (Normal, Manuel İnceleme veya Üslup Uyarılı) ─────────────
    # Hepsi için önce yönlendirme kararı üretilsin (routing düğümü)
    if durum in ["TASLAK_HAZIR", "TASLAK_HAZIR_MANUEL_INCELEME_UYARILI"]:
        logger.info("[Router] Taslak hazır (%s) → Önce yönlendirme (routing)", durum)
        return "routing"

    # ── Bilinmeyen durum → kritik hata ────────────────────────────────────────
    logger.error("[Router] Bilinmeyen agent3 durumu: %s", durum)
    return "output"


def after_routing_router(
    state: AgentState,
) -> Literal["human_approval", "output"]:
    """
    Yönlendirme kararı üretildikten sonra insan onayı gerekip gerekmediğini denetler.
    """
    agent1 = state.get("agent1_output") or {}
    meta = agent1.get("agent1_islem_metadata", {}) or {}
    ocr_guven = meta.get("ocr_guven_skoru", 1.0) or 1.0

    agent3 = state.get("agent3_output") or {}
    taslak = agent3.get("uretilen_taslak", {}) or {}
    uslup = taslak.get("resmi_uslup_kontrolu", {}) or {}
    durum = agent3.get("durum", "")

    # ── Üslup ihlali → insan onayı (sözleşme §5 notu) ─────────────────────────
    if not uslup.get("uygun_mu", True):
        logger.info("[Router] Üslup ihlali tespit edildi → human_approval")
        return "human_approval"

    # ── Manuel inceleme uyarılı → insan onayı ─────────────────────────────────
    if durum == "TASLAK_HAZIR_MANUEL_INCELEME_UYARILI":
        logger.info("[Router] MANUEL_INCELEME_UYARILI → human_approval")
        return "human_approval"

    # ── Düşük OCR güven skoru (< 0.70) → insan onayı ─────────────────────────
    if ocr_guven < 0.70:
        logger.info("[Router] Düşük OCR güven skoru (%.2f) → human_approval", ocr_guven)
        return "human_approval"

    # ── Normal durum → doğrudan çıktı ─────────────────────────────────────────
    logger.info("[Router] Otomatik onaylanabilir → output")
    return "output"


def retry_router(state: AgentState) -> Literal["agent3"]:
    """Retry node'u Agent 3'e geri döner (retry_count artırılarak)."""
    return "agent3"


def after_missing_info_router(
    state: AgentState,
) -> Literal["agent2", "output"]:
    """
    Eksik bilgi tamamlandıktan sonra:
    - Kritik hata sinyali varsa → output
    - Normal ise Agent 2'ye geri besleme (loopback)
    """
    sistem_durumu = state.get("sistem_durumu", "")
    if sistem_durumu == "KRITIK_HATA_MANUEL_KUYRUK":
        return "output"
    return "agent2"  # Agent 2 → Agent 3 → tekrar değerlendirme


# ─── Retry Node ──────────────────────────────────────────────────────────────
def retry_agent3_node(state: AgentState):
    """
    Agent 3'ü yeniden denemek için retry sayacını artırır.
    Sıcaklık (temperature) artırımı mock_agent3_node içinde simüle edilir.
    """
    return {"retry_count": state.get("retry_count", 0) + 1}


# ─── Graf Kurulumu ────────────────────────────────────────────────────────────
def build_graph(use_memory: bool = True, use_real_agents: bool = False) -> StateGraph:
    """
    LangGraph StateGraph'i oluşturur ve derler.

    Args:
        use_memory: True ise MemorySaver kullanılır (interrupt için zorunlu)
        use_real_agents: True ise gerçek Agent 1/2/3 kullanılır;
                         False ise mock JSON tabanlı demo modu (varsayılan)

    Returns:
        Derlenmiş (compiled) LangGraph grafiği
    """
    # Node seçimi — gerçek veya mock
    agent1_node = real_agent1_node if use_real_agents else mock_agent1_node
    agent2_node = real_agent2_node if use_real_agents else mock_agent2_node
    agent3_node = real_agent3_node if use_real_agents else mock_agent3_node
    logger.info(
        "[Graph] Pipeline modu: %s",
        "GERCEK (Agent1/2/3)" if use_real_agents else "DEMO (Mock)",
    )
    builder = StateGraph(AgentState)

    # ─── Node'ları ekle ────────────────────────────────────────────────────────
    builder.add_node("agent1",        agent1_node)
    builder.add_node("agent2",        agent2_node)
    builder.add_node("agent3",        agent3_node)
    builder.add_node("routing",       routing_node)
    builder.add_node("missing_info",  request_missing_info_node)
    builder.add_node("human_approval", human_approval_node)
    builder.add_node("retry_agent3",  retry_agent3_node)
    builder.add_node("output",        output_node)

    # ─── Kenarları ekle ───────────────────────────────────────────────────────
    # Başlangıç
    builder.add_edge(START, "agent1")

    # Agent 1 sonrası
    builder.add_conditional_edges(
        "agent1",
        after_agent1_router,
        {"agent2": "agent2", "output": "output"},
    )

    # Agent 2 → Agent 3 (doğrudan)
    builder.add_edge("agent2", "agent3")

    # Agent 3 sonrası — ana karar noktası
    builder.add_conditional_edges(
        "agent3",
        after_agent3_router,
        {
            "routing":       "routing",
            "missing_info":  "missing_info",
            "retry_agent3":  "retry_agent3",
            "output":        "output",
        },
    )

    # Yönlendirme sonrası — İnsan onayı gerekip gerekmediğini denetle
    builder.add_conditional_edges(
        "routing",
        after_routing_router,
        {
            "human_approval": "human_approval",
            "output":        "output",
        },
    )

    # Retry → Agent 3
    builder.add_edge("retry_agent3", "agent3")

    # Eksik bilgi → Agent 2 loopback veya output
    builder.add_conditional_edges(
        "missing_info",
        after_missing_info_router,
        {"agent2": "agent2", "output": "output"},
    )

    # İnsan onayı → Çıktı
    builder.add_edge("human_approval", "output")

    # Bitiş
    builder.add_edge("output", END)

    # ─── Derleme ──────────────────────────────────────────────────────────────
    checkpointer = MemorySaver() if use_memory else None
    graph = builder.compile(checkpointer=checkpointer)

    logger.info(
        "[Graph] LangGraph grafiği derlendi. MemorySaver: %s | Gerçek Ajanlar: %s",
        use_memory, use_real_agents,
    )
    return graph


# Varsayılan graf örneği (Gradio için paylaşımlı)
_compiled_graph = None


def get_graph() -> StateGraph:
    """Singleton pattern — sadece bir kez derlenir."""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph(use_memory=True)
    return _compiled_graph


def create_initial_state(
    evrak_id: str,
    senaryo: str,
    dosya_yolu: str | None = None,
    pipeline_modu: str = "DEMO",
) -> AgentState:
    """Başlangıç AgentState nesnesi oluşturur."""
    return AgentState(
        evrak_id=evrak_id,
        ham_metin=None,
        temizlenmis_metin=None,
        agent1_output=None,
        agent2_output=None,
        agent3_output=None,
        retry_count=0,
        loopback_count=0,
        eksik_alanlar_gecmisi=[],
        nihai_yonlendirme=None,
        sistem_durumu="",
        nihai_cikti=None,
        hata_log=[],
        senaryo=senaryo,
        pipeline_modu=pipeline_modu,
        dosya_yolu=dosya_yolu,
    )
