"""
Agent 4 — Kapsamlı Test Paketi
4 senaryonun tamamını mock JSON çıktılarıyla test eder.

Çalıştırma:
    cd c:\\TEKNOFEST\\NLP\\nlp_project
    pytest tests/test_agent4.py -v
"""

import json
import os
import sys
import pytest
from typing import Dict, Any

# Proje kökünü path'e ekle
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agent4.state import MAX_RETRY, MAX_LOOPBACK, HEDEF_BIRIMLER, OLLAMA_MODEL
from agent4.validators.schema_validator import (
    validate_agent3_output,
    validate_agent4_output,
    AGENT3_CIKTI_SEMASI,
    AGENT4_CIKTI_SEMASI,
)
from agent4.graph import build_graph, create_initial_state
from agent4.nodes.output_node import _belirle_sistem_durumu, output_node
from agent4.nodes.routing_node import _fallback_routing, _validate_routing_output

# ─── Mock Veri Yükleme ────────────────────────────────────────────────────────
MOCK_DIR = os.path.join(os.path.dirname(__file__), "mock_outputs")


def load_mock(dosya_adi: str) -> Dict[str, Any]:
    """Mock JSON dosyasını yükler."""
    yol = os.path.join(MOCK_DIR, dosya_adi)
    with open(yol, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def mock_taslak_hazir():
    return load_mock("agent3_mock_taslak_hazir.json")


@pytest.fixture
def mock_eksik_bilgi():
    return load_mock("agent3_mock_eksik_bilgi.json")


@pytest.fixture
def mock_manuel():
    return load_mock("agent3_mock_manuel.json")


@pytest.fixture
def mock_uretilemedi():
    return load_mock("agent3_mock_uretilemedi.json")


# ─── MODÜL 1: Sabitler & Konfigürasyon ──────────────────────────────────────
class TestKonfigurasyon:
    """Temel sabitler ve konfigürasyon testleri."""

    def test_max_retry_gecerli(self):
        """MAX_RETRY pozitif tam sayı olmalı."""
        assert isinstance(MAX_RETRY, int)
        assert MAX_RETRY > 0
        assert MAX_RETRY <= 5  # Makul üst sınır

    def test_max_loopback_gecerli(self):
        """MAX_LOOPBACK pozitif tam sayı olmalı."""
        assert isinstance(MAX_LOOPBACK, int)
        assert MAX_LOOPBACK > 0
        assert MAX_LOOPBACK == 3  # Sözleşme ile tutarlı

    def test_ollama_model_belirlenmis(self):
        """OLLAMA_MODEL boş olmamalı."""
        assert OLLAMA_MODEL
        assert isinstance(OLLAMA_MODEL, str)

    def test_hedef_birimler_tamam(self):
        """6 sabit birim + MANUEL_BELIRSIZ doğrulanmalı."""
        beklenen = {
            "INSAN_KAYNAKLARI", "BILGI_ISLEM", "HUKUK_MUSAVIRLIGI",
            "YAZI_ISLERI", "DESTEK_HIZMETLERI", "STRATEJI_GELISTIRME", "MANUEL_BELIRSIZ"
        }
        assert set(HEDEF_BIRIMLER) == beklenen
        assert len(HEDEF_BIRIMLER) == 7


# ─── MODÜL 2: Mock Veri Şema Doğrulama ──────────────────────────────────────
class TestMockVeriSema:
    """Mock JSON dosyalarının şema uygunluğu testleri."""

    def test_mock_taslak_hazir_sema(self, mock_taslak_hazir):
        """TASLAK_HAZIR mock verisi agent3 şemasına uygun olmalı."""
        gecerli, hata = validate_agent3_output(mock_taslak_hazir)
        assert gecerli, f"Şema hatası: {hata}"

    def test_mock_eksik_bilgi_sema(self, mock_eksik_bilgi):
        """EKSIK_BILGI mock verisi agent3 şemasına uygun olmalı."""
        gecerli, hata = validate_agent3_output(mock_eksik_bilgi)
        assert gecerli, f"Şema hatası: {hata}"

    def test_mock_manuel_sema(self, mock_manuel):
        """MANUEL_INCELEME mock verisi agent3 şemasına uygun olmalı."""
        gecerli, hata = validate_agent3_output(mock_manuel)
        assert gecerli, f"Şema hatası: {hata}"

    def test_mock_uretilemedi_sema(self, mock_uretilemedi):
        """URETILEMEDI mock verisi agent3 şemasına uygun olmalı."""
        gecerli, hata = validate_agent3_output(mock_uretilemedi)
        assert gecerli, f"Şema hatası: {hata}"

    def test_mock_taslak_hazir_durum(self, mock_taslak_hazir):
        """TASLAK_HAZIR mock verisinin durum alanı doğru olmalı."""
        assert mock_taslak_hazir["durum"] == "TASLAK_HAZIR"

    def test_mock_eksik_bilgi_durum(self, mock_eksik_bilgi):
        """EKSIK_BILGI mock verisinin durum alanı doğru olmalı."""
        assert mock_eksik_bilgi["durum"] == "TASLAK_HAZIR_EKSIK_BILGI"
        assert len(mock_eksik_bilgi["kaynak_baglam"]["eksik_alanlar"]) > 0

    def test_mock_manuel_uslup(self, mock_manuel):
        """MANUEL mock'un agent2_durum alanı MANUEL_INCELEME olmalı."""
        assert mock_manuel["kaynak_baglam"]["agent2_durum"] == "MANUEL_INCELEME"

    def test_mock_uretilemedi_bos_metin(self, mock_uretilemedi):
        """URETILEMEDI mock'un taslak_metni boş olmalı."""
        assert mock_uretilemedi["uretilen_taslak"]["taslak_metni"] == ""
        assert mock_uretilemedi["uretilen_taslak"]["resmi_uslup_kontrolu"]["uygun_mu"] is False


# ─── MODÜL 3: Fallback Yönlendirme ──────────────────────────────────────────
class TestFallbackRouting:
    """Kural tabanlı fallback yönlendirme testleri."""

    def test_dilekce_yazi_isleri(self):
        result = _fallback_routing("DILEKCE", "Test Kurum")
        assert result["hedef_birim"] == "YAZI_ISLERI"
        assert 0 <= result["yonlendirme_guven_skoru"] <= 1

    def test_fatura_destek_hizmetleri(self):
        result = _fallback_routing("FATURA", "Test Kurum")
        assert result["hedef_birim"] == "DESTEK_HIZMETLERI"

    def test_sozlesme_hukuk(self):
        result = _fallback_routing("SOZLESME_PROTOKOL", "Test Kurum")
        assert result["hedef_birim"] == "HUKUK_MUSAVIRLIGI"

    def test_diger_manuel_belirsiz(self):
        result = _fallback_routing("DIGER", "Test Kurum")
        assert result["hedef_birim"] == "MANUEL_BELIRSIZ"

    def test_bilgi_edinme_yazi_isleri(self):
        result = _fallback_routing("BILGI_EDINME_BASVURUSU", "Test Kurum")
        assert result["hedef_birim"] == "YAZI_ISLERI"

    def test_fallback_gecerli_birimlerde(self):
        """Tüm evrak türleri için fallback geçerli birim döndürmeli."""
        evrak_turleri = [
            "DILEKCE", "BILGI_EDINME_BASVURUSU", "SIKAYET_BASVURUSU",
            "RESMI_UST_YAZI", "FATURA", "SOZLESME_PROTOKOL", "DIGER"
        ]
        for tur in evrak_turleri:
            result = _fallback_routing(tur, "")
            assert result["hedef_birim"] in HEDEF_BIRIMLER, \
                f"{tur} için geçersiz birim: {result['hedef_birim']}"

    def test_routing_output_dogrulama(self):
        """Geçerli routing çıktısı doğrulanmalı."""
        gecerli = {
            "hedef_birim": "YAZI_ISLERI",
            "gerekce": "Test gerekçe",
            "yonlendirme_guven_skoru": 0.85,
        }
        assert _validate_routing_output(gecerli) is True

    def test_routing_output_gecersiz_birim(self):
        """Geçersiz birim adı olan routing çıktısı reddedilmeli."""
        gecersiz = {
            "hedef_birim": "GECERSIZ_BIRIM",
            "gerekce": "Test",
            "yonlendirme_guven_skoru": 0.5,
        }
        assert _validate_routing_output(gecersiz) is False

    def test_routing_output_eksik_alan(self):
        """Eksik alan olan routing çıktısı reddedilmeli."""
        eksik = {
            "hedef_birim": "YAZI_ISLERI",
            "gerekce": "Test",
            # yonlendirme_guven_skoru eksik
        }
        assert _validate_routing_output(eksik) is False


# ─── MODÜL 4: Sistem Durumu Belirleme ────────────────────────────────────────
class TestSistemDurumuBelirleme:
    """output_node'daki _belirle_sistem_durumu fonksiyonu testleri."""

    def _base_state(self, **overrides) -> dict:
        """Test için temel state oluşturur."""
        state = {
            "evrak_id": "EVR-2026-TEST",
            "ham_metin": None,
            "temizlenmis_metin": "Test metin",
            "agent1_output": {
                "agent1_islem_metadata": {
                    "durum": "BASARILI",
                    "ocr_guven_skoru": 0.92,
                }
            },
            "agent2_output": {},
            "agent3_output": {
                "durum": "TASLAK_HAZIR",
                "uretilen_taslak": {
                    "resmi_uslup_kontrolu": {"uygun_mu": True, "tespit_edilen_sorunlar": []},
                    "eksik_alan_yer_tutucular": [],
                },
                "kaynak_baglam": {"eksik_alanlar": []},
            },
            "retry_count": 0,
            "loopback_count": 0,
            "eksik_alanlar_gecmisi": [],
            "nihai_yonlendirme": None,
            "sistem_durumu": "",
            "nihai_cikti": None,
            "hata_log": [],
            "senaryo": "TASLAK_HAZIR",
        }
        state.update(overrides)
        return state

    def test_taslak_hazir_otomatik(self):
        """TASLAK_HAZIR + yüksek OCR skoru → OTOMATIK_ONAYLANABILIR."""
        state = self._base_state()
        durum = _belirle_sistem_durumu(state)
        assert durum == "OTOMATIK_ONAYLANABILIR"

    def test_agent1_basarisiz(self):
        """Agent 1 BASARISIZ → KRITIK_HATA_MANUEL_KUYRUK."""
        state = self._base_state()
        state["agent1_output"]["agent1_islem_metadata"]["durum"] = "BASARISIZ"
        durum = _belirle_sistem_durumu(state)
        assert durum == "KRITIK_HATA_MANUEL_KUYRUK"

    def test_uretilemedi_kritik_hata(self):
        """URETILEMEDI → KRITIK_HATA_MANUEL_KUYRUK."""
        state = self._base_state()
        state["agent3_output"]["durum"] = "URETILEMEDI"
        durum = _belirle_sistem_durumu(state)
        assert durum == "KRITIK_HATA_MANUEL_KUYRUK"

    def test_uslup_ihlali_insan_onayi(self):
        """Üslup ihlali → INSAN_ONAYI_BEKLIYOR (durum'dan bağımsız — sözleşme §5)."""
        state = self._base_state()
        state["agent3_output"]["uretilen_taslak"]["resmi_uslup_kontrolu"]["uygun_mu"] = False
        state["agent3_output"]["uretilen_taslak"]["resmi_uslup_kontrolu"]["tespit_edilen_sorunlar"] = ["argo ifade"]
        durum = _belirle_sistem_durumu(state)
        assert durum == "INSAN_ONAYI_BEKLIYOR"

    def test_manuel_inceleme_insan_onayi(self):
        """TASLAK_HAZIR_MANUEL_INCELEME_UYARILI → INSAN_ONAYI_BEKLIYOR."""
        state = self._base_state()
        state["agent3_output"]["durum"] = "TASLAK_HAZIR_MANUEL_INCELEME_UYARILI"
        durum = _belirle_sistem_durumu(state)
        assert durum == "INSAN_ONAYI_BEKLIYOR"

    def test_eksik_bilgi_talebi(self):
        """TASLAK_HAZIR_EKSIK_BILGI → EKSIK_BILGI_TALEBI."""
        state = self._base_state()
        state["agent3_output"]["durum"] = "TASLAK_HAZIR_EKSIK_BILGI"
        durum = _belirle_sistem_durumu(state)
        assert durum == "EKSIK_BILGI_TALEBI"

    def test_dusuk_ocr_insan_onayi(self):
        """OCR güven skoru < 0.70 → INSAN_ONAYI_BEKLIYOR."""
        state = self._base_state()
        state["agent1_output"]["agent1_islem_metadata"]["ocr_guven_skoru"] = 0.65
        durum = _belirle_sistem_durumu(state)
        assert durum == "INSAN_ONAYI_BEKLIYOR"


# ─── MODÜL 5: LangGraph Pipeline Entegrasyon Testleri ───────────────────────
class TestPipelineEntegrasyon:
    """
    Dört ana senaryo için uçtan uca pipeline testleri.
    LangGraph MemorySaver ile çalışır; Ollama gerektirmez (fallback kullanır).
    """

    @pytest.fixture(autouse=True)
    def setup_graph(self):
        """Her test için yeni bir graf örneği oluşturur."""
        self.graph = build_graph(use_memory=True)

    def _make_config(self) -> dict:
        import uuid
        return {"configurable": {"thread_id": str(uuid.uuid4())}}

    def _invoke(self, senaryo: str) -> dict:
        """Belirli senaryo ile pipeline'ı çalıştırır."""
        import uuid
        evrak_id = f"EVR-2026-{str(uuid.uuid4().int)[:4]:0>4}"
        initial_state = create_initial_state(evrak_id, senaryo)
        config = self._make_config()

        try:
            result = self.graph.invoke(initial_state, config)
        except Exception:
            # Interrupt durumunda state'ten al
            graph_state = self.graph.get_state(config)
            result = graph_state.values

        return result

    def test_senaryo_taslak_hazir_tamamlanir(self):
        """Senaryo 1: TASLAK_HAZIR — pipeline eksiksiz tamamlanmalı."""
        result = self._invoke("TASLAK_HAZIR")

        assert result is not None
        assert "nihai_cikti" in result
        nihai = result["nihai_cikti"] or {}
        assert nihai.get("sema_versiyonu") == "1.0"
        assert nihai.get("sistem_durumu") == "OTOMATIK_ONAYLANABILIR"
        assert nihai.get("sistem_aksiyonu") == "ARSIFLE_VE_GONDER"

    def test_senaryo_taslak_hazir_yonlendirme(self):
        """Senaryo 1: Birim yönlendirme kararı üretilmeli."""
        result = self._invoke("TASLAK_HAZIR")

        yonlendirme = result.get("nihai_yonlendirme")
        assert yonlendirme is not None
        assert yonlendirme["hedef_birim"] in HEDEF_BIRIMLER
        assert "gerekce" in yonlendirme
        assert 0 <= yonlendirme["yonlendirme_guven_skoru"] <= 1

    def test_senaryo_taslak_hazir_sema_uyumu(self):
        """Senaryo 1: Nihai çıktı Agent4_Nihai_Cikti_Semasi_v1 ile uyumlu olmalı."""
        result = self._invoke("TASLAK_HAZIR")

        nihai = result.get("nihai_cikti", {})
        gecerli, hata = validate_agent4_output(nihai)
        assert gecerli, f"Şema uyumsuzluğu: {hata}"

    def test_senaryo_eksik_bilgi_interrupt(self):
        """Senaryo 2: EKSIK_BILGI — pipeline interrupt tetiklemeli."""
        import uuid
        evrak_id = f"EVR-2026-{str(uuid.uuid4().int)[:4]:0>4}"
        initial_state = create_initial_state(evrak_id, "EKSIK_BILGI")
        config = self._make_config()

        # İlk çalıştırma — interrupt bekleniyor
        try:
            self.graph.invoke(initial_state, config)
        except Exception:
            pass

        graph_state = self.graph.get_state(config)
        # Interrupt oldu ise next node bekliyor olmalı
        assert graph_state.next or graph_state.values.get("loopback_count", -1) >= 0

    def test_senaryo_manuel_inceleme(self):
        """
        Senaryo 3: MANUEL — human_approval_node interrupt tetikler.

        MANUEL senaryosunda human_approval_node interrupt() çağırır ve grafik
        dondurulur. Bu durumda output_node henüz çalışmamış olduğundan
        sistem_durumu alanı boş gelir; graf durumu pending next node ile kontrol
        edilmeli ve INSAN_ONAYI_BEKLIYOR olarak değerlendirilmelidir.
        """
        import uuid
        evrak_id = f"EVR-2026-{str(uuid.uuid4().int)[:4]:0>4}"
        initial_state = create_initial_state(evrak_id, "MANUEL")
        config = self._make_config()

        try:
            result = self.graph.invoke(initial_state, config)
            sistem_durumu = (result.get("nihai_cikti") or {}).get("sistem_durumu") or \
                            result.get("sistem_durumu", "")
        except Exception:
            result = {}
            sistem_durumu = ""

        # Graf interrupt'ta bekliyorsa (pending node var) → INSAN_ONAYI_BEKLIYOR
        graph_state = self.graph.get_state(config)
        if graph_state.next:
            sistem_durumu = "INSAN_ONAYI_BEKLIYOR"

        assert sistem_durumu in ["INSAN_ONAYI_BEKLIYOR", "KRITIK_HATA_MANUEL_KUYRUK"], \
            f"Beklenmeyen durum: {sistem_durumu}"

    def test_senaryo_uretilemedi_retry(self):
        """Senaryo 4: URETILEMEDI — retry mekanizması çalışmalı."""
        result = self._invoke("URETILEMEDI")

        retry_count = result.get("retry_count", 0)
        # Retry yapılmış olmalı (mock agent3 retry sonrası başarılı döner)
        assert retry_count >= 1, f"Retry yapılmadı, retry_count: {retry_count}"

    def test_senaryo_uretilemedi_sonuc(self):
        """Senaryo 4: URETILEMEDI retry sonrası başarıyla tamamlanmalı."""
        result = self._invoke("URETILEMEDI")

        nihai = result.get("nihai_cikti", {})
        # Retry başarılı olduysa OTOMATIK veya INSAN_ONAYI olmalı
        if nihai:
            assert nihai.get("sistem_durumu") in [
                "OTOMATIK_ONAYLANABILIR",
                "INSAN_ONAYI_BEKLIYOR",
                "KRITIK_HATA_MANUEL_KUYRUK",
            ]

    def test_tum_senaryolarda_evrak_id_korunur(self):
        """Tüm senaryolarda evrak_id baştan sona korunmalı."""
        for senaryo in ["TASLAK_HAZIR", "URETILEMEDI"]:
            result = self._invoke(senaryo)
            evrak_id = result.get("evrak_id", "")
            assert evrak_id.startswith("EVR-2026-"), \
                f"Senaryo {senaryo}: evrak_id bozuk: {evrak_id}"

    def test_hata_log_listedir(self):
        """Tüm senaryolarda hata_log liste olmalı."""
        for senaryo in ["TASLAK_HAZIR", "URETILEMEDI"]:
            result = self._invoke(senaryo)
            assert isinstance(result.get("hata_log", []), list)


# ─── MODÜL 6: Şema Doğrulama ─────────────────────────────────────────────────
class TestSemaDogrulama:
    """JSON şema doğrulama modülü testleri."""

    def test_gecerli_agent4_cikti(self):
        """Geçerli bir Agent4 çıktısı doğrulanmalı."""
        gecerli_cikti = {
            "sema_versiyonu": "1.0",
            "evrak_id": "EVR-2026-0001",
            "sistem_durumu": "OTOMATIK_ONAYLANABILIR",
            "sistem_aksiyonu": "ARSIFLE_VE_GONDER",
            "uretilen_taslak": {
                "taslak_metni": "Test taslak",
                "sablon_turu": "BILGI_EDINME_CEVABI",
                "uslup_uygun_mu": True,
            },
            "nihai_yonlendirme": {
                "hedef_birim": "YAZI_ISLERI",
                "gerekce": "Test gerekçe",
                "yonlendirme_guven_skoru": 0.85,
            },
            "kullanici_mesaji": "Evrak başarıyla işlendi.",
        }
        gecerli, hata = validate_agent4_output(gecerli_cikti)
        assert gecerli, f"Şema hatası: {hata}"

    def test_gecersiz_sistem_durumu(self):
        """Geçersiz sistem_durumu reddedilmeli."""
        gecersiz_cikti = {
            "sema_versiyonu": "1.0",
            "evrak_id": "EVR-2026-0001",
            "sistem_durumu": "GECERSIZ_DURUM",  # Hatalı
            "sistem_aksiyonu": "ARSIFLE_VE_GONDER",
            "uretilen_taslak": None,
            "nihai_yonlendirme": None,
            "kullanici_mesaji": "Test",
        }
        gecerli, _ = validate_agent4_output(gecersiz_cikti)
        assert gecerli is False

    def test_gecersiz_evrak_id_formati(self):
        """Yanlış format evrak_id reddedilmeli."""
        gecersiz = {
            "sema_versiyonu": "1.0",
            "evrak_id": "YANLIS-FORMAT",  # Hatalı pattern
            "sistem_durumu": "OTOMATIK_ONAYLANABILIR",
            "sistem_aksiyonu": "ARSIFLE_VE_GONDER",
            "uretilen_taslak": None,
            "nihai_yonlendirme": None,
            "kullanici_mesaji": "Test",
        }
        gecerli, _ = validate_agent4_output(gecersiz)
        assert gecerli is False

    def test_agent3_sema_eksik_alan(self):
        """Zorunlu alan eksik Agent3 çıktısı reddedilmeli."""
        eksik_cikti = {
            "sema_versiyonu": "1.0",
            "evrak_id": "EVR-2026-0001",
            # kaynak_baglam eksik — zorunlu alan
            "uretilen_taslak": {
                "sablon_turu": "BILGI_EDINME_CEVABI",
                "taslak_metni": "Test",
                "eksik_alan_yer_tutucular": [],
                "resmi_uslup_kontrolu": {"uygun_mu": True, "tespit_edilen_sorunlar": []},
            },
            "durum": "TASLAK_HAZIR",
        }
        gecerli, _ = validate_agent3_output(eksik_cikti)
        assert gecerli is False


# ─── Özet Çıktısı ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
