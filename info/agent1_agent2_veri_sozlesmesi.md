# Agent 1 → Agent 2 Veri Sözleşmesi
**Şema versiyonu:** 1.0 · **Kapsam:** Yusuf (Agent 1 — Evrak Okuma & Sınıflandırma) → Nur (Agent 2 — İçerik Analizi & Mevzuat Eşleştirme)
**Şartname referansı:** Madde 6.4.1 (Görev 1: Evrak Sınıflandırma ve İçerik Analizi)

---

## 1. Sorumluluk sınırı

Şartname Görev 1'i tek bir bütün olarak tanımlıyor ama takım bunu iki agent'a bölmüş. Çakışmayı önlemek için kural şu:

| Yetenek (Şartname 6.4.1) | Sorumlu agent | Bu sözleşmedeki karşılığı |
|---|---|---|
| Evrakı OCR/metin olarak okuma | **Agent 1** | `metin_icerigi`, `agent1_islem_metadata` |
| Evrak türünü belirleme | **Agent 1** | `siniflandirma_sonucu` |
| Önemli bilgi unsurlarını çıkarma | **Agent 2** | Agent 2'nin kendi çıktısı (bu sözleşme kapsamı dışı) |
| Eksik bilgi tespiti | **Agent 2** | §4'teki taksonomi tablosunu girdi olarak kullanır |
| Mevzuat/yazışma kuralı önerisi | **Agent 2** | — |
| Özet oluşturma | **Agent 2** | — |

**Altın kural:** Agent 1 sadece *yapısal/yüzeysel* veriyi garanti eder (regex, sabit konum, OCR çıktısı). Anlam çıkarımı, eksiklik analizi ve mevzuat eşlemesi tamamen Agent 2'nindir. `on_cikarimlar` içindeki alanlar bu yüzden "kesin tespit" değil, "ön bulgu" niteliğindedir — Agent 2 bunları doğrulayıp derinleştirebilir.

---

## 2. JSON Şema (v1.0)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Agent1_Cikti_Semasi_v1",
  "type": "object",
  "required": ["sema_versiyonu", "agent1_islem_metadata", "siniflandirma_sonucu", "metin_icerigi", "on_cikarimlar"],
  "properties": {
    "sema_versiyonu": { "type": "string", "const": "1.0" },

    "agent1_islem_metadata": {
      "type": "object",
      "required": ["evrak_id", "islem_zamani", "kaynak_tipi", "durum"],
      "properties": {
        "evrak_id": { "type": "string", "pattern": "^EVR-[0-9]{4}-[0-9]{4,}$" },
        "islem_zamani": { "type": "string", "format": "date-time" },
        "kaynak_tipi": {
          "type": "string",
          "enum": ["DIJITAL_METIN", "TARANMIS_GORUNTU", "PDF_METIN_KATMANI"],
          "description": "DIJITAL_METIN: zaten metin; TARANMIS_GORUNTU: OCR gerekti; PDF_METIN_KATMANI: PDF'in gömülü metin katmanı kullanıldı, OCR'a gerek kalmadı"
        },
        "sayfa_sayisi": { "type": "integer", "minimum": 1, "default": 1 },
        "ocr_motoru": { "type": ["string", "null"], "description": "kaynak_tipi=TARANMIS_GORUNTU değilse null" },
        "ocr_guven_skoru": { "type": ["number", "null"], "minimum": 0, "maximum": 1 },
        "durum": {
          "type": "string",
          "enum": ["BASARILI", "KISMI_BASARILI", "BASARISIZ"],
          "description": "BASARISIZ ise temizlenmis_metin boş olabilir; Agent 2 bu durumda NLP denemesi YAPMAMALI, evrakı manuel kuyruğa yönlendirmeli"
        },
        "manuel_inceleme_onerisi": { "type": "boolean", "description": "ocr_guven_skoru veya siniflandirma_guven_skoru eşik altındaysa true" }
      }
    },

    "siniflandirma_sonucu": {
      "type": "object",
      "required": ["evrak_turu", "siniflandirma_guven_skoru"],
      "properties": {
        "evrak_turu": { "type": "string", "description": "§4'teki taksonomiden bir değer, veya DIGER" },
        "alt_kategori": { "type": ["string", "null"] },
        "siniflandirma_guven_skoru": { "type": "number", "minimum": 0, "maximum": 1 },
        "alternatif_tahminler": {
          "type": "array",
          "description": "İsteğe bağlı: ikinci/üçüncü en olası tür, belirsiz durumlarda Agent 2'ye sinyal verir",
          "items": {
            "type": "object",
            "properties": { "tur": { "type": "string" }, "skor": { "type": "number" } }
          }
        }
      }
    },

    "metin_icerigi": {
      "type": "object",
      "required": ["temizlenmis_metin", "dil"],
      "properties": {
        "ham_metin": { "type": ["string", "null"], "description": "OCR/çıkarım öncesi ham çıktı; hata ayıklama için saklanır, Agent 2 bunu kullanmaz" },
        "temizlenmis_metin": { "type": "string", "description": "Çok sayfalıysa sayfalar '\\n\\n[SAYFA N]\\n\\n' ile ayrılır" },
        "dil": { "type": "string", "const": "tr" }
      }
    },

    "on_cikarimlar": {
      "type": "object",
      "description": "Agent 1'in yapısal/regex tabanlı ön bulguları. Bulunamayan alan null bırakılır — bu, Agent 2'nin eksik-bilgi analizine girdidir.",
      "properties": {
        "gonderici": { "type": ["string", "null"] },
        "alici_kurum": { "type": ["string", "null"], "description": "Evrakta yazılı muhatap; Agent 4'ün hesapladığı 'doğru yönlendirme birimi' ile AYNI ŞEY DEĞİLDİR" },
        "konu": { "type": ["string", "null"] },
        "tarih": { "type": ["string", "null"], "format": "date" },
        "belge_sayisi": { "type": ["string", "null"] },
        "tc_kimlik": { "type": ["string", "null"] },
        "imza_sahibi": { "type": ["string", "null"] },
        "ekler": { "type": ["array", "null"], "items": { "type": "string" } }
      }
    }
  }
}
```

---

## 3. Evrak türü taksonomisi ve zorunlu alan eşlemesi

Bu tablo Nur'un **eksik bilgi tespiti** için ana referans kaynağıdır: `evrak_turu` değerine göre hangi `on_cikarimlar` alanlarının dolu olması gerektiğini söyler. Yeni bir tür eklenirse bu tablo güncellenip her iki tarafa duyurulmalı (bkz. §7).

| `evrak_turu` | Zorunlu alanlar |
|---|---|
| `DILEKCE` | gonderici, tc_kimlik, konu, tarih |
| `BILGI_EDINME_BASVURUSU` | gonderici, tc_kimlik, alici_kurum, konu |
| `SIKAYET_BASVURUSU` | gonderici, tc_kimlik, konu |
| `RESMI_UST_YAZI` | gonderici, alici_kurum, belge_sayisi, konu, tarih, imza_sahibi |
| `CEVAP_YAZISI` | gonderici, alici_kurum, belge_sayisi, konu, tarih |
| `BILGILENDIRME_YAZISI` | gonderici, alici_kurum, konu, tarih |
| `TALIMAT_YAZISI` | gonderici, alici_kurum, konu, tarih, imza_sahibi |
| `FATURA` | gonderici, tarih, belge_sayisi |
| `SOZLESME_PROTOKOL` | gonderici, alici_kurum, tarih, konu |
| `TUTANAK_RAPOR` | tarih, konu |
| `DIGER` | sabit liste yok — Agent 2 genel-amaçlı kontrol uygular |

> Bu liste şartnamenin verdiği örneklerden (*Dilekçe, Üst Yazı, Fatura*) ve gerçek kamu yazışma türlerinden türetildi; sentetik veri setini üretirken bu 11 türün dağılımlı şekilde temsil edilmesi öneririm.

---

## 4. Örnek çıktılar

### 4.1 Normal senaryo (yüksek güven)
```json
{
  "sema_versiyonu": "1.0",
  "agent1_islem_metadata": {
    "evrak_id": "EVR-2026-0001",
    "islem_zamani": "2026-06-28T10:15:00+03:00",
    "kaynak_tipi": "TARANMIS_GORUNTU",
    "sayfa_sayisi": 1,
    "ocr_motoru": "Tesseract 5.3",
    "ocr_guven_skoru": 0.94,
    "durum": "BASARILI",
    "manuel_inceleme_onerisi": false
  },
  "siniflandirma_sonucu": {
    "evrak_turu": "BILGI_EDINME_BASVURUSU",
    "alt_kategori": "VATANDAS_TALEBI",
    "siniflandirma_guven_skoru": 0.91
  },
  "metin_icerigi": {
    "temizlenmis_metin": "T.C. Bilişim Vadisi Yönetim Kurulu Başkanlığına Konu: Bilgi Edinme Talebi Kurumunuz bünyesinde 2026 yılı içerisinde TEKNOFEST hazırlıkları kapsamında açık kaynak platformlarına yapılan destekler hakkında tarafıma bilgi verilmesini arz ederim. Ad Soyad: Ahmet Yılmaz İmza",
    "dil": "tr"
  },
  "on_cikarimlar": {
    "gonderici": "Ahmet Yılmaz",
    "alici_kurum": "T.C. Bilişim Vadisi Yönetim Kurulu Başkanlığı",
    "konu": "Bilgi Edinme Talebi",
    "tarih": null,
    "belge_sayisi": null,
    "tc_kimlik": null,
    "imza_sahibi": null,
    "ekler": null
  }
}
```
*(`tarih` ve `tc_kimlik` kasıtlı null — Agent 2'nin eksik bilgi tespitini test eder. Taksonomi tablosuna göre `BILGI_EDINME_BASVURUSU` için `tc_kimlik` zorunlu, dolayısıyla Agent 2 bu evrakı "eksik bilgili" işaretlemelidir.)*

### 4.2 Düşük güven / manuel inceleme senaryosu
```json
{
  "sema_versiyonu": "1.0",
  "agent1_islem_metadata": {
    "evrak_id": "EVR-2026-0014",
    "islem_zamani": "2026-06-28T11:02:00+03:00",
    "kaynak_tipi": "TARANMIS_GORUNTU",
    "sayfa_sayisi": 1,
    "ocr_motoru": "Tesseract 5.3",
    "ocr_guven_skoru": 0.58,
    "durum": "KISMI_BASARILI",
    "manuel_inceleme_onerisi": true
  },
  "siniflandirma_sonucu": {
    "evrak_turu": "SIKAYET_BASVURUSU",
    "alt_kategori": null,
    "siniflandirma_guven_skoru": 0.63,
    "alternatif_tahminler": [{ "tur": "DILEKCE", "skor": 0.31 }]
  },
  "metin_icerigi": {
    "temizlenmis_metin": "...okunamayan satır... şikayet etmek isti[?]orum ... tarih belirsiz",
    "dil": "tr"
  },
  "on_cikarimlar": {
    "gonderici": null,
    "alici_kurum": null,
    "konu": null,
    "tarih": null,
    "belge_sayisi": null,
    "tc_kimlik": null,
    "imza_sahibi": null,
    "ekler": null
  }
}
```
*(Düşük güven skorları, Agent 4'ün orkestrasyon katmanında "insan onayı" dalına yönlendirme için sinyal görevi görür.)*

### 4.3 Sınıf dışı (`DIGER`) senaryo
```json
{
  "sema_versiyonu": "1.0",
  "agent1_islem_metadata": {
    "evrak_id": "EVR-2026-0027",
    "islem_zamani": "2026-06-28T13:40:00+03:00",
    "kaynak_tipi": "PDF_METIN_KATMANI",
    "sayfa_sayisi": 2,
    "ocr_motoru": null,
    "ocr_guven_skoru": null,
    "durum": "BASARILI",
    "manuel_inceleme_onerisi": false
  },
  "siniflandirma_sonucu": {
    "evrak_turu": "DIGER",
    "alt_kategori": null,
    "siniflandirma_guven_skoru": 0.34,
    "alternatif_tahminler": [{ "tur": "TUTANAK_RAPOR", "skor": 0.30 }, { "tur": "SOZLESME_PROTOKOL", "skor": 0.22 }]
  },
  "metin_icerigi": {
    "temizlenmis_metin": "[SAYFA 1] Davet metni... [SAYFA 2] Katılımcı listesi...",
    "dil": "tr"
  },
  "on_cikarimlar": {
    "gonderici": "Etkinlik Koordinatörlüğü",
    "alici_kurum": null,
    "konu": "Toplantı Daveti",
    "tarih": "2026-07-15",
    "belge_sayisi": null,
    "tc_kimlik": null,
    "imza_sahibi": null,
    "ekler": null
  }
}
```
*(Taksonomiye uymayan ama gerçekçi bir vaka — sistemin robustluğunu göstermek için veri setinde bilerek bulundurulmalı; Görev 2 puanlamasında "uygulama" kalitesi bu gibi kenar durumlarda da test edilecek.)*

---

## 5. Hata ve kenar durum kuralları

- **`durum: BASARISIZ`** → `temizlenmis_metin` boş/anlamsız olabilir. Agent 2 bu durumda NLP çalıştırmaz, evrak doğrudan Agent 4'ün manuel kuyruğuna düşer.
- **Çok sayfalı evrak** → `temizlenmis_metin` içinde sayfalar `[SAYFA N]` etiketiyle ayrılır; imza/tarih gibi alanlar genelde son sayfada olur, Agent 2 bunu varsayım olarak kullanabilir.
- **Güven eşiği** → öneri: `ocr_guven_skoru < 0.70` veya `siniflandirma_guven_skoru < 0.70` ise `manuel_inceleme_onerisi = true`. Eşik değeri Yasin'in orkestrasyon katmanında konfigüre edilebilir olmalı ama referans değeri burada (0.70) sabitlenmiştir.
- **`alici_kurum` ≠ yönlendirme birimi** → `on_cikarimlar.alici_kurum` evrakta yazılı olan muhataptır (örn. "Kurum Başkanlığı"). Agent 4'ün hesapladığı "hangi iç birim bakacak" kararı (örn. "İnsan Kaynakları Daire Başkanlığı") farklı bir alandır ve bu sözleşmenin kapsamında değildir — karıştırılmamalı.

---

## 6. Versiyonlama

`sema_versiyonu` alanı ileride şema değişirse (yeni alan, enum genişlemesi) geriye dönük uyumluluğu yönetmek için var. Önerilen pratik: şema değişikliklerini repodaki `CONTRACT.md` dosyasında changelog olarak tutup, küçük değişiklikleri (1.0 → 1.1) PR ile, kırıcı değişiklikleri (1.x → 2.0) takım içi onayla yapmak.

---

## 7. Nur'a iletmeden önce netleştirilmesi gereken noktalar

1. §4'teki taksonomi ve zorunlu alan tablosu üzerinde mutabakat — Nur'un mevzuat eşleme mantığı da büyük ölçüde `evrak_turu`'ne göre çalışacağı için bu liste ikinizin de "ortak sözlüğü" olacak.
2. `on_cikarimlar`'daki hangi alanların senin (yapısal), hangilerinin Nur'un (semantik) işi olduğu — özellikle `konu` ve `gonderici` gibi bazen kolay regex'le, bazen bağlamla çıkarılabilen alanlarda çakışma riski var.
3. Güven skoru eşiği (0.70 önerisi) üzerinde anlaşma — bu değer aynı zamanda Yasin'in orkestrasyon mantığını da etkiler.
4. `DIGER` durumunda Nur'un davranışı: genel-amaçlı NLP mi denenecek, yoksa direkt insana mı yönlendirilecek?
5. Şema güncellemelerinin nasıl duyurulacağı (GitHub PR, ortak kanal vb.) — açık kaynak repo zorunluluğu olduğu için bu doğal olarak `CONTRACT.md` üzerinden versiyonlanabilir.
