# Agent 2 — İçerik Analizi & Mevzuat Eşleştirme

TEKNOFEST TYDA yarışması kapsamında Agent 1 (OCR + sınıflandırma) çıktısını alan
ve şu 4 modülü çalıştıran ajan:

1. **Bilgi çıkarımı** — LLM + regex + Agent 1 seed hibrit yaklaşımı
2. **Eksik bilgi tespiti** — evrak türüne göre zorunlu alan kontrolü
3. **Mevzuat eşleştirme** — ChromaDB RAG ile ilgili kanun/maddeleri bulma
4. **Özetleme** — Agent 3 için 2-3 cümlelik bağlam özeti

Çıktı formatı `agent2_agent3_veri_sozlesmesi.md`'de (v1.0) tanımlıdır.

---

## Mimari

```
Agent 1 JSON
    ↓
┌───────────────────────────────────────────────┐
│  agent2.py                                    │
│                                               │
│  1. agent1_girdisini_isle()                   │
│     - BASARISIZ ise manuel kuyruğa           │
│                                               │
│  2. bilgi_cikar()  ← ÜÇ KATMANLI              │
│     a) Agent 1 on_cikarimlar (ground truth)   │
│     b) Regex pre-extract (Konu:, Sayı:, TC..) │
│     c) LLM (Gemma2:9b, sıkı prompt)           │
│     d) Halüsinasyon filtresi (metinde ara)    │
│     e) Unvan filtresi (Şube Müdürü → null)    │
│                                               │
│  3. mevzuat_ara()                             │
│     - ChromaDB semantic search                │
│     - Tür filtresi + distance eşiği + top_k=3 │
│                                               │
│  4. eksik_bilgi_tespit()                      │
│     - Türe göre zorunlu alan listesi         │
│                                               │
│  5. ozetle() → LLM                            │
└───────────────────────────────────────────────┘
    ↓
Agent 2 JSON  →  Agent 3
```

---

## Kurulum

Ollama gerekli (LLM ve embedding için):
```bash
# Ollama kurulumu: https://ollama.com
ollama pull gemma2:9b
ollama pull nomic-embed-text
```

Python bağımlılıkları:
```bash
pip install -r requirements.txt
```

Mevzuat veritabanını ChromaDB'ye yükle (bir kere):
```bash
python chroma_yukle.py
```

---

## Kullanım

### Tek dosya (test)
```bash
python agent2.py
```
`../ornek.json` içindeki örnekleri işler, `../agent2_cikti.json`'a yazar.

### Toplu (batch)
```bash
python run_batch.py -i /path/to/agent1/json -o ./cikti_agent2
```

Seçenekler:
- `--limit N` — sadece ilk N evrağı işle (test için)
- `--skip-existing` — output'ta zaten olanları atla (kaldığın yerden devam)

### Değerlendirme
```bash
python degerlendir.py --agent1-dir /path/to/agent1/json --agent2-dir ./cikti_agent2 --detay
```

Rapor içeriği:
- Eksik bilgi tespiti F1/Precision/Recall (Agent 1'in `_meta_eksik_birakilan_alanlar` ground truth'una karşı)
- LLM kurtarma & halüsinasyon oranı
- Alan bazlı F1
- Türe göre mevzuat eşleşme sayısı

---

## Performans (165 evrak, sentetik veri seti)

| Metrik | Değer |
|---|---|
| F1 (eksik bilgi tespiti) | 0.81 |
| Precision | 1.00 |
| Halüsinasyon oranı | %0 |
| Sıfır regresyon | ✓ (Agent 1'in çıkardığı bilgi hiç kaybolmaz) |

### Halüsinasyon savunma katmanları

1. **Agent 1 seed önceliği**: LLM Agent 1'in çıkardığı alanları override edemez
2. **Regex pre-extract**: `Konu:`, `Sayı:`, TC, tarih, Ad Soyad pattern'ları
3. **Placeholder reddi**: "None", "boş", "belirsiz" → null
4. **Unvan filtresi**: Kişi ismi bekleyen alana unvan yazılmaz
5. **Metin doğrulama**: LLM çıkardığı isim/kurum ham metinde geçmelidir

---

## Dosya yapısı

```
agent2/
├── agent2.py             # Ana pipeline
├── mevzuat_db.py         # 21 mevzuat maddesi
├── chroma_yukle.py       # ChromaDB yükleyici
├── run_batch.py          # Toplu işleme
├── degerlendir.py        # Metrik raporu
├── chroma_veri/          # ChromaDB kalıcı depo (git-ignore)
├── requirements.txt
└── README.md
```

---

## Şema

Detay: `../agent2_agent3_veri_sozlesmesi.md` (v1.0)

Örnek çıktı:
```json
{
  "sema_versiyonu": "1.0",
  "agent2_islem_metadata": {
    "evrak_id": "EVR-2026-0001",
    "islem_zamani": "2026-07-14T22:17:08",
    "durum": "EKSIK_BILGI",
    "manuel_inceleme_onerisi": false,
    "agent1_durum": "BASARILI",
    "agent1_siniflandirma_skoru": 0.91
  },
  "evrak_turu": "BILGI_EDINME_BASVURUSU",
  "cikartilan_bilgiler": { ... },
  "ilgili_mevzuat": [ ... ],
  "eksik_alanlar": ["tc_kimlik"],
  "ozet": "..."
}
```
