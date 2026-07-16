"""
Agent 4 — Birim Yönlendirme Node'u
Few-Shot Prompting + Ollama Structured Output kullanır.
Sözleşme referansı: agent4_orkestrasyon_sozlesmesi.md §4
"""

import json
import re
import logging
from typing import Dict, Any

from agent4.state import AgentState, OLLAMA_MODEL, OLLAMA_BASE_URL, HEDEF_BIRIMLER
from agent4.prompts.routing_prompt import build_few_shot_messages

logger = logging.getLogger(__name__)


def _extract_json_from_text(text: str) -> Dict[str, Any]:
    """Model çıktısından JSON bloğu ayrıştırır. Markdown kod bloğunu da destekler."""
    # ```json ... ``` bloğu ara
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        return json.loads(match.group(1))

    # Düz JSON ara
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return json.loads(match.group(0))

    raise ValueError(f"JSON ayrıştırılamadı: {text[:200]}")


def _validate_routing_output(data: Dict[str, Any]) -> bool:
    """Yönlendirme çıktısının gerekli alanları içerdiğini doğrular."""
    required = {"hedef_birim", "gerekce", "yonlendirme_guven_skoru"}
    if not required.issubset(data.keys()):
        return False
    if data["hedef_birim"] not in HEDEF_BIRIMLER:
        return False
    score = data.get("yonlendirme_guven_skoru", -1)
    if not (0 <= score <= 1):
        return False
    return True


def _fallback_routing(evrak_turu: str, alici_kurum: str) -> Dict[str, Any]:
    """
    Ollama bağlantı hatası veya model hatası durumunda kural tabanlı fallback yönlendirme.
    """
    kural_haritasi = {
        "DILEKCE": "YAZI_ISLERI",
        "BILGI_EDINME_BASVURUSU": "YAZI_ISLERI",
        "SIKAYET_BASVURUSU": "YAZI_ISLERI",
        "RESMI_UST_YAZI": "YAZI_ISLERI",
        "CEVAP_YAZISI": "YAZI_ISLERI",
        "BILGILENDIRME_YAZISI": "YAZI_ISLERI",
        "TALIMAT_YAZISI": "YAZI_ISLERI",
        "FATURA": "DESTEK_HIZMETLERI",
        "SOZLESME_PROTOKOL": "HUKUK_MUSAVIRLIGI",
        "TUTANAK_RAPOR": "YAZI_ISLERI",
        "DIGER": "MANUEL_BELIRSIZ",
    }
    hedef = kural_haritasi.get(evrak_turu, "MANUEL_BELIRSIZ")
    return {
        "hedef_birim": hedef,
        "gerekce": (
            f"Ollama modeline erişilemediğinden kural tabanlı yönlendirme uygulandı. "
            f"'{evrak_turu}' türündeki evrak '{hedef}' birimine yönlendirildi."
        ),
        "yonlendirme_guven_skoru": 0.60,
        "_kaynak": "FALLBACK_KURAL_TABANI",
    }


def routing_node(state: AgentState) -> Dict[str, Any]:
    """
    Evrakı incelemesi gereken kurumsal birimi belirler.

    Akış:
    1. Agent 2 ve 3'ün çıktılarından bağlamı derler
    2. Few-Shot + Structured Output ile Ollama'ya yönlendirme sorar (max 3 mevzuat)
    3. Model yanıtını parse eder ve doğrular
    4. Hata durumunda kural tabanlı fallback'e düşer
    """
    agent2: Dict = state.get("agent2_output") or {}
    agent3: Dict = state.get("agent3_output") or {}

    # Bağlam verilerini çıkar
    cikartilan = agent2.get("cikartilan_bilgiler", {}) or {}
    kaynak_baglam = agent3.get("kaynak_baglam", {}) or {}

    evrak_turu = kaynak_baglam.get("evrak_turu") or agent2.get("evrak_turu", "DIGER")
    alici_kurum = cikartilan.get("alici_kurum") or "Belirtilmemiş"
    konu = cikartilan.get("konu") or "Belirtilmemiş"
    ozet = agent2.get("ozet") or "Özet mevcut değil."

    # Mevzuat — ilk 3 maddeyle sınırla (sözleşme §7.3)
    mevzuat_listesi = agent2.get("ilgili_mevzuat") or []
    mevzuat_str = "; ".join(
        m.get("madde", "") for m in mevzuat_listesi[:3] if m.get("madde")
    ) or "Mevzuat eşleşmesi yapılamamıştır."

    hata_log = list(state.get("hata_log", []))

    # ─── Ollama LLM Çağrısı ───────────────────────────────────────────────────
    try:
        from langchain_ollama import ChatOllama
        from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

        messages_raw = build_few_shot_messages(
            evrak_turu=evrak_turu,
            alici_kurum=alici_kurum,
            konu=konu,
            ozet=ozet,
            ilgili_mevzuat=mevzuat_str,
        )

        # LangChain message nesnelerine dönüştür
        lc_messages = []
        for msg in messages_raw:
            role = msg["role"]
            content = msg["content"]
            if role == "system":
                lc_messages.append(SystemMessage(content=content))
            elif role == "user":
                lc_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                lc_messages.append(AIMessage(content=content))

        llm = ChatOllama(
            model=OLLAMA_MODEL,
            base_url=OLLAMA_BASE_URL,
            temperature=0.1,  # Düşük temperature: tutarlı JSON çıktısı
            format="json",    # Ollama JSON modu (structured output)
        )

        response = llm.invoke(lc_messages)
        raw_text = response.content

        routing_data = _extract_json_from_text(raw_text)

        if not _validate_routing_output(routing_data):
            raise ValueError(f"Geçersiz yönlendirme çıktısı: {routing_data}")

        logger.info(
            "Yönlendirme kararı: %s (güven: %.2f)",
            routing_data["hedef_birim"],
            routing_data["yonlendirme_guven_skoru"],
        )

    except Exception as e:
        hata_mesaji = f"[RoutingNode] LLM hatası: {str(e)} — Fallback kural motoru devrede."
        logger.warning(hata_mesaji)
        hata_log.append(hata_mesaji)
        routing_data = _fallback_routing(evrak_turu, alici_kurum)

    return {
        "nihai_yonlendirme": routing_data,
        "hata_log": hata_log,
    }
