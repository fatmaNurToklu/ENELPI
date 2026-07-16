"""
Agent 4 — Gradio Demo Arayüzü  (v2 — düzeltilmiş)
TEKNOFEST TYDA 2026 — ENELPİ Takımı

Düzeltmeler (v2):
- Gradio Base theme koyu renk çatışması → CSS değişkenleri override
- Eksik bilgi form inputları outputs listesine eklendi → artık görünüyor
- Tab isimleri kısaltıldı (6 tab → sığıyor)
- "Radio" label kaldırıldı
- Onay sonrası UI geri bildirimi iyileştirildi
- Temizle butonu eklendi
- Evrak ID gösterildi
"""

import json
import logging
import uuid
from typing import Optional, Dict, Any, Tuple

import gradio as gr
from langgraph.types import Command

from agent4.graph import build_graph, create_initial_state

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── Senaryo Tanımları ────────────────────────────────────────────────────────
SENARYOLAR = {
    "TASLAK_HAZIR": {
        "label": "✅ Normal Akış",
        "aciklama": "Evrak eksiksiz okundu, sınıflandırıldı ve resmî yazı taslağı başarıyla üretildi. Agent 4, LLM Few-Shot ile birim yönlendirmesi yaparak evrakı otomatik onaylama kuyruğuna alır.",
        "renk": "#10b981",
    },
    "EKSIK_BILGI": {
        "label": "📝 Eksik Bilgi",
        "aciklama": "Evrakta TC kimlik numarası ve gönderici adı eksik. LangGraph interrupt tetiklenir, kullanıcıdan eksik bilgiler alınır, Agent 2'ye geri besleme yapılır.",
        "renk": "#f59e0b",
    },
    "MANUEL": {
        "label": "⚠️ Manuel İnceleme",
        "aciklama": "Düşük OCR güven skoru (0.58). Evrak okundu ancak güven eşiğinin altında. LangGraph interrupt ile insan onay kuyruğuna düşer.",
        "renk": "#ef4444",
    },
    "URETILEMEDI": {
        "label": "🔄 Retry Senaryosu",
        "aciklama": "Agent 3'te taslak üretimi başarısız. Agent 4, temperature artırarak 1 retry yapar; başarılı olursa normal akışa döner.",
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

# ─── CSS ─────────────────────────────────────────────────────────────────────
# Gradio Base theme'in açık renkli değişkenlerini dark mode ile override ediyoruz
CUSTOM_CSS = """
/* ── Gradio CSS değişkenleri override ── */
:root, .dark {
    --body-background-fill:          #0f0f1a !important;
    --block-background-fill:         #16213e !important;
    --block-border-color:            #2d3748 !important;
    --block-label-background-fill:   #16213e !important;
    --block-label-text-color:        #94a3b8 !important;
    --block-title-text-color:        #e2e8f0 !important;
    --input-background-fill:         #0f172a !important;
    --input-border-color:            #334155 !important;
    --input-placeholder-color:       #475569 !important;
    --checkbox-background-color:     #1e293b !important;
    --color-accent:                  #4f8ef7 !important;
    --color-accent-soft:             rgba(79,142,247,0.15) !important;
    --button-primary-background-fill:#4f8ef7 !important;
    --button-primary-text-color:     #ffffff !important;
    --button-secondary-background-fill: #1e293b !important;
    --button-secondary-text-color:   #e2e8f0 !important;
    --button-cancel-background-fill: #ef4444 !important;
    --button-cancel-text-color:      #ffffff !important;
    --tab-item-text-color:           #94a3b8 !important;
    --tab-item-selected-text-color:  #4f8ef7 !important;
    --tab-item-active-text-color:    #4f8ef7 !important;
    --table-text-color:              #e2e8f0 !important;
    --neutral-100:                   #1e293b;
    --neutral-200:                   #334155;
    --neutral-300:                   #475569;
    --neutral-400:                   #64748b;
    --neutral-500:                   #94a3b8;
    --neutral-600:                   #cbd5e1;
    --neutral-700:                   #e2e8f0;
    --neutral-800:                   #f1f5f9;
    --neutral-900:                   #f8fafc;
    --neutral-950:                   #ffffff;
}

/* ── Temel ── */
body, .gradio-container, .app, main {
    background: #0f0f1a !important;
    color: #e2e8f0 !important;
    font-family: 'Inter', 'Segoe UI', sans-serif !important;
}

/* ── Tüm metin elementleri ── */
label, span, p, div, h1, h2, h3, h4, h5, .label-wrap span,
.block .wrap .secondary-wrap span, .svelte-1f354aw,
.wrap > span, .input-wrap span, legend, fieldset {
    color: #e2e8f0 !important;
}

/* ── Input / Textarea ── */
input[type="text"], input[type="number"], textarea, select,
.block textarea, .block input {
    background: #0f172a !important;
    color: #e2e8f0 !important;
    border: 1px solid #334155 !important;
    border-radius: 8px !important;
}
input::placeholder, textarea::placeholder {
    color: #475569 !important;
}

/* ── Radio butonları ── */
.wrap input[type="radio"] + span,
.radio-group label span,
input[type="radio"] ~ span {
    color: #e2e8f0 !important;
}
.wrap.svelte-1f354aw {
    background: transparent !important;
}

/* ── Tab'lar ── */
.tab-nav button, .tabs > .tab-nav > button {
    color: #94a3b8 !important;
    background: #16213e !important;
    border-bottom: 2px solid transparent !important;
    font-weight: 500 !important;
}
.tab-nav button.selected, .tabs > .tab-nav > button.selected {
    color: #4f8ef7 !important;
    border-bottom: 2px solid #4f8ef7 !important;
    background: #1a1a2e !important;
}
.tab-nav button:hover:not(.selected) {
    color: #e2e8f0 !important;
    background: #1e293b !important;
}

/* ── Block / Panel container ── */
.block, .gr-block, .gap, .form {
    background: #16213e !important;
    border: 1px solid #2d3748 !important;
    border-radius: 12px !important;
}
.block.padded { padding: 16px !important; }

/* ── Butonlar ── */
button.primary { background: linear-gradient(135deg,#4f8ef7,#8b5cf6) !important; color:#fff !important; font-weight:600 !important; border:none !important; }
button.secondary { background: #1e293b !important; color: #e2e8f0 !important; border: 1px solid #334155 !important; }
button.stop { background: #ef4444 !important; color: #fff !important; border: none !important; }
button:hover { filter: brightness(1.1) !important; }

/* ── Code block ── */
.code-wrap, .codemirror-wrapper, .cm-content, .cm-line {
    background: #0f172a !important;
    color: #e2e8f0 !important;
}
.code-wrap code, .codemirror-wrapper code {
    color: #7dd3fc !important;
}

/* ── Markdown ── */
.prose, .md { color: #e2e8f0 !important; }
.prose h3 { color: #94a3b8 !important; font-size: 0.85em !important; text-transform: uppercase !important; letter-spacing: 0.08em !important; }

/* ── Başlık ── */
.agent4-header {
    background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 50%, #0f172a 100%);
    border: 1px solid rgba(79,142,247,0.3);
    border-radius: 16px;
    padding: 20px 28px;
    margin-bottom: 12px;
    box-shadow: 0 0 40px rgba(79,142,247,0.08), inset 0 1px 0 rgba(255,255,255,0.04);
    position: relative;
    overflow: hidden;
}
.agent4-header::before {
    content: '';
    position: absolute; top: -50%; left: -50%;
    width: 200%; height: 200%;
    background: radial-gradient(circle, rgba(79,142,247,0.04) 0%, transparent 70%);
    animation: pulse-bg 5s ease-in-out infinite;
}
@keyframes pulse-bg {
    0%,100%{ opacity:.5; transform:scale(1); }
    50%{ opacity:1; transform:scale(1.03); }
}
.agent4-header h1 {
    font-size: 1.6em; font-weight: 800;
    background: linear-gradient(135deg,#4f8ef7,#8b5cf6,#10b981);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin: 0 0 4px 0;
}
.agent4-header .meta { color:#64748b !important; font-size:0.82em; margin:0; }
.agent4-header .meta strong { -webkit-text-fill-color: unset !important; }

/* ── Evrak ID chip ── */
.evrak-chip {
    display:inline-block; background:#0f172a; border:1px solid #334155;
    border-radius:20px; padding:3px 12px; font-size:0.78em;
    color:#94a3b8 !important; font-family:monospace;
    margin-top:6px;
}

/* ── Senaryo card ── */
.senaryo-aciklama {
    background: #0f172a;
    border-left: 3px solid #4f8ef7;
    border-radius: 0 8px 8px 0;
    padding: 10px 14px;
    color: #94a3b8 !important;
    font-size: 0.83em;
    line-height: 1.5;
    margin: 6px 0 10px 0;
}

/* ── Boş label'ları gizle ── */
#senaryo_radio .block-label,
.block .block-label:empty,
.block > label:empty,
.block > .label-wrap > span:empty {
    display: none !important;
}
/* ── Radio grubu içindeki bloc label ── */
#senaryo_radio > .block-label { display:none !important; }

@keyframes fadeInUp {
    from{ opacity:0; transform:translateY(8px); }
    to  { opacity:1; transform:translateY(0); }
}
.result-in { animation: fadeInUp 0.35s ease forwards; }

/* ── Divider ── */
hr { border-color: #2d3748 !important; margin: 10px 0 !important; }

/* ── Footer ── */
.gr-footer, footer { display: none !important; }
"""


# ─── Yardımcı HTML render fonksiyonları ──────────────────────────────────────

def _highlight_missing(metin: str) -> str:
    import re
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


def _pipeline_html(tamamlandi: bool = False) -> str:
    adimlar = [
        ("Agent 1", "OCR & Sınıflandırma",    "🔍"),
        ("Agent 2", "NER & Mevzuat RAG",       "🧠"),
        ("Agent 3", "Slot-Filling Taslaklama", "✍️"),
        ("Agent 4", "Orkestrasyon & Yönlendirme", "🎯"),
    ]
    html = '<div style="display:flex;flex-direction:column;gap:6px">'
    for isim, aciklama, ikon in adimlar:
        stil  = "background:rgba(16,185,129,0.1);border:1px solid #10b981" if tamamlandi else "background:#0f172a;border:1px solid #2d3748"
        durum = '<span style="color:#10b981;font-size:0.75em;font-weight:600">✓ Tamamlandı</span>' if tamamlandi else '<span style="color:#475569;font-size:0.75em">Bekliyor</span>'
        html += f"""<div style="{stil};border-radius:10px;padding:9px 14px;display:flex;align-items:center;gap:10px">
            <span style="font-size:1.3em">{ikon}</span>
            <div style="flex:1"><div style="color:#e2e8f0;font-weight:600;font-size:0.88em">{isim}</div>
            <div style="color:#64748b;font-size:0.76em">{aciklama}</div></div>{durum}</div>"""
    html += "</div>"
    return html


def _durum_badge(sistem_durumu: str) -> str:
    cfg = {
        "OTOMATIK_ONAYLANABILIR":   ("✅", "#10b981", "Otomatik Onaylandı"),
        "INSAN_ONAYI_BEKLIYOR":     ("⚠️", "#f59e0b", "İnsan Onayı Bekleniyor"),
        "EKSIK_BILGI_TALEBI":       ("📝", "#4f8ef7", "Eksik Bilgi Talebi"),
        "KRITIK_HATA_MANUEL_KUYRUK":("❌", "#ef4444", "Kritik Hata — Manuel Kuyruk"),
    }
    ikon, renk, etiket = cfg.get(sistem_durumu, ("❓", "#6b7280", sistem_durumu or "—"))
    return (f'<div style="background:{renk}20;border:1px solid {renk}50;border-radius:10px;'
            f'padding:12px 20px;text-align:center;margin-bottom:10px">'
            f'<span style="font-size:1.4em">{ikon}</span>'
            f'<span style="color:{renk};font-weight:700;font-size:1em;margin-left:8px">{etiket}</span></div>')


def _routing_card(yonlendirme: Optional[Dict]) -> str:
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
    return f"""<div style="background:linear-gradient(135deg,#16213e,#1d2b50);border:1px solid {renk}40;
        border-radius:14px;padding:20px;animation:fadeInUp .35s ease">
      <div style="text-align:center;margin-bottom:14px">
        <div style="font-size:2.2em">{ikon}</div>
        <div style="color:{renk};font-size:1.25em;font-weight:800;margin:4px 0">{birim_tr}</div>
        <div style="color:#475569;font-size:0.72em">{birim}</div>
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
        <div style="height:100%;width:{pct}%;background:{g_renk};border-radius:4px;transition:width .7s ease"></div>
      </div>
    </div>"""


def _log_html(hata_log: list) -> str:
    if not hata_log:
        return '<span style="color:#475569;font-size:0.85em">Log kaydı yok.</span>'
    out = ""
    for msg in hata_log:
        renk = "#ef4444" if "KRITIK" in msg or "hata" in msg.lower() else \
               "#f59e0b" if "Loopback" in msg or "uyarı" in msg.lower() else "#64748b"
        out += f'<div style="font-size:0.8em;color:{renk};margin-bottom:4px;font-family:monospace">› {msg}</div>'
    return out


# ─── Session store ─────────────────────────────────────────────────────────
_graph_cache: Dict[str, Any] = {}


def _get_graph(use_real: bool = False):
    key = "graph_real" if use_real else "graph_demo"
    if key not in _graph_cache:
        _graph_cache[key] = build_graph(use_memory=True, use_real_agents=use_real)
    return _graph_cache[key]


def _run_pipeline(
    evrak_id: str,
    senaryo: str,
    thread_id: str,
    dosya_yolu: str | None = None,
    use_real: bool = False,
):
    graph  = _get_graph(use_real=use_real)
    config = {"configurable": {"thread_id": thread_id}}
    state0 = create_initial_state(
        evrak_id,
        senaryo,
        dosya_yolu=dosya_yolu,
        pipeline_modu="GERCEK" if use_real else "DEMO",
    )
    try:
        result = graph.invoke(state0, config)
    except Exception:
        result = {}
    gs = graph.get_state(config)
    if gs.next:
        interrupt_data = {}
        for t in gs.tasks:
            if hasattr(t, "interrupts") and t.interrupts:
                interrupt_data = t.interrupts[0].value
                break
        return {"interrupted": True, "interrupt_data": interrupt_data, "state": gs.values}
    return {"interrupted": False, "result": result}


def _resume_pipeline(thread_id: str, resume_val: Any, use_real: bool = False):
    graph  = _get_graph(use_real=use_real)
    config = {"configurable": {"thread_id": thread_id}}
    try:
        result = graph.invoke(Command(resume=resume_val), config)
    except Exception:
        result = {}
    gs = graph.get_state(config)
    if gs.next:
        interrupt_data = {}
        for t in gs.tasks:
            if hasattr(t, "interrupts") and t.interrupts:
                interrupt_data = t.interrupts[0].value
                break
        return {"interrupted": True, "interrupt_data": interrupt_data, "state": gs.values}
    return {"interrupted": False, "result": result}


# ─── Çıktılar listesi indeksleri ─────────────────────────────────────────────
# [0]  pipeline_steps_html
# [1]  durum_html
# [2]  evrak_id_html
# [3]  taslak_html      (Tab: Taslak)
# [4]  routing_html     (Tab: Yönlendirme)
# [5]  eksik_info_html  (Tab: Eksik Bilgi — bilgi kutusu)
# [6]  eksik_form_group (Tab: Eksik Bilgi — form görünürlük)
# [7]  onay_html        (Tab: Onay Kuyruğu — mesaj)
# [8]  onay_butonlar    (Tab: Onay Kuyruğu — buton görünürlük)
# [9]  log_html         (Tab: Log)
# [10] json_out         (Tab: JSON)
# [11] session_state
# [12] mod_chip_html    (Gerçek/Demo mod göstergesi)

def _build_outputs(run_result: dict, senaryo: str, session_state: dict) -> Tuple:
    """Run sonucundan 13 çıktı üretir."""

    evrak_id = session_state.get("evrak_id", "")
    evrak_chip = f'<div class="evrak-chip">🔖 {evrak_id}</div>' if evrak_id else ""
    mod_chip = (
        '<div class="evrak-chip" style="background:rgba(16,185,129,0.12);border-color:#10b981;color:#10b981">🔴 GERÇEK PIPELINE</div>'
        if session_state.get("use_real") else
        '<div class="evrak-chip">🎭 Demo Modu</div>'
    )

    if run_result.get("interrupted"):
        idata   = run_result.get("interrupt_data", {})
        sv      = run_result.get("state", {})
        tip     = idata.get("tip", "")
        taslak_ = _highlight_missing(idata.get("taslak_metni", ""))
        log_    = _log_html(sv.get("hata_log", []))

        taslak_html = f'<div style="background:#0f172a;border:1px solid #2d3748;border-radius:10px;padding:18px;font-family:monospace;font-size:0.88em;line-height:1.7;color:#e2e8f0;white-space:pre-wrap">{taslak_}</div>'

        if "EKSIK_BILGI" in tip:
            eksik_alanlar = idata.get("eksik_alanlar", [])
            alan_listesi  = "".join(f'<li style="color:#fca5a5;margin:3px 0">• {a}</li>' for a in eksik_alanlar)
            info_html = (
                f'<div style="background:#0f172a;border:1px solid rgba(239,68,68,0.4);border-radius:10px;padding:14px">'
                f'<div style="color:#f87171;font-weight:700;margin-bottom:8px">⚠️ Eksik Alanlar Tespit Edildi</div>'
                f'<ul style="margin:0;padding:0;list-style:none">{alan_listesi}</ul>'
                f'<div style="color:#64748b;font-size:0.78em;margin-top:8px">Lütfen aşağıdaki formu doldurun ve gönderin.</div></div>'
            )
            durum_ = _durum_badge("EKSIK_BILGI_TALEBI")
            return (
                _pipeline_html(False), durum_, evrak_chip, taslak_html,
                _routing_card(None),
                info_html,
                gr.update(visible=True),
                "",
                gr.update(visible=False),
                log_, json.dumps(idata, ensure_ascii=False, indent=2), session_state, mod_chip,
            )

        else:  # INSAN_ONAYI
            mesaj_ = idata.get("mesaj", "Bu taslak için yetkili personel onayı gerekmektedir.")
            uslup  = idata.get("uslup_sorunlari", [])
            uslup_html = ""
            if uslup:
                uslup_html = '<div style="margin-top:8px"><div style="color:#fcd34d;font-size:0.78em;margin-bottom:4px">Tespit edilen sorunlar:</div>'
                uslup_html += "".join(f'<div style="color:#fca5a5;font-size:0.78em;font-family:monospace">• {s}</div>' for s in uslup)
                uslup_html += "</div>"
            onay_html = (
                f'<div style="background:#0f172a;border:1px solid rgba(245,158,11,0.4);border-radius:10px;padding:14px">'
                f'<div style="color:#fcd34d;font-weight:700;margin-bottom:8px">⚠️ İnsan Onayı Gerekli</div>'
                f'<div style="color:#94a3b8;font-size:0.88em;line-height:1.5">{mesaj_}</div>'
                f'{uslup_html}</div>'
            )
            durum_ = _durum_badge("INSAN_ONAYI_BEKLIYOR")
            return (
                _pipeline_html(False), durum_, evrak_chip, taslak_html,
                _routing_card(None),
                "", gr.update(visible=False),
                onay_html,
                gr.update(visible=True),
                log_, json.dumps(idata, ensure_ascii=False, indent=2), session_state, mod_chip,
            )

    else:
        final   = run_result.get("result", {})
        nihai   = final.get("nihai_cikti", {}) or {}
        durum_s = nihai.get("sistem_durumu", final.get("sistem_durumu", ""))
        yonl    = final.get("nihai_yonlendirme")
        taslak_ = (nihai.get("uretilen_taslak") or {}).get("taslak_metni", "")
        taslak_h = _highlight_missing(taslak_) if taslak_ else '<span style="color:#475569">Taslak üretilemedi.</span>'
        taslak_html = f'<div style="background:#0f172a;border:1px solid #2d3748;border-radius:10px;padding:18px;font-family:monospace;font-size:0.88em;line-height:1.7;color:#e2e8f0;white-space:pre-wrap">{taslak_h}</div>'
        log_   = _log_html(final.get("hata_log", []))
        meta   = nihai.get("_meta", {})
        retry  = meta.get("retry_count", 0)
        loop   = meta.get("loopback_count", 0)
        meta_chip = f'<div class="evrak-chip">🔄 retry:{retry} &nbsp; 🔁 loopback:{loop}</div>' if retry or loop else ""
        return (
            _pipeline_html(True),
            _durum_badge(durum_s),
            evrak_chip + meta_chip,
            taslak_html,
            _routing_card(yonl),
            "", gr.update(visible=False),
            "", gr.update(visible=False),
            log_,
            json.dumps(nihai, ensure_ascii=False, indent=2),
            session_state,
            mod_chip,
        )


# ─── Handler'lar ─────────────────────────────────────────────────────────────

def handle_run(senaryo_key: str, s_state: dict) -> Tuple:
    """Demo modu — senaryo tabanlı mock pipeline."""
    thread_id = str(uuid.uuid4())
    evrak_id  = f"EVR-2026-{uuid.uuid4().int % 9000 + 1000}"
    s_state["thread_id"] = thread_id
    s_state["evrak_id"]  = evrak_id
    s_state["senaryo"]   = senaryo_key
    s_state["use_real"]  = False
    try:
        result = _run_pipeline(evrak_id, senaryo_key, thread_id, use_real=False)
    except Exception as e:
        logger.exception("Pipeline hatası: %s", e)
        st = dict(s_state)
        return (_pipeline_html(), _durum_badge(""), "", f'<span style="color:#ef4444">Hata: {e}</span>',
                _routing_card(None), "", gr.update(visible=False), "", gr.update(visible=False),
                "", "{}", st, "")
    return _build_outputs(result, senaryo_key, s_state)


def handle_gercek_run(dosya: Any, s_state: dict) -> Tuple:
    """Gerçek pipeline modu — yüklenen dosyayı Agent 1/2/3/4 zincirinden geçirir."""
    hata_cikti = lambda msg: (
        _pipeline_html(), _durum_badge(""), "",
        f'<div style="background:#0f172a;border:1px solid #ef4444;border-radius:10px;padding:16px;color:#f87171">{msg}</div>',
        _routing_card(None), "", gr.update(visible=False), "", gr.update(visible=False),
        "", "{}", s_state,
        '<div class="evrak-chip" style="border-color:#ef4444;color:#ef4444">❌ Hata</div>',
    )

    if dosya is None:
        return hata_cikti("⚠️ Lütfen bir dosya yükleyin (PDF, JPG, PNG veya TXT).")

    # Gradio File bileşeni: dosya.name = geçici dosya yolu
    dosya_yolu = dosya.name if hasattr(dosya, "name") else str(dosya)

    thread_id = str(uuid.uuid4())
    evrak_id  = f"EVR-2026-{uuid.uuid4().int % 9000 + 1000}"
    s_state["thread_id"] = thread_id
    s_state["evrak_id"]  = evrak_id
    s_state["senaryo"]   = "TASLAK_HAZIR"  # Gerçek modda senaryo yok
    s_state["use_real"]  = True
    s_state["dosya_yolu"] = dosya_yolu

    try:
        result = _run_pipeline(
            evrak_id, "TASLAK_HAZIR", thread_id,
            dosya_yolu=dosya_yolu, use_real=True,
        )
    except Exception as e:
        logger.exception("Gerçek pipeline hatası: %s", e)
        return hata_cikti(f"Pipeline hatası: {e}")

    return _build_outputs(result, "TASLAK_HAZIR", s_state)


def handle_eksik_submit(tc: str, gond: str, konu: str, s_state: dict) -> Tuple:
    tid      = s_state.get("thread_id")
    use_real = s_state.get("use_real", False)
    if not tid:
        return handle_run("TASLAK_HAZIR", s_state)
    user_input = {}
    if tc.strip():    user_input["tc_kimlik"] = tc.strip()
    if gond.strip():  user_input["gonderici"] = gond.strip()
    if konu.strip():  user_input["konu"]      = konu.strip()
    try:
        result = _resume_pipeline(tid, user_input, use_real=use_real)
    except Exception as e:
        logger.exception("Resume hatası: %s", e)
        st = dict(s_state)
        return (_pipeline_html(), _durum_badge(""), "", f'<span style="color:#ef4444">Hata: {e}</span>',
                _routing_card(None), "", gr.update(visible=False), "", gr.update(visible=False),
                "", "{}", st, "")
    return _build_outputs(result, s_state.get("senaryo", "EKSIK_BILGI"), s_state)


def handle_approval(karar: str, s_state: dict) -> Tuple:
    tid      = s_state.get("thread_id")
    use_real = s_state.get("use_real", False)
    if not tid:
        return handle_run("TASLAK_HAZIR", s_state)
    try:
        result = _resume_pipeline(tid, {"karar": karar}, use_real=use_real)
    except Exception as e:
        logger.exception("Onay hatası: %s", e)
        st = dict(s_state)
        return (_pipeline_html(), _durum_badge(""), "", f'<span style="color:#ef4444">Hata: {e}</span>',
                _routing_card(None), "", gr.update(visible=False), "", gr.update(visible=False),
                "", "{}", st, "")
    return _build_outputs(result, s_state.get("senaryo", "MANUEL"), s_state)


def handle_temizle(s_state: dict) -> Tuple:
    s_state.clear()
    return (
        _pipeline_html(False),
        '<div style="color:#475569;text-align:center;padding:16px">Pipeline henüz çalıştırılmadı.</div>',
        "",
        '<div style="color:#475569;padding:20px;text-align:center">Taslak bekleniyor...</div>',
        _routing_card(None),
        "", gr.update(visible=False),
        "", gr.update(visible=False),
        "", "{}",
        s_state,
        "",  # mod_chip
    )


def handle_mod_degis(gercek_mi: bool) -> Tuple:
    """Mod toggle değiştiğinde senaryo/upload panellerini göster/gizle."""
    if gercek_mi:
        return gr.update(visible=False), gr.update(visible=True)
    return gr.update(visible=True), gr.update(visible=False)


def update_aciklama(key: str) -> str:
    s = SENARYOLAR.get(key, {})
    renk = s.get("renk", "#4f8ef7")
    txt  = s.get("aciklama", "")
    return f'<div class="senaryo-aciklama" style="border-left-color:{renk}">{txt}</div>'


# ─── Gradio Arayüzü ──────────────────────────────────────────────────────────
def create_app() -> gr.Blocks:
    with gr.Blocks(title="Agent 4 — TEKNOFEST TYDA 2026 | ENELPİ") as demo:

        session_state = gr.State({})

        # ── Başlık ───────────────────────────────────────────────────────────
        gr.HTML("""
        <div class="agent4-header">
            <h1>🎯 Agent 4 — Birim Yönlendirme & Orkestrasyon</h1>
            <p class="meta">
                <strong style="color:#4f8ef7">TEKNOFEST TYDA 2026</strong> &nbsp;|&nbsp;
                <strong style="color:#8b5cf6">ENELPİ Takımı</strong> &nbsp;|&nbsp;
                Geliştirici: <strong style="color:#10b981">Yasin Taha İnal</strong> &nbsp;|&nbsp;
                LangGraph · Ollama gemma2:2b · Gradio 6
            </p>
        </div>
        """)

        with gr.Row(equal_height=False):

            # ── Sol Panel ────────────────────────────────────────────────────
            with gr.Column(scale=1, min_width=300):

                # Mod toggle
                gercek_mod_toggle = gr.Checkbox(
                    label="🔴 Gerçek Pipeline (Agent 1/2/3)",
                    value=False,
                    elem_id="gercek_mod_toggle",
                    info="Kapalı: Demo modu (mock JSON) · Açık: Gerçek ajanlar",
                )

                # ── Demo paneli ───────────────────────────────────────────────
                with gr.Column(visible=True) as demo_panel:
                    gr.Markdown("### 📋 Demo Senaryosu")
                    senaryo_radio = gr.Radio(
                        choices=[(v["label"], k) for k, v in SENARYOLAR.items()],
                        value="TASLAK_HAZIR",
                        label="",
                        show_label=False,
                        elem_id="senaryo_radio",
                    )
                    senaryo_aciklama = gr.HTML(
                        value=update_aciklama("TASLAK_HAZIR"),
                        elem_id="senaryo_aciklama",
                    )
                    senaryo_radio.change(update_aciklama, senaryo_radio, senaryo_aciklama)
                    with gr.Row():
                        calistir_btn = gr.Button("▶  Başlat", variant="primary", size="lg", elem_id="calistir_btn")
                        temizle_btn  = gr.Button("🗑 Temizle", variant="secondary", size="lg", elem_id="temizle_btn")

                # ── Gerçek pipeline paneli ────────────────────────────────────
                with gr.Column(visible=False) as gercek_panel:
                    gr.Markdown("### 📂 Evrak Yükle")
                    gr.HTML('<div style="color:#94a3b8;font-size:0.82em;margin-bottom:8px">PDF, JPG, PNG veya TXT yükleyin. Agent 1 → 2 → 3 → 4 zinciri çalışır.</div>')
                    dosya_input = gr.File(
                        label="Evrak dosyası",
                        file_types=[".pdf", ".jpg", ".jpeg", ".png", ".txt"],
                        elem_id="dosya_input",
                    )
                    gercek_calistir_btn = gr.Button("🚀  Gerçek Pipeline Başlat", variant="primary", size="lg", elem_id="gercek_calistir_btn")
                    gr.HTML('<div style="background:#0f172a;border:1px solid rgba(239,68,68,0.3);border-radius:8px;padding:10px;margin-top:8px"><div style="color:#f87171;font-size:0.78em;font-weight:600">⚠️ Gereksinimler</div><div style="color:#64748b;font-size:0.75em;line-height:1.6;margin-top:4px">• Ollama çalışıyor olmalı<br>• gemma2:9b veya gemma2:2b yüklü<br>• ChromaDB: agent2/chroma_yukle.py çalıştırılmış<br>• pytesseract/tesseract kurulu (OCR için)</div></div>')

                # Mod toggle → panel görünürlüğü
                gercek_mod_toggle.change(
                    handle_mod_degis,
                    inputs=[gercek_mod_toggle],
                    outputs=[demo_panel, gercek_panel],
                )

                gr.HTML('<hr>')
                gr.Markdown("### 🔄 Pipeline Adımları")
                pipeline_steps = gr.HTML(value=_pipeline_html(False), elem_id="pipeline_steps")

                gr.HTML('<hr>')
                gr.HTML("""
                <div style="background:#0f172a;border:1px solid #1e293b;border-radius:10px;padding:12px">
                    <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">
                        <span style="color:#10b981">●</span>
                        <span style="color:#e2e8f0;font-size:0.85em;font-weight:600">Ollama — gemma2:2b</span>
                    </div>
                    <div style="color:#475569;font-size:0.76em;line-height:1.6">
                        ≈ 1.6GB VRAM · 6GB VRAM uyumlu<br>
                        Few-Shot yönlendirme + JSON mode<br>
                        Fallback: Kural tabanlı yönlendirme
                    </div>
                </div>
                """)

            # ── Sağ Panel ────────────────────────────────────────────────────
            with gr.Column(scale=2):

                durum_html   = gr.HTML(value='<div style="color:#475569;text-align:center;padding:14px">Pipeline henüz çalıştırılmadı.</div>', elem_id="durum_html")
                evrak_id_html = gr.HTML(value="", elem_id="evrak_id_html")

                with gr.Tabs(elem_id="sonuc_tabs"):

                    with gr.Tab("📄 Taslak"):
                        taslak_html = gr.HTML(
                            value='<div style="color:#475569;padding:30px;text-align:center">Pipeline sonucu burada görünecek...</div>',
                            elem_id="taslak_html",
                        )

                    with gr.Tab("🎯 Yönlendirme"):
                        routing_html = gr.HTML(value=_routing_card(None), elem_id="routing_html")

                    with gr.Tab("📝 Eksik Bilgi"):
                        eksik_info_html = gr.HTML(value="", elem_id="eksik_info_html")
                        # Bu grup EKSIK_BILGI senaryosunda visible=True yapılır
                        with gr.Group(visible=False) as eksik_form_group:
                            gr.Markdown("**Lütfen tespit edilen eksik alanları doldurun:**")
                            tc_input   = gr.Textbox(label="TC Kimlik No",      placeholder="12345678901", elem_id="tc_input")
                            gond_input = gr.Textbox(label="Gönderici Adı",     placeholder="Ahmet Yılmaz", elem_id="gond_input")
                            konu_input = gr.Textbox(label="Konu (isteğe bağlı)", placeholder="Evrak konusu...", elem_id="konu_input")
                            eksik_btn  = gr.Button("✅ Gönder ve Devam Et", variant="primary", elem_id="eksik_btn")

                    with gr.Tab("⚠️ İnsan Onayı"):
                        onay_html = gr.HTML(value='<div style="color:#475569;text-align:center;padding:20px">Bu sekmede insan onayı gerektiren evraklar görünür.</div>', elem_id="onay_html")
                        with gr.Group(visible=False) as onay_butonlar:
                            with gr.Row():
                                onayla_btn = gr.Button("✅ Onayla", variant="primary",   elem_id="onayla_btn")
                                reddet_btn = gr.Button("❌ Reddet", variant="stop",      elem_id="reddet_btn")

                    with gr.Tab("📊 Log"):
                        log_html = gr.HTML(value='<span style="color:#475569;font-size:0.85em">Log kaydı bekleniyor.</span>', elem_id="log_html")

                with gr.Tab("🔧 JSON"):
                        json_out = gr.Code(value="{}", language="json", label="Agent4_Nihai_Cikti_Semasi_v1", elem_id="json_out")

        # Mod chip — sağ üstte gösterilecek
        mod_chip_html = gr.HTML(value="", elem_id="mod_chip_html")

        gr.HTML("""
        <div style="text-align:center;padding:12px 0 4px;color:#334155;font-size:0.76em">
            TEKNOFEST TYDA 2026 · ENELPİ · Agent 4 ·
            <span style="color:#4f8ef7">LangGraph</span> +
            <span style="color:#8b5cf6">Ollama</span> +
            <span style="color:#10b981">Gradio 6</span>
        </div>
        """)

        # ── Çıktı listesi (sıra önemli!) ─────────────────────────────────────
        _out = [
            pipeline_steps,   # 0
            durum_html,       # 1
            evrak_id_html,    # 2
            taslak_html,      # 3
            routing_html,     # 4
            eksik_info_html,  # 5
            eksik_form_group, # 6
            onay_html,        # 7
            onay_butonlar,    # 8
            log_html,         # 9
            json_out,         # 10
            session_state,    # 11
            mod_chip_html,    # 12
        ]

        # ── Event handler'lar ─────────────────────────────────────────────────
        calistir_btn.click(fn=handle_run,          inputs=[senaryo_radio, session_state], outputs=_out)
        temizle_btn.click( fn=handle_temizle,      inputs=[session_state],               outputs=_out)
        eksik_btn.click(   fn=handle_eksik_submit, inputs=[tc_input, gond_input, konu_input, session_state], outputs=_out)
        onayla_btn.click(  fn=lambda s: handle_approval("ONAYLA", s), inputs=[session_state], outputs=_out)
        reddet_btn.click(  fn=lambda s: handle_approval("REDDET", s), inputs=[session_state], outputs=_out)
        gercek_calistir_btn.click(fn=handle_gercek_run, inputs=[dosya_input, session_state], outputs=_out)

    return demo


if __name__ == "__main__":
    app = create_app()
    app.launch(  # type: ignore[call-arg]
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True,
        css=CUSTOM_CSS,              # type: ignore[call-arg]
        theme=gr.themes.Base(        # type: ignore[call-arg]
            primary_hue="blue",
            neutral_hue="slate",
            font=[gr.themes.GoogleFont("Inter"), "ui-sans-serif", "system-ui"],
        ),
    )
