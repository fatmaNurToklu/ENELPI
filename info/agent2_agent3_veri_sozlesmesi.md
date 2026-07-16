# Agent 2 → Agent 3 Veri Sözleşmesi
**Şema versiyonu:** 1.0 · **Kapsam:** Nur (Agent 2 — İçerik Analizi & Mevzuat Eşleştirme) → Can (Agent 3 — Resmi Yazı Taslağı Üretimi)  
**Şartname referansı:** Madde 6.4.1 (Görev 1) ve Madde 6.4.2 (Görev 2: Resmi Yazışma Taslağı)

> Agent 1'in çıktı şeması için bkz. `agent1_agent2_veri_sozlesmesi.md`. Bu sözleşme yalnızca Agent 2'nin ürettiği çıktıyı ve Agent 3'ün bu çıktıyı nasıl tüketmesi gerektiğini tanımlar.

---

## 1. Sorumluluk sınırı

| Yetenek | Sorumlu agent |
|---|---|
| Evrak metnini okuma ve sınıflandırma | Agent 1 |
| Bilgi çıkarımı, mevzuat eşleştirme, eksik alan tespiti, özetleme | **Agent 2** |
| Resmi yazı taslağı üretimi | **Agent 3** |
| Yönlendirme kararı ve orkestrasyon | Agent 4 |

**Altın kural:** Agent 3, Agent 2'nin `cikartilan_bilgiler` ve `ozet` alanlarını ham girdi olarak kullanır; kendi başına OCR, sınıflandırma veya mevzuat araması yapmaz. `eksik_alanlar` listesi doluysa taslakta eksik bilgi uyarısı yer almalıdır.

---

## 2. JSON Şema (v1.0)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Agent2_Cikti_Semasi_v1",
  "type": "object",
  "required": ["sema_versiyonu", "agent2_islem_metadata", "evrak_turu", "cikartilan_bilgiler", "ilgili_mevzuat", "eksik_alanlar", "ozet"],
  "properties": {
    "sema_versiyonu": { "type": "string", "const": "1.0" },

    "agent2_islem_metadata": {
      "type": "object",
      "required": ["evrak_id", "islem_zamani", "durum", "manuel_inceleme_onerisi", "agent1_durum", "agent1_siniflandirma_skoru"],
      "properties": {
        "evrak_id": { "type": "string", "pattern": "^EVR-[0-9]{4}-[0-9]{4,}$" },
        "islem_zamani": { "type": "string", "format": "date-time" },
        "durum": {
          "type": "string",
          "enum": ["TAMAMLANDI", "EKSIK_BILGI", "MANUEL_INCELEME"],
          "description": "TAMAMLANDI: tüm zorunlu alanlar dolu, taslağa geç. EKSIK_BILGI: bazı zorunlu alanlar eksik, taslakta belirt. MANUEL_INCELEME: Agent 1'den gelen düşük güven sinyali, insan onayı gerekebilir."
        },
        "manuel_inceleme_onerisi": { "type": "boolean" },
        "agent1_durum": {
          "type": "string",
          "enum": ["BASARILI", "KISMI_BASARILI"],
          "description": "BASARISIZ durumda Agent 2 bu sözleşmeyi üretmez; evrak doğrudan Agent 4'ün manuel kuyruğuna düşer."
        },
        "agent1_siniflandirma_skoru": { "type": "number", "minimum": 0, "maximum": 1 }
      }
    },

    "evrak_turu": {
      "type": "string",
      "description": "Agent 1'in belirlediği tür. Agent 3 taslak formatını buna göre seçer.",
      "enum": ["DILEKCE", "BILGI_EDINME_BASVURUSU", "SIKAYET_BASVURUSU", "RESMI_UST_YAZI", "CEVAP_YAZISI", "BILGILENDIRME_YAZISI", "TALIMAT_YAZISI", "FATURA", "SOZLESME_PROTOKOL", "TUTANAK_RAPOR", "DIGER"]
    },

    "cikartilan_bilgiler": {
      "type": "object",
      "description": "Agent 2'nin LLM ile derinleştirdiği bilgi alanları. Bulunamayan alanlar null.",
      "properties": {
        "gonderici": { "type": ["string", "null"] },
        "gonderici_kurum": { "type": ["string", "null"] },
        "alici_kurum": { "type": ["string", "null"] },
        "konu": { "type": ["string", "null"] },
        "tarih": { "type": ["string", "null"] },
        "belge_sayisi": { "type": ["string", "integer", "null"] },
        "tc_kimlik": { "type": ["string", "null"] },
        "imza_sahibi": { "type": ["string", "null"] },
        "ekler": { "type": ["array", "null"], "items": { "type": "string" } }
      }
    },

    "ilgili_mevzuat": {
      "type": "array",
      "description": "ChromaDB RAG ile eşleştirilen mevzuat maddeleri. Boş liste DIGER türü için normaldir.",
      "items": {
        "type": "object",
        "required": ["kanun", "madde", "metin"],
        "properties": {
          "kanun": { "type": "string" },
          "madde": { "type": "string" },
          "metin": { "type": "string" }
        }
      }
    },

    "eksik_alanlar": {
      "type": "array",
      "description": "Evrak türünün zorunlu alanlarından null olanlar. Boş liste tüm zorunlu alanların dolu olduğu anlamına gelir.",
      "items": { "type": "string" }
    },

    "ozet": {
      "type": "string",
      "description": "Agent 2'nin LLM ile ürettiği 2-3 cümlelik özet. Agent 3 taslak hazırlarken bağlam olarak kullanır."
    }
  }
}
```

---

## 3. `durum` alanına göre Agent 3'ün davranışı

| `durum` | Agent 3'ün yapması gereken |
|---|---|
| `TAMAMLANDI` | Doğrudan taslak üret |
| `EKSIK_BILGI` | Taslağı üret, eksik alanları `[BİLGİ EKSİK: <alan_adı>]` yer tutucusuyla işaretle |
| `MANUEL_INCELEME` | Taslağı üret ama başına `[UYARI: Bu evrak düşük güven skoruyla işlenmiştir, insan denetimi önerilir]` notu ekle |

---

## 4. Örnek çıktılar

### 4.1 Normal senaryo — `EKSIK_BILGI`
```json
{
  "sema_versiyonu": "1.0",
  "agent2_islem_metadata": {
    "evrak_id": "EVR-2026-0001",
    "islem_zamani": "2026-07-01T21:02:51.570209",
    "durum": "EKSIK_BILGI",
    "manuel_inceleme_onerisi": false,
    "agent1_durum": "BASARILI",
    "agent1_siniflandirma_skoru": 0.91
  },
  "evrak_turu": "BILGI_EDINME_BASVURUSU",
  "cikartilan_bilgiler": {
    "gonderici": "Ahmet Yılmaz",
    "gonderici_kurum": null,
    "alici_kurum": "T.C. Bilişim Vadisi Yönetim Kurulu Başkanlığına",
    "konu": "Bilgi Edinme Talebi",
    "tarih": null,
    "belge_sayisi": null,
    "tc_kimlik": null,
    "imza_sahibi": "Ahmet Yılmaz",
    "ekler": null
  },
  "ilgili_mevzuat": [
    {
      "kanun": "4982 Sayılı Bilgi Edinme Hakkı Kanunu",
      "madde": "Madde 5",
      "metin": "Kurum ve kuruluşlar, başvurucu tarafından istenen bilgi veya belgeyi 15 iş günü içinde vermek zorundadır."
    }
  ],
  "eksik_alanlar": ["tc_kimlik"],
  "ozet": "Ahmet Yılmaz tarafından T.C. Bilişim Vadisi Yönetim Kurulu Başkanlığı'na gönderilen bir bilgi edinme talebi bulunmaktadır."
}
```
*`tc_kimlik` eksik — Agent 3 taslakta `[BİLGİ EKSİK: tc_kimlik]` yer tutucusu kullanmalıdır.*

### 4.2 Manuel inceleme senaryosu — `MANUEL_INCELEME`
```json
{
  "sema_versiyonu": "1.0",
  "agent2_islem_metadata": {
    "evrak_id": "EVR-2026-0014",
    "islem_zamani": "2026-07-01T21:03:05.225940",
    "durum": "MANUEL_INCELEME",
    "manuel_inceleme_onerisi": true,
    "agent1_durum": "KISMI_BASARILI",
    "agent1_siniflandirma_skoru": 0.63
  },
  "evrak_turu": "SIKAYET_BASVURUSU",
  "cikartilan_bilgiler": {
    "gonderici": null,
    "gonderici_kurum": null,
    "alici_kurum": null,
    "konu": null,
    "tarih": "belirlsiz",
    "belge_sayisi": null,
    "tc_kimlik": null,
    "imza_sahibi": null,
    "ekler": null
  },
  "ilgili_mevzuat": [
    {
      "kanun": "657 Sayılı Devlet Memurları Kanunu",
      "madde": "Madde 125",
      "metin": "Devlet memurlarına uygulanacak disiplin cezaları..."
    }
  ],
  "eksik_alanlar": ["gonderici", "tc_kimlik", "konu"],
  "ozet": "Gönderen ve konunun belirtilmemiş bir dilekçede şikayet etmek istediği belirtiliyor."
}
```

### 4.3 DIGER türü — `TAMAMLANDI`
```json
{
  "sema_versiyonu": "1.0",
  "agent2_islem_metadata": {
    "evrak_id": "EVR-2026-0027",
    "islem_zamani": "2026-07-01T21:03:16.552881",
    "durum": "TAMAMLANDI",
    "manuel_inceleme_onerisi": false,
    "agent1_durum": "BASARILI",
    "agent1_siniflandirma_skoru": 0.34
  },
  "evrak_turu": "DIGER",
  "cikartilan_bilgiler": {
    "gonderici": null,
    "gonderici_kurum": null,
    "alici_kurum": null,
    "konu": "Davet metni",
    "tarih": null,
    "belge_sayisi": 2,
    "tc_kimlik": null,
    "imza_sahibi": null,
    "ekler": null
  },
  "ilgili_mevzuat": [],
  "eksik_alanlar": [],
  "ozet": "Toplantı davetiyesi resmi bir şekilde hazırlanmış ve ilgili mevzuat bilgisi eksik değildir."
}
```
*`DIGER` türünde `ilgili_mevzuat` boş listedir — normaldir, Agent 3 mevzuat atıfı yapmadan genel taslak üretir.*

---

## 5. Hata ve kenar durum kuralları

- **`durum: MANUEL_INCELEME` + `eksik_alanlar` dolu:** Her iki uyarı da taslağa yansıtılmalı.
- **`ilgili_mevzuat: []`:** Yalnızca `DIGER` türünde beklenir. Diğer türlerde boş gelirse Agent 3 bunu işaret etmeli.
- **`agent1_siniflandirma_skoru < 0.70`:** Agent 3 taslak üretirken evrak türünün yanlış sınıflandırılmış olabileceğini göz önünde bulundurmalı; gerekirse taslağın üstüne not eklemeli.
- **`BASARISIZ` Agent 1 çıktısı:** Bu sözleşme kapsamına girmez; Agent 2 bu durumda hiç çıktı üretmez, evrak Agent 4 üzerinden manuel kuyruğa düşer.

---

## 6. Versiyonlama

Şema değişikliklerinde `sema_versiyonu` güncellenir. Küçük değişiklikler (1.0 → 1.1) PR ile, kırıcı değişiklikler (1.x → 2.0) takım içi onayla yapılır. Değişiklikler bu dosyada changelog olarak tutulur.
