# Agent 3 — Resmî Yazı Taslaklama

TEKNOFEST TYDA yarışması kapsamında Agent 2 (içerik analizi + mevzuat eşleştirme)
çıktısını alan ve şu 3 modülü çalıştıran ajan:

1. **Şablon + slot-filling taslak üretimi** — deterministik iskelet + LLM gövde
2. **Resmi üslup kontrolü** — kural tabanlı (regex + kelime listesi)
3. **Agent 4'e yönlendirme sinyali** — 4 durum kodu

Çıktı formatı `agent3_agent4_veri_sozlesmesi.md`'de (v1.0) tanımlıdır.

---

## Mimari (sözleşme §0)

```
Agent 2 JSON
    ↓
┌───────────────────────────────────────────────┐
│  agent3.py                                    │
│                                               │
│  1. sablon_turu_sec(evrak_turu)               │
│     11 evrak türü → 8 şablon                  │
│                                               │
│  2. LLM ile gövde paragrafı üret              │
│     Gemma2:9b, temperature=0.3                │
│     SADECE 2-4 cümlelik paragraf              │
│     Hitap/kapanış YASAK                       │
│                                               │
│  3. Şablon + gövde birleştir (deterministik)  │
│     [UYARI] → hitap+giriş → gövde →           │
│     [BİLGİ EKSİK] → kapanış                   │
│                                               │
│  4. uslup_kontrol_et(govde)                   │
│     - Argo / gündelik ifade                   │
│     - İkinci tekil şahıs                      │
│     - Emoji, aşırı noktalama                  │
│     - İngilizce sızıntı                       │
│                                               │
│  5. Durum belirle                             │
│     TAMAMLANDI      → TASLAK_HAZIR            │
│     EKSIK_BILGI     → TASLAK_HAZIR_EKSIK...   │
│     MANUEL_INCELEME → ...UYARILI              │
│     Gövde boş       → URETILEMEDI             │
└───────────────────────────────────────────────┘
    ↓
Agent 3 JSON  →  Agent 4
```

**Anahtar tasarım kararı:** LLM sadece gövde paragrafını üretir. Hitap, kapanış,
uyarı bloğu, eksik-bilgi yer tutucuları hepsi kod tarafından şablondan gelir.
Bu sayede LLM halüsinasyon riski büyük ölçüde kontrol altında.

---

## Kurulum

Ollama gerekli:
```bash
# Ollama kurulumu: https://ollama.com
ollama pull gemma2:9b
```

Python bağımlılıkları:
```bash
pip install -r requirements.txt
```

---

## Kullanım

### Test (3 örnek üzerinden)
```bash
python agent3.py
```
`../agent2_cikti.json` içindeki örnekleri işler, `../agent3_cikti.json`'a yazar.

### Toplu (batch)
```bash
python run_batch.py -i ../agent2/cikti_agent2 -o ./cikti_agent3
```

Seçenekler:
- `--limit N` — sadece ilk N evrağı işle
- `--skip-existing` — output'ta zaten olanları atla

### Üslup kontrolünü tek başına test
```bash
python uslup_kontrol.py
```

---

## Dosya yapısı

```
agent3/
├── agent3.py             # Ana pipeline
├── sablonlar.py          # 8 şablon iskeleti + yardımcılar
├── uslup_kontrol.py      # Kural tabanlı üslup kontrolü
├── run_batch.py          # Toplu işleme
├── requirements.txt
├── README.md
└── .gitignore
```

---

## Şema

Detay: `../agent3_agent4_veri_sozlesmesi.md` (v1.0)

Örnek çıktı:
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
    "taslak_metni": "Sayın Ahmet Yılmaz,\n\n...",
    "eksik_alan_yer_tutucular": ["tc_kimlik"],
    "resmi_uslup_kontrolu": {
      "uygun_mu": true,
      "tespit_edilen_sorunlar": []
    }
  },
  "durum": "TASLAK_HAZIR_EKSIK_BILGI"
}
```

---

## Sözleşmenin uygulamada nasıl karşılandığı

| Sözleşme kuralı | Uygulama yeri |
|---|---|
| §0 — Şablon + slot-filling | `sablonlar.py` (deterministik iskelet) |
| §2 — 8 şablon türü | `SABLONLAR` dict + `sablon_turu_sec()` |
| §2 — Üslup kontrolü kural tabanlı | `uslup_kontrol.py` (regex/kelime listesi) |
| §3 — Durum kodu haritası | `durum_belirle()` |
| §5 — Uyarı bloğu her zaman en başta | `taslak_olustur()` sıralaması |
| §5 — Mevzuat >5 ise ilk 3 kullan | `govde_uret()` slicing |
| §5 — URETILEMEDI = boş gövde | `durum_belirle()` |
