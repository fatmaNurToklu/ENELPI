"""
Agent 4 — Ana Başlatıcı
TEKNOFEST TYDA 2026 — ENELPİ Takımı

Kullanım:
    python run.py          → Gradio arayüzünü başlatır (varsayılan)
    python run.py --test   → Pytest test paketini çalıştırır
    python run.py --cli    → CLI modunda belirli bir senaryoyu çalıştırır
"""

import sys
import os
import logging

# Proje kökü
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("agent4.run")


def run_ui():
    """Gradio arayüzünü başlatır."""
    import gradio as gr
    from agent4.ui.app import create_app, CUSTOM_CSS
    logger.info("Gradio arayüzü başlatılıyor...")
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


def run_streamlit():
    """Streamlit arayüzünü başlatır."""
    import subprocess
    logger.info("Streamlit arayüzü başlatılıyor...")
    streamlit_path = os.path.join(BASE_DIR, "app_streamlit.py")
    
    # CORS ve XSRF korumasını kapat (dosya yükleme 400 hatasını önler)
    os.environ["STREAMLIT_SERVER_ENABLE_CORS"] = "false"
    os.environ["STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION"] = "false"
    os.environ["STREAMLIT_SERVER_MAX_UPLOAD_SIZE"] = "200"
    
    try:
        subprocess.run([
            "streamlit", "run", streamlit_path,
            "--server.enableCORS=false",
            "--server.enableXsrfProtection=false",
            "--server.maxUploadSize=200",
        ])
    except KeyboardInterrupt:
        logger.info("Streamlit arayüzü kapatıldı.")
    except Exception as e:
        logger.error("Streamlit başlatılamadı: %s", e)


def run_tests():
    """Pytest test paketini çalıştırır."""
    import pytest
    logger.info("Test paketi çalıştırılıyor...")
    exit_code = pytest.main([
        os.path.join(BASE_DIR, "tests", "test_agent4.py"),
        "-v",
        "--tb=short",
        "--color=yes",
    ])
    sys.exit(exit_code)


def run_cli(senaryo: str = "TASLAK_HAZIR"):
    """CLI modunda belirli bir senaryoyu çalıştırır ve sonucu yazdırır."""
    import json
    import uuid

    logger.info("CLI modu — Senaryo: %s", senaryo)

    from agent4.graph import build_graph, create_initial_state

    graph = build_graph(use_memory=True)
    evrak_id = f"EVR-2026-{str(uuid.uuid4().int)[:4]:0>4}"
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    initial_state = create_initial_state(evrak_id, senaryo)

    print(f"\n{'='*60}")
    print(f"  Agent 4 CLI — Senaryo: {senaryo}")
    print(f"  Evrak ID: {evrak_id}")
    print(f"{'='*60}\n")

    try:
        result = graph.invoke(initial_state, config)

        nihai = result.get("nihai_cikti", {})
        if nihai:
            print("📋 NİHAİ ÇIKTI:")
            print(json.dumps(nihai, ensure_ascii=False, indent=2))
        else:
            print("⚠️  Nihai çıktı üretilemedi (interrupt durumunda olabilir).")
            print("Sistem durumu:", result.get("sistem_durumu", "—"))

        print(f"\n{'─'*40}")
        print("🔍 PIPELINE LOG:")
        for log in result.get("hata_log", []):
            print(f"  › {log}")

    except Exception as e:
        graph_state = graph.get_state(config)
        if graph_state.next:
            print("⏸️  INTERRUPT: Graf donduruldu — Eksik bilgi veya insan onayı bekleniyor.")
            print("   Bekleyen node:", graph_state.next)
            print("   (Gradio arayüzünü kullanarak devam edebilirsiniz.)")
        else:
            logger.exception("CLI hatası: %s", e)
            raise


if __name__ == "__main__":
    args = sys.argv[1:]

    if "--test" in args:
        run_tests()
    elif "--cli" in args:
        senaryo = "TASLAK_HAZIR"
        # --senaryo argümanı varsa al
        for i, arg in enumerate(args):
            if arg == "--senaryo" and i + 1 < len(args):
                senaryo = args[i + 1]
                break
        run_cli(senaryo)
    elif "--gradio" in args:
        run_ui()
    else:
        run_streamlit()
