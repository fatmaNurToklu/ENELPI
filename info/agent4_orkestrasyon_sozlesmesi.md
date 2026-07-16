# Agent 4 Orkestrasyon & Yönlendirme Sözleşmesi
**Şema versiyonu:** 1.0 · **Kapsam:** Yasin (Agent 4 — Yönlendirme Kararı & Orkestrasyon) → Sistem Nihai Çıktısı & Kullanıcı Arayüzü Katmanı
**Şartname referansı:** Madde 6.4.2 (Görev 2: Resmî Yazı Taslaklama ve Birim Yönlendirme) ve Madde 6.1–6.4 (Çoklu Ajan Entegrasyonu)

> Diğer ajanların girdi/çıktı şemaları için bkz. `agent1_agent2_veri_sozlesmesi.md`, `agent2_agent3_veri_sozlesmesi.md` ve `agent3_agent4_veri_sozlesmesi.md`. Bu sözleşme, Agent 4'ün tüm pipeline'ı (LangGraph) nasıl koordine edeceğini, gelen taslakları nasıl tüketeceğini, nihai yönlendirme kararını nasıl vereceğini ve arayüz/insan katmanıyla nasıl etkileşime gireceğini tanımlar.

---

## 1. Sorumluluk sınırı ve rol tanımı

Şartname Görev 2 kapsamında birim yönlendirme, süreç bilgilendirmesi ve eksik bilgi yönetimini merkezi bir role bağlamıştır. Ajanlar arası iş bölümüne göre Agent 4'ün üstlendiği kritik görevler şunlardır:

| Yetenek (Şartname 6.4.2) | Sorumlu ajan / bileşen | Bu sözleşmedeki karşılığı |
|---|---|---|
| Çoklu ajan orkestrasyonu | **Agent 4** (LangGraph) | Şema durum yönetimi (§2) ve grafik akış mantığı (§5) |
| Doğru birime yönlendirme önerisi | **Agent 4** (Yönlendirici LLM) | `nihai_yonlendirme.hedef_birim` ve prompt yapısı (§4) |
| Kullanıcıya süreç bilgilendirmesi | **Agent 4** (Arayüz/UI) | `sistem_aksiyonu` ve `kullanici_mesaji` |
| Eksik bilgi talep etme & kesinti | **Agent 4** (LangGraph Interrupt) | Arayüz döngüsü ve durum güncelleme mantığı (§6) |
| İnsan onay kuyruğu yönetimi | **Agent 4** (UI & Orkestrasyon) | `durum: INSAN_ONAYI_BEKLIYOR` |

**Altın kural:** Agent 4, kendisinden önceki tüm ajanların (Agent 1, 2 ve 3) çıktılarını birleştiren ve sistemin dış dünyaya (kullanıcıya/veritabanına) açılan tek kapısıdır. Agent 4 kendi başına yeniden sınıflandırma veya ham metinden mevzuat çıkarma işlemlerini **tetiklemez**; ancak önceki ajanlardan gelen hata sinyallerine (`URETILEMEDI` veya üslup ihlali vb.) göre akıllı yeniden deneme (retry) veya insana yönlendirme kararlarını yönetir.

---

## 2. LangGraph ortak durum şeması (State Definition)

Tüm çoklu ajan sisteminin durumunu (State) merkezi olarak yönetmek ve ajanlar arası veri taşınmasını sağlamak amacıyla tasarlanan LangGraph `AgentState` yapısı aşağıdadır. Bu yapı, Agent 4'ün orkestrasyon katmanının temelini oluşturur.

```python
from typing import TypedDict, List, Optional, Dict, Any

class AgentState(TypedDict):
    # Temel Evrak Bilgileri
    evrak_id: str                          # Format: EVR-YYYY-XXXX
    ham_metin: Optional[str]               # OCR öncesi ham metin (hata ayıklama için)
    temizlenmis_metin: Optional[str]       # Agent 1'den gelen temiz metin

    # Ajan Girdi/Çıktı Blokları (Sözleşme Nesneleri)
    agent1_output: Optional[Dict[str, Any]] # agent1_agent2_veri_sozlesmesi şeması
    agent2_output: Optional[Dict[str, Any]] # agent2_agent3_veri_sozlesmesi şeması
    agent3_output: Optional[Dict[str, Any]] # agent3_agent4_veri_sozlesmesi şeması

    # Orkestrasyon Kontrol Metrikleri
    retry_count: int                       # Agent 3 veya OCR için yeniden deneme sayısı
    eksik_alanlar_gecmisi: List[str]       # Kullanıcıdan tamamlanan eksik alanların takibi

    # Nihai Karar ve Sistem Çıktıları
    nihai_yonlendirme: Optional[Dict[str, Any]] # Hedef birim, gerekçe ve güven skoru
    sistem_durumu: str                     # OTOMATIK_ONAY, INSAN_ONAYI, EKSIK_BILGI, MANUEL_KUYRUK
```

---

## 3. Sistem durum yönetimi ve JSON çıktı şeması (v1.0)

Agent 4, tüm boru hattı (pipeline) tamamlandığında veya bir kesinti (interrupt) anında dış dünyaya ve kullanıcı arayüzüne (UI) aşağıdaki JSON şemasını üretmekle yükümlüdür.

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Agent4_Nihai_Cikti_Semasi_v1",
  "type": "object",
  "required": ["sema_versiyonu", "evrak_id", "sistem_durumu", "sistem_aksiyonu", "uretilen_taslak", "nihai_yonlendirme", "kullanici_mesaji"],
  "properties": {
    "sema_versiyonu": { "type": "string", "const": "1.0" },
    "evrak_id": { "type": "string", "pattern": "^EVR-[0-9]{4}-[0-9]{4,}$" },

    "sistem_durumu": {
      "type": "string",
      "enum": ["OTOMATIK_ONAYLANABILIR", "INSAN_ONAYI_BEKLIYOR", "EKSIK_BILGI_TALEBI", "KRITIK_HATA_MANUEL_KUYRUK"],
      "description": "Sistemin uçtan uca değerlendirme sonucundaki nihai durum kapısı."
    },

    "sistem_aksiyonu": {
      "type": "string",
      "enum": ["ARSIFLE_VE_GONDER", "UI_ONAY_EKRANINA_DUSUR", "UI_INPUT_FORMU_AC", "MANUEL_INCELEME_MASASINA_AT"],
      "description": "Kullanıcı arayüzünün veya tetiklenecek servislerin alacağı aksiyon."
    },

    "uretilen_taslak": {
      "type": ["object", "null"],
      "description": "Agent 3'ten alınan taslak metin bilgileri. Durum KRITIK_HATA ise null olabilir.",
      "properties": {
        "taslak_metni": { "type": "string" },
        "sablon_turu": { "type": "string" },
        "uslup_uygun_mu": { "type": "boolean" }
      }
    },

    "nihai_yonlendirme": {
      "type": ["object", "null"],
      "description": "Agent 4 yönlendirici LLM tarafından üretilen birim kararı.",
      "required": ["hedef_birim", "gerekce", "yonlendirme_guven_skoru"],
      "properties": {
        "hedef_birim": {
          "type": "string",
          "enum": ["INSAN_KAYNAKLARI", "BILGI_ISLEM", "HUKUK_MUSAVIRLIGI", "YAZI_ISLERI", "DESTEK_HIZMETLERI", "STRATEJI_GELISTIRME", "MANUEL_BELIRSIZ"]
        },
        "gerekce": { "type": "string", "description": "Evrak içeriği ve mevzuatla ilişkilendirilmiş yönlendirme gerekçesi." },
        "yonlendirme_guven_skoru": { "type": "number", "minimum": 0, "maximum": 1 }
      }
    },

    "kullanici_mesaji": {
      "type": "string",
      "description": "Kamu personeline arayüzde gösterilecek açıklayıcı, yönlendirici ve bilgilendirici metin."
    }
  }
}
```

---

## 4. Birim yönlendirme mantığı ve prompt yapısı

Agent 4, evrakın kurum içi yönlendirmesini yaparken serbest tahminleme yerine, Agent 2'nin ürettiği `ozet`, `konu` ve `alici_kurum` verilerini baz alan **Few-Shot Prompting + Structured Output** mimarisini kullanır. Yönlendirme kararı verilirken Agent 2'nin vektör veritabanından çektiği mevzuat maddelerinin içeriği de bağlama eklenerek hukuki gerekçe güçlendirilir.

**Referans prompt şablonu:**

```
Sistem: Sen bir kamu kurumu akıllı evrak yönlendirme ajanısın. Görevin, gelen evrakın
içeriğini, konusunu ve ilişkili mevzuatı analiz ederek belgeyi incelemesi gereken en
doğru iç birimi seçmek ve gerekçelendirmektir.

Seçebileceğin Hedef Birimler ve Görev Alanları:
1. INSAN_KAYNAKLARI: Personel alımı, özlük hakları, izinler, tayinler ve eğitim süreçleri.
2. BILGI_ISLEM: Yazılım, donanım, ağ altyapısı, siber güvenlik, sistem erişim talepleri.
3. HUKUK_MUSAVIRLIGI: Dava dosyaları, ihtarnameler, sözleşme ve protokol incelemeleri.
4. YAZI_ISLERI: Vatandaş dilekçeleri, genel bilgi edinme başvuruları, kurumlar arası resmi üst yazılar.
5. DESTEK_HIZMETLERI: Fatura ödemeleri, bina bakım-onarım, malzeme tedariki, lojistik.

Girdi Verileri:
- Evrak Türü: {evrak_turu}
- Belirtilen Muhatap: {alici_kurum}
- Konu: {konu}
- İçerik Özeti: {ozet}
- Eşleşen Mevzuat: {ilgili_mevzuat}

Kurallar:
- Yanıtını kesinlikle belirtilen JSON şemasına uygun olarak üret.
- Gerekçe alanında evrak içeriği ile seçilen birimin görev alanını doğrudan ilişkilendir.
- Eğer evrak içeriği hiçbir birime uymuyorsa veya çok belirsizse HEDEF_BIRIM olarak
  'MANUEL_BELIRSIZ' seç ve güven skorunu düşük tut.
```

---

## 5. Grafik akış karar matrisi ve kenar durumları

LangGraph orkestrasyon motorunun, ajanlardan gelen sinyallere göre çalıştıracağı koşullu yönlendirme (Conditional Edges) kuralları ve hata yönetim matrisi aşağıda tanımlanmıştır:

| Girdi durumu (önceki ajan sinyalleri) | Rota kararı | Tetiklenecek arayüz / sistem aksiyonu |
|---|---|---|
| `agent1_output.durum == "BASARISIZ"` | `KRITIK_HATA_MANUEL_KUYRUK` | Evrak doğrudan insan masasına düşer, sonraki ajanlar çalıştırılmaz. |
| `agent3_output.durum == "URETILEMEDI"` & `retry_count < 2` | `AGENT3_RETRY_NODE` | Agent 3'ün sıcaklık (temperature) değeri artırılarak taslak üretimi 1 kez daha denenir. |
| `agent3_output.durum == "URETILEMEDI"` & `retry_count == 2` | `KRITIK_HATA_MANUEL_KUYRUK` | Yeniden deneme başarısız olduğu için evrak doğrudan manuel masaya yönlendirilir. |
| `agent3_output.uretilen_taslak.resmi_uslup_kontrolu.uygun_mu == false` | `INSAN_ONAYI_BEKLIYOR` | Taslak üretilmiştir ancak üslup ihlali (örn: senli benli konuşma) nedeniyle otomatik gönderim kapatılır. |
| `agent3_output.durum == "TASLAK_HAZIR_EKSIK_BILGI"` | `EKSIK_BILGI_TALEBI` | Grafik dondurulur (Interrupt). UI üzerinde form alanı açılarak eksik bilgi beklenir (§6). |
| `agent3_output.durum == "TASLAK_HAZIR"` & `ocr_guven_skoru >= 0.70` | `OTOMATIK_ONAYLANABILIR` | Sistem otomatik olarak birim yönlendirmesini yapar ve taslağı onay kuyruğuna alır. |
| `agent3_output.durum == "TASLAK_HAZIR_MANUEL_INCELEME_UYARILI"` | `INSAN_ONAYI_BEKLIYOR` | Taslak ve yönlendirme hazırdır ancak sistem güveni düşük olduğundan kamu personelinin fiziksel onayı istenir. |

---

## 6. Arayüz kesinti (Interrupt) ve eksik bilgi döngüsü

Şartnamede kritik öneme sahip olan "gerektiğinde eksik bilgi talep edebilme" işlevi, LangGraph'in durum tabanlı hafıza (state checkpointer) ve kesinti yetenekleri kullanılarak gerçekleştirilir.

1. **Kesinti noktası (Freeze):** `AgentState` içinde `agent3_output.durum` değeri `TASLAK_HAZIR_EKSIK_BILGI` olarak geldiğinde, LangGraph süreci durdurur ve durumu `EKSIK_BILGI_TALEBI` olarak dışarı fırlatır.
2. **Kullanıcı etkileşimi (UI Input):** Arayüz, `eksik_alan_yer_tutucular` listesinde yer alan alanları (örn. `tc_kimlik`, `gonderici`) kırmızı uyarı çerçevesiyle kamu personeline gösterir ve form girdisi talep eder.
3. **Grafik uyanışı ve geri besleme (Resume & Loopback):** Kamu personeli bilgiyi girip "Süreci Devam Ettir" butonuna bastığında, Agent 4 girilen verileri `eksik_alanlar_gecmisi` içerisine yazar, evrakın `temizlenmis_metin` alanının sonuna bu bilgileri ekler ve grafiği Agent 2 (Nur) düğümüne geri yönlendirir.
4. **Yeniden değerlendirme:** Agent 2 yeni verilerle eksiklik kontrolünü tekrar yapar. Alanlar tamamlandığı için durum `TAMAMLANDI`'ya döner, Agent 3 eksiksiz temiz taslak üretir ve Agent 4 süreci normal akışında sonlandırır.

---

## 7. Yasin'in ekibe notları (netleştirilmesi gerekenler)

1. **Yönlendirme birimleri:** Prompt içinde yer alan hedef birimler (İnsan Kaynakları, Bilgi İşlem vb.) örnek olarak verilmiştir. Kurgu evrak veri setimizi hazırlayan Yusuf ile bu birimlerin sayısını ve isimlerini sabitlememiz gerekiyor.
2. **UI tasarımı:** LangGraph kesintiye (interrupt) uğradığında bu süreci demo arayüzünde (Gradio/Streamlit vb.) nasıl göstereceğimizi kararlaştırmalıyız.
3. **Mevzuat sınırı:** Can'ın taslak oluşturma aşamasında çok fazla mevzuat geldiğinde modelin kafası karışabilir. Orkestrasyon aşamasında ben prompt'a gönderirken `ilgili_mevzuat` sayısını ilk 3 mevzuat ile sınırlandıracağım, eğer başka bir kural uygulayacaksak teyit edelim.
