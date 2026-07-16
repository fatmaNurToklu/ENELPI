# -*- coding: utf-8 -*-
"""
TF-IDF + LinearSVC ML sınıflandırıcı (yedek yol).

Kural tabanlı sınıflandırıcı net sonuç üretemediğinde devreye girer.
Veri seti: cikti/json/*.json dosyalarındaki temizlenmis_metin → evrak_turu.

Fonksiyonlar:
  egit()      : modeli eğitir ve diske kaydeder
  yukle()     : kaydedilmiş modeli yükler
  tahmin_et() : tek metin için (tur, guven, alternatifler) döner
"""
import json
import pickle
import re
from pathlib import Path

import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import SGDClassifier
from sklearn.metrics import classification_report
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder

MODEL_YOLU = Path(__file__).parent / "model" / "tfidf_svc.pkl"
MODEL_YOLU.parent.mkdir(exist_ok=True)

JSON_DIR = Path(__file__).parent / "cikti" / "json"


# ── Türkçe için basit tokenizer ─────────────────────────────────────────────

_TR_LOWER = str.maketrans("İIŞĞÜÖÇ", "işğüöç".replace("ş", "ş") + "i")  # düzeltilmiş versiyon

def _tr_lower(metin: str) -> str:
    return (metin
            .replace("İ", "i").replace("I", "ı")
            .replace("Ş", "ş").replace("Ğ", "ğ")
            .replace("Ü", "ü").replace("Ö", "ö")
            .replace("Ç", "ç").lower())

def _on_isle_metin(metin: str) -> str:
    """TF-IDF için metin normalleştirme: küçük harf + Türkçe stop-word benzeri gürültü kaldırma."""
    metin = _tr_lower(metin)
    # Belge numarası, tarih gibi değişken token'ları maskele
    metin = re.sub(r"\d{2}\.\d{2}\.\d{4}", " TARIH ", metin)
    metin = re.sub(r"e-\d{5,}-[\d\.]+", " BELGE_NO ", metin)
    metin = re.sub(r"\b\d{11}\b", " TC_KIMLIK ", metin)
    metin = re.sub(r"\b\d+\b", " SAYI ", metin)
    # Noktalama kaldır
    metin = re.sub(r"[^\w\s]", " ", metin)
    metin = re.sub(r"\s{2,}", " ", metin)
    return metin.strip()


# ── Veri yükleme ─────────────────────────────────────────────────────────────

def _veri_yukle() -> tuple[list[str], list[str]]:
    metinler, etiketler = [], []
    for dosya in sorted(JSON_DIR.glob("*.json")):
        veri = json.load(open(dosya, encoding="utf-8"))
        ham = veri["metin_icerigi"]["temizlenmis_metin"]
        tur = veri["siniflandirma_sonucu"]["evrak_turu"]
        if ham and tur:
            metinler.append(_on_isle_metin(ham))
            etiketler.append(tur)
    return metinler, etiketler


# ── Model pipeline ────────────────────────────────────────────────────────────

def _pipeline_olustur() -> Pipeline:
    """
    TF-IDF (karakter + kelime n-gram birlikte) + CalibratedClassifierCV(SGD).
    Neden bu kombinasyon:
      - Karakter n-gram (2-4): Türkçe eklerini (sınıflandırma, başvurusu, vb.) yakalar
      - Kelime n-gram (1-2): "bilgi edinme", "arz ederim" gibi sabit ifadeleri tutar
      - SGD + kalibrasyon: hızlı, az veriyle iyi çalışır, softmax olasılık üretir
        (LinearSVC doğrudan olasılık üretemez ama CalibratedClassifierCV ile sarar)
    """
    vektorizer = TfidfVectorizer(
        analyzer="char_wb",
        ngram_range=(2, 4),
        max_features=40_000,
        sublinear_tf=True,
    )
    # Kelime n-gram ile birleştir
    from sklearn.pipeline import FeatureUnion
    from sklearn.feature_extraction.text import TfidfVectorizer as TV

    kelime_vec = TV(
        analyzer="word",
        ngram_range=(1, 2),
        max_features=20_000,
        sublinear_tf=True,
    )

    birlesik = FeatureUnion([
        ("char_tfidf", vektorizer),
        ("word_tfidf", kelime_vec),
    ])

    sgd = SGDClassifier(
        loss="modified_huber",   # olasılık üretebilir
        alpha=1e-4,
        max_iter=1000,
        random_state=42,
        class_weight="balanced",
    )
    kalibre = CalibratedClassifierCV(sgd, cv=3, method="sigmoid")

    return Pipeline([
        ("ozellik", birlesik),
        ("siniflandirici", kalibre),
    ])


# ── Eğitim ───────────────────────────────────────────────────────────────────

def egit(rapor_yazdir: bool = True) -> Pipeline:
    """
    Tüm veri setiyle modeli eğitir, diske kaydeder.
    Çapraz doğrulama (5-fold) ile gerçek performansı da raporlar.
    """
    print("Veri yükleniyor...")
    metinler, etiketler = _veri_yukle()
    print(f"{len(metinler)} örnek, {len(set(etiketler))} sınıf yüklendi.")

    pipeline = _pipeline_olustur()

    if rapor_yazdir:
        print("\n── 5-Fold Çapraz Doğrulama ─────────────────────────────────────")
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        tahminler = cross_val_predict(pipeline, metinler, etiketler, cv=cv)
        print(classification_report(etiketler, tahminler, zero_division=0))

    print("\nTüm veri setiyle final model eğitiliyor...")
    pipeline.fit(metinler, etiketler)

    with open(MODEL_YOLU, "wb") as f:
        pickle.dump(pipeline, f)
    print(f"Model kaydedildi: {MODEL_YOLU}")

    return pipeline


# ── Yükleme / tahmin ─────────────────────────────────────────────────────────

_yuklu_pipeline: Pipeline | None = None


def yukle() -> Pipeline:
    global _yuklu_pipeline
    if _yuklu_pipeline is None:
        if not MODEL_YOLU.exists():
            print("Model bulunamadı, eğitiliyor...")
            _yuklu_pipeline = egit(rapor_yazdir=False)
        else:
            with open(MODEL_YOLU, "rb") as f:
                _yuklu_pipeline = pickle.load(f)
    return _yuklu_pipeline


def tahmin_et(metin: str, ilk_n: int = 3) -> tuple[str, float, list[dict]]:
    """
    Tek metin için ML tahmini.

    Dönüş:
      (evrak_turu, guven_skoru, alternatif_tahminler)
      - alternatif_tahminler: [{"tur": ..., "skor": ...}, ...]  (ilk_n-1 alternatif)
    """
    model = yukle()
    islenm = _on_isle_metin(metin)
    olasiliklar = model.predict_proba([islenm])[0]
    siniflar = model.classes_

    sirali = sorted(zip(siniflar, olasiliklar), key=lambda x: -x[1])
    en_iyi_tur, en_iyi_skor = sirali[0]
    alternatifler = [
        {"tur": t, "skor": round(float(s), 4)}
        for t, s in sirali[1:ilk_n]
    ]
    return en_iyi_tur, round(float(en_iyi_skor), 4), alternatifler


if __name__ == "__main__":
    egit(rapor_yazdir=True)
