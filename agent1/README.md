# Agent 1 — Sentetik Veri Üretici

TEKNOFEST TYDA şartname madde 6.5 gereği gerçek kamu verisi kullanılamadığı için,
Agent 1'in (OCR + sınıflandırma) test ve geliştirme verisini üreten araç.

## Kurulum
```bash
pip install faker jinja2 reportlab pdf2image pillow numpy
# pdf2image için sistemde poppler-utils kurulu olmalı (pdftoppm)
```

## Çalıştırma
```bash
python3 olustur_veri_seti.py --adet 15 --eksik-oran 0.35 --taranmis-oran 0.4 --seed 42
```

| Parametre | Açıklama | Varsayılan |
|---|---|---|
| `--adet` | Her evrak türü için kaç kayıt üretilecek (11 tür var) | 15 |
| `--eksik-oran` | Zorunlu alanların kasıtlı `null` bırakılma olasılığı (eksik-bilgi tespiti testi için) | 0.35 |
| `--taranmis-oran` | Kayıtların ne kadarının "taranmış görüntü" (gürültü+eğiklik) olarak simüle edileceği | 0.4 |
| `--seed` | Tekrarlanabilirlik için rastgelelik tohumu | 42 |

## Çıktı yapısı
```
cikti/
  pdf/EVR-2026-XXXX.pdf        -> her evrak için temiz PDF (PDF_METIN_KATMANI yolu için)
  gorsel/EVR-2026-XXXX.png     -> sadece taranmış simüle edilenler (TARANMIS_GORUNTU yolu için)
  json/EVR-2026-XXXX.json      -> ground truth, agent1_agent2_veri_sozlesmesi.md şemasına (v1.0) uygun
  veri_seti_ozet.json          -> tüm kayıtlar + tür dağılımı istatistiği tek dosyada
```

## Nasıl kullanılır

- **OCR pipeline testi**: `cikti/gorsel/*.png` dosyalarını OCR motoruna (Tesseract/PaddleOCR) ver,
  çıkan metni `cikti/json/*.json` içindeki `metin_icerigi.temizlenmis_metin` ile karşılaştırarak
  karakter/kelime hata oranını (CER/WER) ölç.
- **Sınıflandırma eğitimi/testi**: `cikti/json/*.json` dosyalarındaki `temizlenmis_metin` → `evrak_turu`
  çiftlerini etiketli veri olarak kullan (örn. TF-IDF+SVC eğitimi).
- **Eksik bilgi tespiti testi (Nur için)**: her JSON'daki `_meta_eksik_birakilan_alanlar` listesi,
  o evrakta hangi zorunlu alanın bilerek boş bırakıldığını söyler — Agent 2'nin doğru tespit edip
  etmediğini bununla doğrulayabilirsiniz.
- **`_meta_*` alanları kontrat şemasının PARÇASI DEĞİLDİR** — sadece üretim/değerlendirme amaçlı
  yardımcı bilgidir. Gerçek Agent 1 çıktısı bu alanları içermeyecek, gerçek OCR/sınıflandırma
  sonucu üretecek (`ocr_guven_skoru`, `siniflandirma_guven_skoru` gibi alanlar burada `null`/`1.0`
  çünkü bu ground truth, henüz OCR/ML'den geçmemiş veri).

## Evrak türleri (11 adet)
DILEKCE, BILGI_EDINME_BASVURUSU, SIKAYET_BASVURUSU, RESMI_UST_YAZI, CEVAP_YAZISI,
BILGILENDIRME_YAZISI, TALIMAT_YAZISI, FATURA, SOZLESME_PROTOKOL, TUTANAK_RAPOR, DIGER

Zorunlu alan eşlemesi `agent1_agent2_veri_sozlesmesi.md` §4 ile birebir senkronizedir —
taksonomi değişirse iki dosyayı birlikte güncelleyin.

## Genişletme fikirleri
- `govdeler.py` içindeki şablonlara yeni varyasyonlar eklemek metinsel çeşitliliği artırır.
- `render.py`'deki bozulma parametrelerini (`egiklik_derece_araligi`, `gurultu_yogunlugu_araligi`)
  daha zorlu OCR senaryoları için genişletebilirsiniz.
- Gövde cümlelerini şu an sabit bir havuzdan rastgele seçiyoruz; isterseniz bir LLM API çağrısıyla
  (Anthropic API, kontrat dokümanındaki örnekteki gibi) daha doğal/çeşitli gövde metinleri
  ürettirip aynı pipeline'a entegre edebilirsiniz.
