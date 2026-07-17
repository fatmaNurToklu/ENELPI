# -*- coding: utf-8 -*-
"""
Ajan 4 — Streamlit Arayüzü
TEKNOFEST TYDA 2026 — ENELPİ Takımı
"""

import os
import sys
import json
import uuid
import re
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List

import streamlit as st

# Proje kökünü path'e ekle
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from agent4.graph import build_graph, create_initial_state
import agent4.state

# Loglama ayarları
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agent4.streamlit")

# ─── Senaryo Tanımları ────────────────────────────────────────────────────────
SENARYOLAR = {
    "TASLAK_HAZIR": {
        "label": "✅ Normal Akış",
        "aciklama": "Evrak eksiksiz okundu, sınıflandırıldı ve resmî yazı taslağı başarıyla üretildi. Ajan 4, LLM Few-Shot ile birim yönlendirmesi yaparak evrakı otomatik onaylama kuyruğuna alır.",
        "renk": "#10b981",
    },
    "EKSIK_BILGI": {
        "label": "📝 Eksik Bilgi",
        "aciklama": "Evrakta T.C. kimlik numarası ve gönderici adı eksik. LangGraph interrupt tetiklenir, kullanıcıdan eksik bilgiler alınır, Ajan 2'ye geri besleme (loopback) yapılır.",
        "renk": "#f59e0b",
    },
    "MANUEL": {
        "label": "⚠️ Manuel İnceleme",
        "aciklama": "Düşük OCR güven skoru (0.58). Evrak okundu ancak güven eşiğinin altında. LangGraph interrupt ile insan onay kuyruğuna düşer.",
        "renk": "#ef4444",
    },
    "URETILEMEDI": {
        "label": "🔄 Yeniden Deneme Senaryosu",
        "aciklama": "Ajan 3'te taslak üretimi başarısız. Ajan 4, temperature artırarak 1 yeniden deneme yapar; başarılı olursa normal akışa döner.",
        "renk": "#8b5cf6",
    },
}

BIRIM_RENKLERI = {
    "INSAN_KAYNAKLARI":    ("👥", "#3b82f6"),
    "BILGI_ISLEM":         ("💻", "#8b5cf6"),
    "HUKUK_MUSAVIRLIGI":   ("⚖️",  "#ef4444"),
    "YAZI_ISLERI":         ("📄", "#10b981"),
    "DESTEK_HIZMETLERI":   ("🔧", "#f59e0b"),
    "STRATEJI_GELISTIRME": ("📊", "#06b6d4"),
    "MANUEL_BELIRSIZ":     ("❓", "#6b7280"),
}

BIRIM_TR = {
    "INSAN_KAYNAKLARI":    "İnsan Kaynakları",
    "BILGI_ISLEM":         "Bilgi İşlem",
    "HUKUK_MUSAVIRLIGI":   "Hukuk Müşavirliği",
    "YAZI_ISLERI":         "Yazı İşleri",
    "DESTEK_HIZMETLERI":   "Destek Hizmetleri",
    "STRATEJI_GELISTIRME": "Strateji Geliştirme",
    "MANUEL_BELIRSIZ":     "Manuel / Belirsiz",
}

# ─── Streamlit Sayfa Konfigürasyonu ──────────────────────────────────────────
st.set_page_config(
    page_title="Ajan 4 — Orkestrasyon Arayüzü",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── Custom CSS (Glassmorphism & Dark Mode) ───────────────────────────────────
CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* Temel stil */
.stApp {
    background-color: #0f0f1a !important;
    color: #e2e8f0 !important;
    font-family: 'Inter', sans-serif !important;
}

/* Header Banner */
.agent4-header {
    background: linear-gradient(135deg, #16213e 0%, #0f172a 100%);
    border: 1px solid rgba(79, 142, 247, 0.25);
    border-radius: 16px;
    padding: 24px 30px;
    margin-bottom: 25px;
    box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
}
.agent4-header h1 {
    font-size: 2.2rem;
    font-weight: 800;
    margin: 0 0 8px 0;
    background: linear-gradient(135deg, #4f8ef7, #8b5cf6, #10b981);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.agent4-header p {
    color: #94a3b8;
    font-size: 0.95rem;
    margin: 0;
}

/* Kartlar */
.custom-card {
    background: #16213e;
    border: 1px solid #2d3748;
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 15px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

/* Evrak ID Chip */
.evrak-chip {
    display: inline-block;
    background: #0f172a;
    border: 1px solid #334155;
    border-radius: 20px;
    padding: 4px 14px;
    font-size: 0.85rem;
    color: #cbd5e1 !important;
    font-family: monospace;
    font-weight: bold;
    margin-top: 5px;
    margin-right: 10px;
}

/* Senaryo Açıklama */
.senaryo-aciklama {
    background: #0f172a;
    border-left: 4px solid #4f8ef7;
    border-radius: 0 8px 8px 0;
    padding: 12px 16px;
    color: #94a3b8 !important;
    font-size: 0.88rem;
    line-height: 1.6;
    margin: 10px 0 15px 0;
}

/* Log Kutusu */
.log-box {
    background: #0f172a;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 15px;
    font-family: monospace;
    font-size: 0.85rem;
    max-height: 250px;
    overflow-y: auto;
}

/* JSON Kutusu */
.json-box {
    background: #0f172a;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 15px;
    font-family: monospace;
    font-size: 0.85rem;
    color: #7dd3fc;
}

/* Tablar */
.stTabs [data-baseweb="tab-list"] {
    gap: 10px;
}
.stTabs [data-baseweb="tab"] {
    background-color: #16213e;
    border: 1px solid #2d3748;
    border-radius: 8px 8px 0 0;
    color: #94a3b8;
    padding: 10px 20px;
    font-weight: 600;
}
.stTabs [aria-selected="true"] {
    background-color: #1e293b !important;
    border-color: #4f8ef7 !important;
    color: #4f8ef7 !important;
}

/* Buton stilleri */
div.stButton > button {
    border-radius: 8px !important;
    font-weight: 600 !important;
    transition: all 0.3s ease;
}
div.stButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(79, 142, 247, 0.3);
}

/* İlerleme çubuğu arka plan overlay */
.progress-overlay {
    position: relative;
    background: rgba(15,15,26,0.85);
    backdrop-filter: blur(6px);
    border: 1px solid #2d3748;
    border-radius: 14px;
    padding: 28px 24px;
    margin-bottom: 20px;
}
.progress-overlay .step-label {
    color: #94a3b8;
    font-size: 0.88rem;
    margin-bottom: 8px;
}
.progress-overlay .pct-label {
    color: #4f8ef7;
    font-size: 1.6rem;
    font-weight: 800;
    text-align: center;
    margin-top: 10px;
}

/* File Uploader Turkcelestirme */
[data-testid="stFileUploader"] button {
    font-size: 0 !important;
}
[data-testid="stFileUploader"] button * {
    display: none !important;
}
[data-testid="stFileUploader"] button::before {
    content: "Dosya Seçin" !important;
    font-size: 14px !important;
    display: inline-block !important;
    visibility: visible !important;
}
[data-testid="stFileUploaderDropzone"] [data-testid="stFileUploaderDropzoneText"] {
    font-size: 0 !important;
}
[data-testid="stFileUploaderDropzone"] [data-testid="stFileUploaderDropzoneText"] * {
    display: none !important;
}
[data-testid="stFileUploaderDropzone"] [data-testid="stFileUploaderDropzoneText"]::after {
    content: "Dosyayı buraya sürükleyip bırakın" !important;
    font-size: 14px !important;
    display: block !important;
    visibility: visible !important;
    color: #94a3b8 !important;
}
[data-testid="stFileUploader"] section small {
    font-size: 0 !important;
}
[data-testid="stFileUploader"] section small * {
    display: none !important;
}
[data-testid="stFileUploader"] section small::after {
    content: "Limit: Dosya başına 200MB (PDF, JPG, JPEG, PNG, TXT)" !important;
    font-size: 12px !important;
    display: block !important;
    visibility: visible !important;
    color: #64748b !important;
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ─── Yardımcı Fonksiyonlar ────────────────────────────────────────────────────

def _highlight_missing(metin: str) -> str:
    """Eksik alanları ve uyarıları görsel olarak işaretler."""
    metin = re.sub(
        r"\[BİLGİ EKSİK: ([^\]]+)\]",
        r'<mark style="background:rgba(239,68,68,0.25);border:1px solid rgba(239,68,68,0.5);'
        r'border-radius:3px;padding:0 4px;color:#fca5a5">[EKSİK: \1]</mark>',
        metin,
    )
    metin = re.sub(
        r"\[UYARI: ([^\]]+)\]",
        r'<mark style="background:rgba(245,158,11,0.2);border:1px solid rgba(245,158,11,0.4);'
        r'border-radius:3px;padding:0 4px;color:#fcd34d">[⚠ \1]</mark>',
        metin,
    )
    return metin.replace("\n", "<br>")


def _pipeline_html(completed_nodes: list, current_node: Optional[str] = None) -> str:
    """Multi-Ajan adım ilerleme tablosunu HTML olarak oluşturur."""
    adimlar = [
        ("agent1", "Ajan 1: OCR & Sınıflandırma",    "🔍"),
        ("agent2", "Ajan 2: NER & Mevzuat RAG",       "🧠"),
        ("agent3", "Ajan 3: Slot-Filling Taslaklama", "✍️"),
        ("routing", "Ajan 4: Orkestrasyon & Yönlendirme", "🎯"),
    ]
    html = '<div style="display:flex;flex-direction:column;gap:8px">'
    for code, label, ikon in adimlar:
        if code in completed_nodes:
            stil = "background:rgba(16,185,129,0.12);border:1px solid #10b981"
            durum = '<span style="color:#10b981;font-size:0.8rem;font-weight:600">✓ Tamamlandı</span>'
        elif code == current_node:
            stil = "background:rgba(245,158,11,0.12);border:1px solid #f59e0b"
            durum = '<span style="color:#f59e0b;font-size:0.8rem;font-weight:600">⚡ İşleniyor/Durakladı</span>'
        else:
            stil = "background:#0f172a;border:1px solid #2d3748"
            durum = '<span style="color:#475569;font-size:0.8rem">Bekliyor</span>'
            
        html += f"""<div style="{stil};border-radius:10px;padding:10px 16px;display:flex;align-items:center;gap:12px">
            <span style="font-size:1.4em">{ikon}</span>
            <div style="flex:1">
                <div style="color:#e2e8f0;font-weight:600;font-size:0.88em">{label}</div>
            </div>
            {durum}
        </div>"""
    html += "</div>"
    return html


def _durum_badge(sistem_durumu: str) -> str:
    """Sistem durumunu temsil eden renkli bir badge oluşturur."""
    cfg = {
        "OTOMATIK_ONAYLANABILIR":   ("✅", "#10b981", "Otomatik Onaylandı"),
        "INSAN_ONAYI_BEKLIYOR":     ("⚠️", "#f59e0b", "İnsan Onayı Bekleniyor"),
        "EKSIK_BILGI_TALEBI":       ("📝", "#3b82f6", "Eksik Bilgi Talebi"),
        "KRITIK_HATA_MANUEL_KUYRUK":("❌", "#ef4444", "Kritik Hata — Manuel Kuyruk"),
    }
    ikon, renk, etiket = cfg.get(sistem_durumu, ("❓", "#6b7280", sistem_durumu or "Bekleniyor"))
    return (f'<div style="background:{renk}20;border:1px solid {renk}50;border-radius:10px;'
            f'padding:12px 20px;text-align:center;margin-bottom:15px">'
            f'<span style="font-size:1.4em">{ikon}</span>'
            f'<span style="color:{renk};font-weight:700;font-size:1.05em;margin-left:8px">{etiket}</span></div>')


def _routing_card(yonlendirme: Optional[Dict]) -> str:
    """Birim yönlendirme kartını oluşturur."""
    if not yonlendirme:
        return '<div style="color:#475569;text-align:center;padding:24px;font-size:0.9em">Yönlendirme kararı bekleniyor...</div>'
    birim    = yonlendirme.get("hedef_birim", "MANUEL_BELIRSIZ")
    gerekce  = yonlendirme.get("gerekce", "—")
    guven    = yonlendirme.get("yonlendirme_guven_skoru", 0)
    pct      = int(guven * 100)
    kaynak   = yonlendirme.get("_kaynak", "LLM_FEW_SHOT")
    ikon, renk = BIRIM_RENKLERI.get(birim, ("❓", "#6b7280"))
    birim_tr   = BIRIM_TR.get(birim, birim)
    g_renk     = "#10b981" if guven >= .8 else "#f59e0b" if guven >= .6 else "#ef4444"
    k_label    = "🤖 LLM Few-Shot" if "LLM" in kaynak else "📋 Kural Motoru"
    return f"""<div style="background:linear-gradient(135deg,#16213e,#1a1a2e);border:1px solid {renk}40;
        border-radius:14px;padding:20px;">
      <div style="text-align:center;margin-bottom:14px">
        <div style="font-size:2.2em">{ikon}</div>
        <div style="color:{renk};font-size:1.25em;font-weight:800;margin:4px 0">{birim_tr}</div>
        <div style="color:#64748b;font-size:0.72em">{birim}</div>
      </div>
      <div style="background:#0f172a;border-radius:8px;padding:10px;margin-bottom:12px">
        <div style="color:#64748b;font-size:0.7em;text-transform:uppercase;letter-spacing:.08em;margin-bottom:3px">Gerekçe</div>
        <div style="color:#e2e8f0;font-size:0.85em;line-height:1.5">{gerekce}</div>
      </div>
      <div style="display:flex;justify-content:space-between;align-items:center">
        <div><div style="color:#64748b;font-size:0.7em;text-transform:uppercase">Güven</div>
             <div style="color:{g_renk};font-size:1.3em;font-weight:700">%{pct}</div></div>
        <div style="text-align:right"><div style="color:#64748b;font-size:0.7em;text-transform:uppercase">Kaynak</div>
             <div style="color:#94a3b8;font-size:0.8em">{k_label}</div></div>
      </div>
      <div style="margin-top:10px;background:#0f172a;border-radius:4px;height:5px;overflow:hidden">
        <div style="height:100%;width:{pct}%;background:{g_renk};border-radius:4px;"></div>
      </div>
    </div>"""


def _log_html(hata_log: list) -> str:
    """Log kayıtlarını HTML olarak formatlar."""
    if not hata_log:
        return '<span style="color:#475569;font-size:0.85em">Log kaydı yok.</span>'
    out = ""
    for msg in hata_log:
        # "agent" -> "ajan" dönüşümü log mesajlarında
        msg_tr = msg.replace("Agent", "Ajan").replace("agent", "ajan")
        renk = "#ef4444" if "KRITIK" in msg or "hata" in msg.lower() else \
               "#f59e0b" if "Loopback" in msg or "uyarı" in msg.lower() else "#64748b"
        out += f'<div style="font-size:0.85rem;color:{renk};margin-bottom:5px;font-family:monospace">› {msg_tr}</div>'
    return out


# ─── LangGraph Orkestrasyon Entegrasyonu ──────────────────────────────────────

@st.cache_resource
def _get_graph(use_real: bool = False):
    """LangGraph StateGraph'i singleton olarak derler."""
    return build_graph(use_memory=True, use_real_agents=use_real)


def _run_pipeline(
    evrak_id: str,
    senaryo: str,
    thread_id: str,
    dosya_yolu: Optional[str] = None,
    use_real: bool = False,
    model_name: str = "gemma3:4b",
) -> Dict[str, Any]:
    """LangGraph pipeline'ını başlatır."""
    # LLM Modeli dinamik olarak ata
    agent4.state.OLLAMA_MODEL = model_name
    
    graph = _get_graph(use_real=use_real)
    config = {"configurable": {"thread_id": thread_id}}
    state0 = create_initial_state(
        evrak_id,
        senaryo,
        dosya_yolu=dosya_yolu,
        pipeline_modu="GERCEK" if use_real else "DEMO",
    )
    
    try:
        result = graph.invoke(state0, config)
    except Exception as e:
        logger.exception("Pipeline çağrı hatası: %s", e)
        result = {}
        
    gs = graph.get_state(config)
    if gs.next:
        interrupt_data = {}
        for t in gs.tasks:
            if hasattr(t, "interrupts") and t.interrupts:
                interrupt_data = t.interrupts[0].value
                break
        return {"interrupted": True, "interrupt_data": interrupt_data, "state": gs.values, "next_node": gs.next[0]}
    return {"interrupted": False, "result": result, "state": result}


def _resume_pipeline(
    thread_id: str,
    resume_val: Any,
    use_real: bool = False,
    model_name: str = "gemma3:4b",
) -> Dict[str, Any]:
    """LangGraph pipeline'ını bir interrupt sonrasında devam ettirir."""
    # LLM Modeli dinamik olarak ata
    agent4.state.OLLAMA_MODEL = model_name
    
    graph = _get_graph(use_real=use_real)
    config = {"configurable": {"thread_id": thread_id}}
    
    from langgraph.types import Command
    try:
        result = graph.invoke(Command(resume=resume_val), config)
    except Exception as e:
        logger.exception("Pipeline devam hatası: %s", e)
        result = {}
        
    gs = graph.get_state(config)
    if gs.next:
        interrupt_data = {}
        for t in gs.tasks:
            if hasattr(t, "interrupts") and t.interrupts:
                interrupt_data = t.interrupts[0].value
                break
        return {"interrupted": True, "interrupt_data": interrupt_data, "state": gs.values, "next_node": gs.next[0]}
    return {"interrupted": False, "result": result, "state": result}


# ─── Arayüz State Yönetimi ───────────────────────────────────────────────────

if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
if "evrak_id" not in st.session_state:
    st.session_state.evrak_id = ""
if "run_result" not in st.session_state:
    st.session_state.run_result = None
if "use_real" not in st.session_state:
    st.session_state.use_real = True  # Varsayılan: Gerçek Pipeline
if "senaryo" not in st.session_state:
    st.session_state.senaryo = "TASLAK_HAZIR"
if "pipeline_running" not in st.session_state:
    st.session_state.pipeline_running = False

# ─── ARAYÜZ TASARIMI ──────────────────────────────────────────────────────────

# Header Banner
st.markdown(f"""
<div class="agent4-header">
    <h1>🎯 Ajan 4 — Birim Yönlendirme & Orkestrasyon</h1>
    <p>
        <strong style="color:#4f8ef7">TEKNOFEST TYDA 2026</strong> &nbsp;|&nbsp;
        <strong style="color:#8b5cf6">ENELPİ Takımı</strong> &nbsp;|&nbsp;
        Geliştirici: <strong style="color:#10b981">ENELPİ</strong> &nbsp;|&nbsp;
        LangGraph · Ollama · Streamlit
    </p>
</div>
""", unsafe_allow_html=True)

col1, col2 = st.columns([1, 2], gap="large")

# ──────────────────────────────────────────────────────────────────────────────
# SOL PANEL (Kontroller & Girdiler)
# ──────────────────────────────────────────────────────────────────────────────
with col1:
    st.markdown("### 🛠️ Kontrol Paneli")
    
    # Gerçek/Demo Pipeline Seçicisi
    use_real = st.toggle(
        "🔴 Gerçek Pipeline (Ajan 1/2/3)",
        value=st.session_state.use_real,
        help="Açık: Gerçek Ajan Kodları (OCR + RAG + Taslak) · Kapalı: Demo Modu (Mock JSON)"
    )
    st.session_state.use_real = use_real
    
    # Ollama Model Seçicisi
    model_name = st.selectbox(
        "🤖 Orkestrasyon Model Seçimi",
        options=["gemma3:4b", "gemma2:9b"],
        index=0,
        help="LangGraph birim yönlendirme (routing) kararlarında bu modeli kullanır."
    )
    
    yuklenen_dosya = None
    dosya_yolu = None
    
    if not use_real:
        # DEMO PANEL
        st.markdown("---")
        st.markdown("#### 🎭 Demo Senaryosu Seçimi")
        
        senaryo_key = st.radio(
            "Demo Senaryoları",
            options=list(SENARYOLAR.keys()),
            format_func=lambda x: SENARYOLAR[x]["label"],
            label_visibility="collapsed"
        )
        st.session_state.senaryo = senaryo_key
        
        # Senaryo açıklaması
        s_desc = SENARYOLAR[senaryo_key]
        st.markdown(f"""
        <div class="senaryo-aciklama" style="border-left-color:{s_desc['renk']}">
            {s_desc['aciklama']}
        </div>
        """, unsafe_allow_html=True)
        
    else:
        # GERÇEK PIPELINE PANEL
        st.markdown("---")
        st.markdown("#### 📁 Evrak Yükleme")
        yuklenen_dosya = st.file_uploader(
            "Evrak Dosyası Yükleyin",
            type=["pdf", "jpg", "jpeg", "png", "txt"],
            help="PDF, JPG, PNG, veya TXT formatında resmi bir kamu evrakı yükleyin."
        )
        
        # Dosya geçici olarak kaydedilir
        if yuklenen_dosya is not None:
            temp_dir = Path("temp_evraklar")
            temp_dir.mkdir(exist_ok=True)
            dosya_yolu = str(temp_dir / yuklenen_dosya.name)
            with open(dosya_yolu, "wb") as f:
                f.write(yuklenen_dosya.getbuffer())
            st.success(f"Dosya yüklendi: `{yuklenen_dosya.name}`")
            
    # Aksiyon Butonları
    btn_col1, btn_col2 = st.columns(2)
    
    with btn_col1:
        start_btn = st.button("▶  Başlat", use_container_width=True, type="primary")
        
    with btn_col2:
        clear_btn = st.button("🗑 Temizle", use_container_width=True)
        
    if clear_btn:
        st.session_state.thread_id = str(uuid.uuid4())
        st.session_state.evrak_id = ""
        st.session_state.run_result = None
        st.session_state.pipeline_running = False
        # Geçici dosyaları temizle
        if dosya_yolu and os.path.exists(dosya_yolu):
            try: os.remove(dosya_yolu)
            except: pass
        st.rerun()

    # Başlatma tetikleyicisi
    if start_btn:
        st.session_state.thread_id = str(uuid.uuid4())
        evrak_id = f"EVR-2026-{uuid.uuid4().int % 9000 + 1000}"
        st.session_state.evrak_id = evrak_id
        st.session_state.pipeline_running = True
        
        # ─── İLERLEME ÇUBUĞU İLE PIPELINE ÇALIŞTIRMA ───
        adim_labels = [
            "Ajan 1: OCR & Sınıflandırma",
            "Ajan 2: NER & Mevzuat RAG",
            "Ajan 3: Slot-Filling Taslaklama",
            "Ajan 4: Orkestrasyon & Yönlendirme",
        ]
        
        progress_bar = st.progress(0, text="⏳ Pipeline başlatılıyor...")
        status_box = st.empty()
        
        # İlk adım göster
        progress_bar.progress(10, text=f"🔍 {adim_labels[0]} çalışıyor...")
        
        # Pipeline'ı çalıştır
        res = None
        if not use_real:
            progress_bar.progress(25, text=f"🔍 {adim_labels[0]} çalışıyor...")
            res = _run_pipeline(
                evrak_id=evrak_id,
                senaryo=st.session_state.senaryo,
                thread_id=st.session_state.thread_id,
                use_real=False,
                model_name=model_name
            )
        else:
            if yuklenen_dosya is None:
                progress_bar.empty()
                st.error("Lütfen önce bir dosya yükleyin!")
                res = None
            else:
                progress_bar.progress(15, text=f"🔍 {adim_labels[0]} çalışıyor...")
                res = _run_pipeline(
                    evrak_id=evrak_id,
                    senaryo="TASLAK_HAZIR",
                    thread_id=st.session_state.thread_id,
                    dosya_yolu=dosya_yolu,
                    use_real=True,
                    model_name=model_name
                )
                # Geçici dosyayı sil
                try: os.remove(dosya_yolu)
                except: pass
        
        # İlerleme tamamlandı
        if res is not None:
            progress_bar.progress(100, text="✅ Pipeline tamamlandı!")
            time.sleep(0.6)
            progress_bar.empty()
            status_box.empty()
            st.session_state.run_result = res
            st.session_state.pipeline_running = False
            st.rerun()


# ──────────────────────────────────────────────────────────────────────────────
# SAĞ PANEL (Sonuçlar, Tablar, Görseller)
# ──────────────────────────────────────────────────────────────────────────────
with col2:
    st.markdown("### 📊 İşlem Sonuçları")
    
    res = st.session_state.run_result
    
    if res is None:
        # Boş arayüz durumu
        st.markdown(f"""
        <div class="custom-card" style="text-align:center;padding:40px 20px;color:#64748b">
            <h4>Pipeline henüz çalıştırılmadı.</h4>
            <p>Sol paneldeki parametreleri ayarlayarak 'Başlat' butonuna basın.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Boş pipeline adımları göster
        st.markdown("#### ⏳ İşlem Adımları")
        st.markdown(_pipeline_html([]), unsafe_allow_html=True)
        
    else:
        # Pipeline çalıştırıldı
        interrupted = res.get("interrupted", False)
        state_values = res.get("state", {})
        
        # 1. Pipeline Başlık & ID
        evrak_chip_html = f'<div class="evrak-chip">🔖 {st.session_state.evrak_id}</div>'
        mod_chip_html = (
            '<div class="evrak-chip" style="background:rgba(239,68,68,0.15);border-color:#ef4444;color:#f87171">🔴 GERÇEK PIPELINE</div>'
            if st.session_state.use_real else
            '<div class="evrak-chip" style="background:rgba(139,92,246,0.15);border-color:#8b5cf6;color:#c084fc">🎭 Demo Modu</div>'
        )
        
        # Retry & Loopback bilgisi
        retry = state_values.get("retry_count", 0)
        loopback = state_values.get("loopback_count", 0)
        retry_chip = f'<div class="evrak-chip">🔄 Yeniden Deneme: {retry}</div>' if retry > 0 else ""
        loopback_chip = f'<div class="evrak-chip">🔁 Geri Besleme: {loopback}</div>' if loopback > 0 else ""
        
        st.markdown(f"""
        <div style="display:flex;align-items:center;flex-wrap:wrap;margin-bottom:15px">
            {evrak_chip_html} {mod_chip_html} {retry_chip} {loopback_chip}
        </div>
        """, unsafe_allow_html=True)
        
        # 2. Sistem Durum Göstergesi
        if interrupted:
            idata = res.get("interrupt_data", {})
            tip = idata.get("tip", "")
            sistem_durumu = "EKSIK_BILGI_TALEBI" if "EKSIK_BILGI" in tip else "INSAN_ONAYI_BEKLIYOR"
        else:
            final_res = res.get("result", {})
            nihai_cikti = final_res.get("nihai_cikti", {}) or {}
            sistem_durumu = nihai_cikti.get("sistem_durumu", state_values.get("sistem_durumu", ""))
            
        st.markdown(_durum_badge(sistem_durumu), unsafe_allow_html=True)
        
        # 3. Adım İlerleme Göstergesi
        st.markdown("#### ⏳ İşlem Adımları")
        completed_nodes = []
        current_node = None
        
        if interrupted:
            current_node = res.get("next_node")
            # Hangilerinin bittiğini belirle
            if current_node == "missing_info":
                completed_nodes = ["agent1", "agent2", "agent3"]
            elif current_node == "human_approval":
                completed_nodes = ["agent1", "agent2", "agent3"]
        else:
            completed_nodes = ["agent1", "agent2", "agent3", "routing"]
            
        st.markdown(_pipeline_html(completed_nodes, current_node), unsafe_allow_html=True)
        st.markdown("---")
        
        # 4. Tab Yapısı
        tab_taslak, tab_routing, tab_eksik, tab_onay, tab_log, tab_json = st.tabs([
            "📝 Taslak", "🎯 Yönlendirme", "📋 Eksik Bilgi", "👤 İnsan Onayı", "📑 Log", "🔍 JSON"
        ])
        
        # ─── TAB: TASLAK ───
        with tab_taslak:
            st.markdown("#### Üretilen Resmî Yazı Taslağı")
            taslak_metni = ""
            if interrupted:
                idata = res.get("interrupt_data", {})
                taslak_metni = idata.get("taslak_metni", "")
            else:
                final_res = res.get("result", {})
                nihai_cikti = final_res.get("nihai_cikti", {}) or {}
                taslak_metni = (nihai_cikti.get("uretilen_taslak") or {}).get("taslak_metni", "")
                
            if taslak_metni:
                highlighted_taslak = _highlight_missing(taslak_metni)
                st.markdown(f"""
                <div style="background:#0f172a;border:1px solid #2d3748;border-radius:10px;padding:20px;font-family:monospace;font-size:0.95rem;line-height:1.7;color:#e2e8f0;white-space:pre-wrap">
                    {highlighted_taslak}
                </div>
                """, unsafe_allow_html=True)
            else:
                st.info("Henüz üretilmiş bir taslak bulunmuyor.")
                
        # ─── TAB: YÖNLENDİRME ───
        with tab_routing:
            st.markdown("#### Birim Yönlendirme Kararı")
            yonlendirme = None
            if not interrupted:
                final_res = res.get("result", {})
                yonlendirme = final_res.get("nihai_yonlendirme")
                
            st.markdown(_routing_card(yonlendirme), unsafe_allow_html=True)
            
        # ─── TAB: EKSİK BİLGİ (Dinamik Interrupt Formu) ───
        with tab_eksik:
            st.markdown("#### Eksik Bilgi Tamamlama")
            if interrupted and "EKSIK_BILGI" in res.get("interrupt_data", {}).get("tip", ""):
                idata = res.get("interrupt_data", {})
                eksik_alanlar = idata.get("eksik_alanlar", [])
                
                st.warning("⚠️ Belgede bazı zorunlu alanlar tespit edilemedi. Lütfen aşağıdaki bilgileri doldurarak süreci devam ettirin:")
                
                with st.form("eksik_bilgi_formu"):
                    inputs = {}
                    for alan in eksik_alanlar:
                        inputs[alan] = st.text_input(f"{alan.upper()} Değeri", key=f"inp_{alan}")
                        
                    submit_eksik = st.form_submit_button("Bilgileri Kaydet ve Süreci Devam Ettir")
                    
                    if submit_eksik:
                        # Değerlerin boş olmadığını kontrol et
                        if not any(v.strip() for v in inputs.values()):
                            st.error("Lütfen en az bir alanı doldurun!")
                        else:
                            with st.spinner("Süreç devam ettiriliyor..."):
                                user_input = {k: v.strip() for k, v in inputs.items() if v.strip()}
                                # Resume tetikle
                                res_new = _resume_pipeline(
                                    thread_id=st.session_state.thread_id,
                                    resume_val=user_input,
                                    use_real=st.session_state.use_real,
                                    model_name=model_name
                                )
                                st.session_state.run_result = res_new
                                st.success("Bilgiler başarıyla gönderildi, sayfa yenileniyor...")
                                st.rerun()
            else:
                st.info("Herhangi bir eksik bilgi bulunmamaktadır veya süreç duraklatılmamıştır.")
                
        # ─── TAB: İNSAN ONAYI (Dinamik Interrupt Formu) ───
        with tab_onay:
            st.markdown("#### Kamu Personeli Onay Masası")
            if interrupted and "INSAN_ONAYI" in res.get("interrupt_data", {}).get("tip", ""):
                idata = res.get("interrupt_data", {})
                mesaj = idata.get("mesaj", "İnceleme gerekiyor.")
                uslup_sorunlari = idata.get("uslup_sorunlari", [])
                taslak_m = idata.get("taslak_metni", "")
                
                st.warning(f"⚠️ İnsan Onayı Gerekli: {mesaj}")
                if uslup_sorunlari:
                    st.error(f"🚨 Üslup İhlalleri: {', '.join(uslup_sorunlari)}")
                    
                st.markdown("##### Taslak Metni Düzenle:")
                # Kullanıcının taslağı düzenlemesine izin ver
                edited_draft = st.text_area(
                    "Taslak Metni Düzenleme",
                    value=taslak_m,
                    height=300,
                    key="edited_draft_area",
                    label_visibility="collapsed"
                )
                
                col_onay1, col_onay2 = st.columns(2)
                with col_onay1:
                    onayla = st.button("👍 Onayla ve Gönder", use_container_width=True, type="primary")
                with col_onay2:
                    reddet = st.button("👎 Reddet ve İptal Et", use_container_width=True)
                    
                if onayla:
                    with st.spinner("Süreç onaylanıyor..."):
                        res_new = _resume_pipeline(
                            thread_id=st.session_state.thread_id,
                            resume_val={"karar": "ONAYLA", "edited_draft": edited_draft},
                            use_real=st.session_state.use_real,
                            model_name=model_name
                        )
                        st.session_state.run_result = res_new
                        st.success("Onaylandı! Sayfa yenileniyor...")
                        st.rerun()
                        
                if reddet:
                    with st.spinner("Süreç reddediliyor..."):
                        res_new = _resume_pipeline(
                            thread_id=st.session_state.thread_id,
                            resume_val={"karar": "REDDET"},
                            use_real=st.session_state.use_real,
                            model_name=model_name
                        )
                        st.session_state.run_result = res_new
                        st.success("Reddedildi! Sayfa yenileniyor...")
                        st.rerun()
            else:
                st.info("İnsan onayı bekleyen bir işlem bulunmamaktadır.")
                
        # ─── TAB: LOG ───
        with tab_log:
            st.markdown("#### Düğüm Çalışma Günlükleri")
            hata_log = state_values.get("hata_log", [])
            st.markdown(f"""
            <div class="log-box">
                {_log_html(hata_log)}
            </div>
            """, unsafe_allow_html=True)
            
        # ─── TAB: JSON ───
        with tab_json:
            st.markdown("#### Sistem Ham Çıktısı (State)")
            if interrupted:
                raw_json = res.get("interrupt_data", {})
            else:
                raw_json = res.get("result", {})
                
            st.markdown(f"""
            <pre class="json-box">{json.dumps(raw_json, ensure_ascii=False, indent=2)}</pre>
            """, unsafe_allow_html=True)
