# Agent 3 → Agent 4 Veri Sözleşmesi
**Şema versiyonu:** 1.0 · **Kapsam:** Can (Agent 3 — Resmî Yazı Taslağı Üretimi) → Yasin (Agent 4 — Yönlendirme Kararı & Orkestrasyon)
**Şartname referansı:** Madde 6.4.2 (Görev 2: Resmî Yazı Taslaklama ve Birim Yönlendirme)

> Agent 1'in çıktı şeması için bkz. `agent1_agent2_veri_sozlesmesi.md`. Agent 2'nin çıktı şeması için bkz. `agent2_agent3_veri_sozlesmesi.md`. Bu sözleşme yalnızca Agent 3'ün ürettiği taslağı ve Agent 4'ün bunu nasıl tüketip yönlendirme kararına bağlayacağını tanımlar.

---

## 0. Taslak üretim yaklaşımı (bilgi amaçlı)

Agent 3, taslağı tek seferde serbest LLM üretimiyle değil, **şablon + slot-filling** yaklaşımıyla oluşturur:
- Her `sablon_turu` için sabit bir şablon iskeleti vardır (hitap satırı, kapanış, varsa uyarı bloğu, eksik-bilgi yer tutucuları) — bunlar kod tarafında **deterministik** olarak eklenir.
- Gemma 2 9B yalnızca gövde paragrafını, Agent 2'nin `cikartilan_bilgiler` ve `ozet` alanlarından doldurur; modele bırakılan tek kısım burasıdır.
- Bu nedenle `eksik_alan_yer_tutucular` ve varsa `[UYARI: ...]` bloğu **taslakta her zaman garanti olarak bulunur** — bunlar modelin ürettiği bir şey değil, kodun eklediği sabit bir parçadır. Agent 4 bu tutarlılığa güvenebilir.
- `resmi_uslup_kontrolu` da aynı sebeple kural tabanlıdır (modelin kendi çıktısını denetlemesi değil); bkz. §2.

Bu yaklaşımın Agent 4 için tek pratik sonucu: `taslak_metni` içindeki format öğeleri (hitap/kapanış/yer tutucu/uyarı) sabit ve öngörülebilir, gövde paragrafı ise modelin ürettiği ve bu yüzden `resmi_uslup_kontrolu` ile ayrıca doğrulanan kısımdır.

---

## 1. Sorumluluk sınırı

Şartname Görev 2'yi ("hangi resmi yazının hazırlanması gerektiğine karar veren ve buna uygun bir yazı taslağı oluşturan... birim yönlendirme işlevlerini yerine getiren agent sistemi") tek bir bütün olarak tanımlıyor, ama takım bunu iki agent'a bölmüş. Çakışmayı önlemek için kural şu:

| Yetenek (Şartname 6.4.2) | Sorumlu agent | Bu sözleşmedeki karşılığı |
|---|---|---|
| Üst yazı / cevap yazısı / bilgilendirme metni taslağı oluşturma | **Agent 3** | `uretilen_taslak.taslak_metni` |
| Taslağın resmi üsluba uygun olması | **Agent 3** | `uretilen_taslak.resmi_uslup_kontrolu` |
| Evrakın içeriğine göre doğru birime yönlendirme önerisi | **Agent 4** | Agent 4'ün kendi çıktısı (bu sözleşme kapsamı dışı) |
| Kullanıcıya süreç hakkında bilgilendirme | **Agent 4** | — |
| Gerekli durumlarda eksik bilgi talep etme | Agent 2 tespit eder, Agent 3 taslakta işaretler, Agent 4 kullanıcıya iletir | `eksik_alan_yer_tutucular` |

**Altın kural:** Agent 3, Agent 2'nin `cikartilan_bilgiler`, `ilgili_mevzuat`, `eksik_alanlar` ve `ozet` alanlarını ham girdi olarak kullanır; **hangi birime yönlendirileceğine karar vermez** — bu tamamen Agent 4'ündür. Agent 3'ün tek işi, önündeki bilgiyle en iyi taslağı üretmek ve taslağın güvenilirlik durumunu (`durum`) Agent 4'e doğru şekilde işaretlemektir. Agent 3 kendi başına mevzuat araması, yeniden sınıflandırma veya eksik bilgi tamamlama **yapmaz**.

---

## 2. JSON Şema (v1.0)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Agent3_Cikti_Semasi_v1",
  "type": "object",
  "required": ["sema_versiyonu", "evrak_id", "kaynak_baglam", "uretilen_taslak", "durum"],
  "properties": {
    "sema_versiyonu": { "type": "string", "const": "1.0" },
    "evrak_id": { "type": "string", "pattern": "^EVR-[0-9]{4}-[0-9]{4,}$" },

    "kaynak_baglam": {
      "type": "object",
      "description": "Agent 2'den gelen bağlamın Agent 4'e taşınması için gerekli asgari alt küme (tam kopya değil, referans amaçlı özet)",
      "required": ["evrak_turu", "agent2_durum", "eksik_alanlar", "mevzuat_sayisi"],
      "properties": {
        "evrak_turu": {
          "type": "string",
          "enum": ["DILEKCE", "BILGI_EDINME_BASVURUSU", "SIKAYET_BASVURUSU", "RESMI_UST_YAZI", "CEVAP_YAZISI", "BILGILENDIRME_YAZISI", "TALIMAT_YAZISI", "FATURA", "SOZLESME_PROTOKOL", "TUTANAK_RAPOR", "DIGER"]
        },
        "agent2_durum": { "type": "string", "enum": ["TAMAMLANDI", "EKSIK_BILGI", "MANUEL_INCELEME"] },
        "eksik_alanlar": { "type": "array", "items": { "type": "string" } },
        "mevzuat_sayisi": { "type": "integer", "minimum": 0, "description": "ilgili_mevzuat dizisinin uzunluğu; 0 ise DIGER türünde normal, diğer türlerde Agent 4'e sinyal" }
      }
    },

    "uretilen_taslak": {
      "type": "object",
      "required": ["sablon_turu", "taslak_metni", "eksik_alan_yer_tutucular", "resmi_uslup_kontrolu"],
      "properties": {
        "sablon_turu": {
          "type": "string",
          "description": "evrak_turu'ne göre seçilen taslak şablonu; DIGER için GENEL_AMACLI kullanılır",
          "enum": ["DILEKCE_CEVABI", "BILGI_EDINME_CEVABI", "SIKAYET_CEVABI", "UST_YAZI", "CEVAP_YAZISI", "BILGILENDIRME_YAZISI", "TALIMAT_YAZISI", "GENEL_AMACLI"]
        },
        "taslak_metni": { "type": "string", "description": "Resmi yazışma formatında üretilen tam taslak metni. Hitap/kapanış/yer tutucu/uyarı blokları deterministik şablondan gelir; yalnızca gövde paragrafı model tarafından üretilir (bkz. §0)" },
        "eksik_alan_yer_tutucular": {
          "type": "array",
          "description": "kaynak_baglam.eksik_alanlar ile birebir eşleşmeli; taslak_metni içinde '[BİLGİ EKSİK: <alan_adı>]' olarak geçen alanların listesi. Şablon tarafından deterministik eklendiği için normalde eksik_alanlar ile tam örtüşür",
          "items": { "type": "string" }
        },
        "resmi_uslup_kontrolu": {
          "type": "object",
          "description": "Yalnızca modelin ürettiği gövde paragrafı için çalıştırılan, kural tabanlı (regex/kelime listesi) kontrol sonucu",
          "required": ["uygun_mu", "tespit_edilen_sorunlar"],
          "properties": {
            "uygun_mu": { "type": "boolean" },
            "tespit_edilen_sorunlar": { "type": "array", "items": { "type": "string" }, "description": "Örn: 'argo ifade tespit edildi', 'ikinci tekil şahıs kullanımı', 'imza bloğu eksik'" }
          }
        }
      }
    },

    "durum": {
      "type": "string",
      "enum": ["TASLAK_HAZIR", "TASLAK_HAZIR_EKSIK_BILGI", "TASLAK_HAZIR_MANUEL_INCELEME_UYARILI", "URETILEMEDI"],
      "description": "Agent 4'ün davranışını belirleyen ana sinyal; bkz. §3"
    }
  }
}
```

---

## 3. `durum` alanına göre Agent 4'ün davranışı

| `durum` | Tetiklendiği koşul | Agent 4'ün yapması gereken |
|---|---|---|
| `TASLAK_HAZIR` | `agent2_durum: TAMAMLANDI` ve taslak başarıyla üretildi | Taslağı kullanıcıya sun, yönlendirme kararını `kaynak_baglam` + Agent 2'nin `alici_kurum` bilgisiyle hesapla |
| `TASLAK_HAZIR_EKSIK_BILGI` | `agent2_durum: EKSIK_BILGI` | Taslağı sun, `eksik_alan_yer_tutucular` listesindeki alanları arayüzde vurgula; gerekirse kullanıcıdan tamamlama iste, otomatik gönderime kapat |
| `TASLAK_HAZIR_MANUEL_INCELEME_UYARILI` | `agent2_durum: MANUEL_INCELEME` | Taslağı **insan onay kuyruğuna** düşür; otomatik/doğrudan gönderim kesinlikle yapılmaz |
| `URETILEMEDI` | Gövde paragrafı üretimi başarısız oldu (boş/anlamsız model çıktısı) | Evrakı manuel kuyruğa yönlendir; Agent 4 isteğe bağlı olarak Agent 3'ü yeniden deneyebilir |

> `resmi_uslup_kontrolu.uygun_mu: false` geldiğinde, `durum` ne olursa olsun Agent 4 taslağı **otomatik gönderilebilir** olarak işaretlememelidir — bu alan `durum`'dan bağımsız ayrı bir kapı görevi görür.

---

## 4. Örnek çıktılar

### 4.1 Normal senaryo — `TASLAK_HAZIR_EKSIK_BILGI`
```json
{
  "sema_versiyonu": "1.0",
  "evrak_id": "EVR-2026-0001",
  "kaynak_baglam": {
    "evrak_turu": "BILGI_EDINME_BASVURUSU",
    "agent2_durum": "EKSIK_BILGI",
    "eksik_alanlar": ["tc_kimlik"],
    "mevzuat_sayisi": 1
  },
  "uretilen_taslak": {
    "sablon_turu": "BILGI_EDINME_CEVABI",
    "taslak_metni": "Sayın Ahmet Yılmaz,\n\nT.C. Bilişim Vadisi Yönetim Kurulu Başkanlığına yapmış olduğunuz bilgi edinme talebiniz tarafımızca değerlendirilmeye alınmıştır. 4982 Sayılı Bilgi Edinme Hakkı Kanunu Madde 5 uyarınca başvurunuz 15 iş günü içerisinde sonuçlandırılacaktır.\n\nBaşvurunuzun işleme alınabilmesi için aşağıdaki bilginin tarafımıza iletilmesi gerekmektedir:\n[BİLGİ EKSİK: tc_kimlik]\n\nSaygılarımızla,",
    "eksik_alan_yer_tutucular": ["tc_kimlik"],
    "resmi_uslup_kontrolu": {
      "uygun_mu": true,
      "tespit_edilen_sorunlar": []
    }
  },
  "durum": "TASLAK_HAZIR_EKSIK_BILGI"
}
```
*(İkinci paragraf — "Kurumunuza yapmış olduğunuz... değerlendirilmeye alınmıştır" — modelin ürettiği gövde; hitap, mevzuat cümlesinin kalıbı, eksik bilgi bloğu ve kapanış şablondan gelir.)*

### 4.2 Manuel inceleme senaryosu — `TASLAK_HAZIR_MANUEL_INCELEME_UYARILI`
```json
{
  "sema_versiyonu": "1.0",
  "evrak_id": "EVR-2026-0014",
  "kaynak_baglam": {
    "evrak_turu": "SIKAYET_BASVURUSU",
    "agent2_durum": "MANUEL_INCELEME",
    "eksik_alanlar": ["gonderici", "tc_kimlik", "konu"],
    "mevzuat_sayisi": 1
  },
  "uretilen_taslak": {
    "sablon_turu": "SIKAYET_CEVABI",
    "taslak_metni": "[UYARI: Bu evrak düşük güven skoruyla işlenmiştir, insan denetimi önerilir]\n\nSayın İlgili,\n\nTarafımıza iletilen şikayet başvurunuz değerlendirilmeye alınmıştır. Ancak başvurunuzda yer alan bazı bilgiler netlik taşımadığından süreç şu an tamamlanamamaktadır:\n[BİLGİ EKSİK: gonderici]\n[BİLGİ EKSİK: tc_kimlik]\n[BİLGİ EKSİK: konu]\n\nSaygılarımızla,",
    "eksik_alan_yer_tutucular": ["gonderici", "tc_kimlik", "konu"],
    "resmi_uslup_kontrolu": {
      "uygun_mu": true,
      "tespit_edilen_sorunlar": []
    }
  },
  "durum": "TASLAK_HAZIR_MANUEL_INCELEME_UYARILI"
}
```

### 4.3 Taslak üretilemedi — `URETILEMEDI`
```json
{
  "sema_versiyonu": "1.0",
  "evrak_id": "EVR-2026-0031",
  "kaynak_baglam": {
    "evrak_turu": "SOZLESME_PROTOKOL",
    "agent2_durum": "TAMAMLANDI",
    "eksik_alanlar": [],
    "mevzuat_sayisi": 6
  },
  "uretilen_taslak": {
    "sablon_turu": "GENEL_AMACLI",
    "taslak_metni": "",
    "eksik_alan_yer_tutucular": [],
    "resmi_uslup_kontrolu": {
      "uygun_mu": false,
      "tespit_edilen_sorunlar": ["bos_cikti"]
    }
  },
  "durum": "URETILEMEDI"
}
```
*(6 mevzuat maddesinin tamamının tek promptta gövde paragrafına gerekçe olarak verilmeye çalışılması, model üretimini başarısız kılmış olabilir; bkz. §5.)*

---

## 5. Hata ve kenar durum kuralları

- **`agent2_durum: MANUEL_INCELEME` + `eksik_alanlar` dolu:** Her iki uyarı da taslağa yansıtılır — önce `[UYARI: ...]` başlığı, sonra ilgili yer tutucular. Sıralama tutarlı olmalı: uyarı her zaman metnin en başında. Bu bloklar şablondan geldiği için sıralama hatası olmamalı; olursa bir kod hatasıdır, model hatası değildir.
- **`mevzuat_sayisi` yüksek (öneri eşiği: >5):** Prompt'a gövde paragrafı için verilen mevzuat maddesi sayısı 2-3 ile sınırlandırılır (bkz. §0); tamamı verilmez. Yine de çok sayıda madde varsa gövde üretimi zorlaşabilir.
- **`sablon_turu: GENEL_AMACLI` (DIGER türü):** Sabit iskelet daha esnektir, mevzuat atfı yapılmaz. Bu durum hata değildir, `resmi_uslup_kontrolu.uygun_mu` yine de kontrol edilmelidir.
- **`durum: URETILEMEDI`:** Yalnızca modelin ürettiği gövde paragrafı başarısız olduğunda oluşur (şablon iskeleti kendi başına asla başarısız olmaz). Agent 4 bu evrakı **doğrudan manuel kuyruğa** yönlendirir; otomatik yeniden deneme sayısı orkestrasyon katmanında sınırlı tutulmalıdır (öneri: 1-2 kez).
- **`resmi_uslup_kontrolu.uygun_mu: false` ama `durum: TASLAK_HAZIR`:** Çelişkili görünse de mümkündür (gövde üretildi ama kural kontrolünden geçemedi). Agent 4 bu durumu `TASLAK_HAZIR_MANUEL_INCELEME_UYARILI` ile aynı şekilde, insan onayı gerektiren bir durum olarak ele almalıdır.
- **`eksik_alan_yer_tutucular` ile `kaynak_baglam.eksik_alanlar` uyuşmazlığı:** Normalde bu iki liste birebir örtüşür (yer tutucular şablondan deterministik eklenir). Fark varsa bu bir kod hatasıdır — Agent 4 taslağı otomatik onaya kapatmalı ve farkı loglamalıdır.

---

## 6. Versiyonlama

Şema değişikliklerinde `sema_versiyonu` güncellenir. Küçük değişiklikler (1.0 → 1.1) PR ile, kırıcı değişiklikler (1.x → 2.0) takım içi onayla yapılır. Değişiklikler bu dosyada changelog olarak tutulur.

---

## 7. Yasin'e iletmeden önce netleştirilmesi gereken noktalar

1. Yönlendirme kararının (`hangi birim bakacak`) girdisi Agent 2'nin `cikartilan_bilgiler.alici_kurum` alanından mı, yoksa Agent 3'ün taslak içeriğinden çıkarım yapılarak mı üretilecek — bu sözleşme Agent 3'ün yönlendirmeye karışmadığını varsayıyor, Yasin ile teyit edilmeli.
2. `URETILEMEDI` durumunda Agent 4'ün Agent 3'ü otomatik tekrar çağırıp çağırmayacağı, çağıracaksa kaç kez.
3. `resmi_uslup_kontrolu` şu an kural tabanlı/basit bir kontrol olarak tanımlandı — ileride ayrı bir LLM-judge adımına dönüşürse şema versiyonu 1.1'e çıkarılmalı.
4. Çok sayıda mevzuat maddesi geldiğinde (`mevzuat_sayisi` yüksek) Agent 3'ün gövde promptuna hangi kritere göre 2-3 madde seçeceği (en yüksek alaka skoru, ilk N madde vb.) — bu seçim mantığı Agent 2 ile de görüşülmeli, zira mevzuat sıralaması Agent 2'nin çıktı sırasına bağlı.
5. Demo videosu ve final sunumunda, taslak üretiminin gerçek evrak akışı içinde nasıl gösterileceği — şartnamenin Değerlendirme Kriterleri'nde "Uygulama" başlığı (%35) altında "yazı şablon oluşturma kalitesi" doğrudan Agent 3'ün çıktısına dayanıyor, demo bu noktayı net göstermeli.
