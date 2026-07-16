"""
Agent 2 Değerlendirme Scripti
------------------------------
Agent 1 (sentetik veri üretici) her JSON'da `_meta_eksik_birakilan_alanlar` alanı
bırakıyor — bu, o evrakta hangi zorunlu alanın bilerek boş bırakıldığının ground
truth'u. Bu script Agent 2'nin `eksik_alanlar` çıktısını bununla karşılaştırıp
precision / recall / F1 hesaplar.

Ayrıca bilgi çıkarımı kalitesi için:
  - `on_cikarimlar` (Agent 1) vs `cikartilan_bilgiler` (Agent 2) alan bazlı doluluk

Kullanım:
    python degerlendir.py \\
        --agent1-dir ../cikti_agent1 \\
        --agent2-dir ./cikti_agent2
"""

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path


ZORUNLU_ALANLAR = {
    "DILEKCE": ["gonderici", "tc_kimlik", "konu", "tarih"],
    "BILGI_EDINME_BASVURUSU": ["gonderici", "tc_kimlik", "alici_kurum", "konu"],
    "SIKAYET_BASVURUSU": ["gonderici", "tc_kimlik", "konu"],
    "RESMI_UST_YAZI": ["gonderici", "alici_kurum", "belge_sayisi", "konu", "tarih", "imza_sahibi"],
    "CEVAP_YAZISI": ["gonderici", "alici_kurum", "belge_sayisi", "konu", "tarih"],
    "BILGILENDIRME_YAZISI": ["gonderici", "alici_kurum", "konu", "tarih"],
    "TALIMAT_YAZISI": ["gonderici", "alici_kurum", "konu", "tarih", "imza_sahibi"],
    "FATURA": ["gonderici", "tarih", "belge_sayisi"],
    "SOZLESME_PROTOKOL": ["gonderici", "alici_kurum", "tarih", "konu"],
    "TUTANAK_RAPOR": ["tarih", "konu"],
    "DIGER": [],
}


def prf(tp: int, fp: int, fn: int):
    """Precision, Recall, F1 hesapla."""
    p = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    r = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0.0
    return p, r, f1


def eksik_bilgi_degerlendir(agent1: dict, agent2: dict, alan_stats: dict):
    """
    Ground truth: _meta_eksik_birakilan_alanlar (Agent 1 bilerek boş bıraktı)
    Tahmin:      eksik_alanlar (Agent 2 tespit etti)

    Not: Ground truth SADECE zorunlu alanları kapsar (üretici bunu böyle
    tasarlamış). Ama eksik olabilecek başka alanlar da var (LLM'in tespit
    ettiği). Adil karşılaştırma için TP/FP/FN'i evrak türünün zorunlu
    alan kümesiyle sınırlıyoruz.
    """
    evrak_turu = agent2["evrak_turu"]
    zorunlular = set(ZORUNLU_ALANLAR.get(evrak_turu, []))

    ground_truth = set(agent1.get("_meta_eksik_birakilan_alanlar") or []) & zorunlular
    tahmin = set(agent2.get("eksik_alanlar") or []) & zorunlular

    tp = len(ground_truth & tahmin)
    fp = len(tahmin - ground_truth)
    fn = len(ground_truth - tahmin)

    # Alan bazlı ayrıntı
    for alan in ground_truth & tahmin:
        alan_stats[alan]["tp"] += 1
    for alan in tahmin - ground_truth:
        alan_stats[alan]["fp"] += 1
    for alan in ground_truth - tahmin:
        alan_stats[alan]["fn"] += 1

    return tp, fp, fn


def bilgi_cikarim_analiz(agent1: dict, agent2: dict, cikarim_stats: dict):
    """
    Agent 2, LLM ile Agent 1'in çıkardığı bilgileri zenginleştirmeli.
    Alan bazında: Agent 1 null ama Agent 2 doldurdu → İYİLEŞTİRME
                  Her ikisi de dolu ve eşit    → KORUNDU
                  Agent 1 dolu ama Agent 2 boş → REGRESYON (kod bug)
                  Her ikisi null               → BİLGİ YOK
    """
    a1 = agent1.get("on_cikarimlar") or {}
    a2 = agent2.get("cikartilan_bilgiler") or {}

    for alan in ["gonderici", "alici_kurum", "konu", "tarih",
                 "belge_sayisi", "tc_kimlik", "imza_sahibi"]:
        v1 = a1.get(alan)
        v2 = a2.get(alan)
        if v1 and not v2:
            cikarim_stats[alan]["regresyon"] += 1
        elif not v1 and v2:
            cikarim_stats[alan]["iyilestirme"] += 1
        elif v1 and v2:
            cikarim_stats[alan]["korundu"] += 1
        else:
            cikarim_stats[alan]["bilgi_yok"] += 1


def halusinasyon_kontrol(agent1: dict, agent2: dict, halusinasyon_stats: dict):
    """
    LLM'in Agent 1'in null bıraktığı alanlara yazdığı değerler ham metinde
    geçiyor mu? Geçmiyorsa halüsinasyon şüphesi.

    - TESPIT_EDILDI: Agent 2 doldurdu ve değer metinde geçiyor (temiz kurtarma)
    - HALUSINASYON  : Agent 2 doldurdu ama değer metinde YOK (uydurma şüphesi)
    - DOLDURMADI    : Agent 2 de null bıraktı (eksik)
    - AGENT1_DOLU   : Agent 1 zaten doldurmuştu (kapsam dışı)
    """
    a1 = agent1.get("on_cikarimlar") or {}
    a2 = agent2.get("cikartilan_bilgiler") or {}
    metin = (agent1.get("metin_icerigi") or {}).get("temizlenmis_metin") or ""
    metin_lower = metin.lower()

    for alan in ["gonderici", "alici_kurum", "konu", "tarih",
                 "belge_sayisi", "tc_kimlik", "imza_sahibi"]:
        v1 = a1.get(alan)
        v2 = a2.get(alan)

        if v1:
            halusinasyon_stats[alan]["agent1_dolu"] += 1
            continue

        if not v2:
            halusinasyon_stats[alan]["doldurmadi"] += 1
            continue

        # Agent 2 doldurmuş — değer metinde geçiyor mu?
        v2_str = str(v2).strip().lower()
        if not v2_str:
            halusinasyon_stats[alan]["doldurmadi"] += 1
            continue

        # Kaba eşleşme: değerin yarısından fazlası metinde geçiyorsa "bulundu"
        # Tarih için özel kural (2026-05-28 → 28.05.2026 olarak metinde olabilir)
        if alan == "tarih":
            parcalar = v2_str.split("-")
            if len(parcalar) == 3:
                # Yıl kesinlikle metinde olmalı
                yil = parcalar[0]
                gun_ay = parcalar[2] + "." + parcalar[1]
                if yil in metin and (gun_ay in metin or "-".join(parcalar) in metin_lower):
                    halusinasyon_stats[alan]["tespit_edildi"] += 1
                else:
                    halusinasyon_stats[alan]["halusinasyon"] += 1
            else:
                halusinasyon_stats[alan]["halusinasyon"] += 1
        else:
            if v2_str in metin_lower:
                halusinasyon_stats[alan]["tespit_edildi"] += 1
            else:
                # Kelime bazlı kısmi eşleşme (isim parçaları için)
                kelimeler = [k for k in v2_str.split() if len(k) > 2]
                if kelimeler and sum(k in metin_lower for k in kelimeler) >= max(1, len(kelimeler) // 2):
                    halusinasyon_stats[alan]["tespit_edildi"] += 1
                else:
                    halusinasyon_stats[alan]["halusinasyon"] += 1


def kurtarma_orani_hesapla(halusinasyon_stats: dict, alan: str):
    """Recovery rate: Agent 1 boş bırakmıştı, Agent 2 kaçını temiz kurtardı?"""
    s = halusinasyon_stats[alan]
    kurtarilabilir = s["tespit_edildi"] + s["halusinasyon"] + s["doldurmadi"]
    if kurtarilabilir == 0:
        return 0.0, 0.0
    temiz_kurtarma = s["tespit_edildi"] / kurtarilabilir
    halusinasyon_orani = s["halusinasyon"] / kurtarilabilir
    return temiz_kurtarma, halusinasyon_orani


def mevzuat_analiz(agent2: dict, mevzuat_stats: dict):
    """Türe göre mevzuat eşleşme sayısı."""
    tur = agent2["evrak_turu"]
    mevzuat_sayisi = len(agent2.get("ilgili_mevzuat") or [])
    mevzuat_stats[tur].append(mevzuat_sayisi)


def durum_analiz(agent2: dict, durum_sayaci: Counter):
    durum_sayaci[agent2["agent2_islem_metadata"]["durum"]] += 1


def bicim(deger, geniyakla=8):
    return f"{deger:>{geniyakla}}"


def main():
    parser = argparse.ArgumentParser(
        description="Agent 2 çıktılarını Agent 1 ground truth'a karşı değerlendirir."
    )
    parser.add_argument("--agent1-dir", type=Path, required=True,
                        help="Agent 1 JSON çıktı klasörü (ground truth)")
    parser.add_argument("--agent2-dir", type=Path, required=True,
                        help="Agent 2 JSON çıktı klasörü")
    parser.add_argument("--detay", action="store_true",
                        help="Alan ve tür bazlı ayrıntı raporu")
    args = parser.parse_args()

    args.agent1_dir = args.agent1_dir.expanduser().resolve()
    args.agent2_dir = args.agent2_dir.expanduser().resolve()

    agent2_dosyalari = sorted(args.agent2_dir.glob("*.json"))
    if not agent2_dosyalari:
        print(f"[HATA] Agent 2 çıktısı yok: {args.agent2_dir}", file=sys.stderr)
        sys.exit(1)

    toplam_tp = toplam_fp = toplam_fn = 0
    alan_stats = defaultdict(lambda: Counter())
    cikarim_stats = defaultdict(lambda: Counter())
    halusinasyon_stats = defaultdict(lambda: Counter())
    mevzuat_stats = defaultdict(list)
    durum_sayaci = Counter()
    tur_sayaci = Counter()
    islenen = 0
    hata = 0

    for a2_yol in agent2_dosyalari:
        a1_yol = args.agent1_dir / a2_yol.name
        if not a1_yol.exists():
            hata += 1
            continue

        try:
            with open(a1_yol, encoding="utf-8") as f:
                agent1 = json.load(f)
            with open(a2_yol, encoding="utf-8") as f:
                agent2 = json.load(f)
        except Exception as e:
            print(f"[UYARI] {a2_yol.name} okunamadı: {e}", file=sys.stderr)
            hata += 1
            continue

        tp, fp, fn = eksik_bilgi_degerlendir(agent1, agent2, alan_stats)
        toplam_tp += tp
        toplam_fp += fp
        toplam_fn += fn

        bilgi_cikarim_analiz(agent1, agent2, cikarim_stats)
        halusinasyon_kontrol(agent1, agent2, halusinasyon_stats)
        mevzuat_analiz(agent2, mevzuat_stats)
        durum_analiz(agent2, durum_sayaci)
        tur_sayaci[agent2["evrak_turu"]] += 1
        islenen += 1

    p, r, f1 = prf(toplam_tp, toplam_fp, toplam_fn)

    print(f"\n{'='*68}")
    print(f"AGENT 2 DEĞERLENDİRME RAPORU")
    print(f"{'='*68}")
    print(f"İşlenen evrak       : {islenen}")
    print(f"Okunamayan/eşleşmeyen: {hata}")

    print(f"\n--- EKSİK BİLGİ TESPİTİ ---")
    print(f"  True Positive  (doğru tespit)   : {toplam_tp}")
    print(f"  False Positive (yanlış alarm)   : {toplam_fp}")
    print(f"  False Negative (kaçan eksik)    : {toplam_fn}")
    print(f"  Precision : {p:.3f}")
    print(f"  Recall    : {r:.3f}")
    print(f"  F1        : {f1:.3f}")

    # --- YENİ: KURTARMA & HALÜSİNASYON ÖZETİ ---
    print(f"\n--- LLM KURTARMA & HALÜSİNASYON ÖZETİ ---")
    print(f"  (Agent 1 null bıraktığı alanlardan LLM'in ne kadarını doldurduğu)")
    print(f"  {'Alan':<15} {'Kurtarma':>10} {'Halusinasyon':>14} {'Doldurmadi':>12}")
    toplam_kurtarma_tp = 0
    toplam_kurtarma_hal = 0
    toplam_kurtarma_bos = 0
    for alan in ["gonderici", "alici_kurum", "konu", "tarih",
                 "belge_sayisi", "tc_kimlik", "imza_sahibi"]:
        s = halusinasyon_stats[alan]
        temiz, halu = kurtarma_orani_hesapla(halusinasyon_stats, alan)
        print(f"  {alan:<15} "
              f"{s['tespit_edildi']:>4} ({temiz*100:>3.0f}%) "
              f"{s['halusinasyon']:>5} ({halu*100:>3.0f}%)      "
              f"{s['doldurmadi']:>5}")
        toplam_kurtarma_tp += s["tespit_edildi"]
        toplam_kurtarma_hal += s["halusinasyon"]
        toplam_kurtarma_bos += s["doldurmadi"]

    genel = toplam_kurtarma_tp + toplam_kurtarma_hal + toplam_kurtarma_bos
    if genel > 0:
        print(f"  {'TOPLAM':<15} "
              f"{toplam_kurtarma_tp:>4} ({toplam_kurtarma_tp/genel*100:>3.0f}%) "
              f"{toplam_kurtarma_hal:>5} ({toplam_kurtarma_hal/genel*100:>3.0f}%)      "
              f"{toplam_kurtarma_bos:>5}")

    print(f"\n--- İŞLEM DURUMU DAĞILIMI ---")
    for durum, sayi in durum_sayaci.most_common():
        print(f"  {durum:20s}: {sayi}")

    print(f"\n--- EVRAK TÜRÜ DAĞILIMI ---")
    for tur, sayi in tur_sayaci.most_common():
        print(f"  {tur:25s}: {sayi}")

    if args.detay:
        print(f"\n--- ALAN BAZLI EKSİK TESPİT F1 ---")
        print(f"  {'Alan':<15} {'TP':>4} {'FP':>4} {'FN':>4} {'P':>6} {'R':>6} {'F1':>6}")
        for alan in sorted(alan_stats.keys()):
            s = alan_stats[alan]
            p_a, r_a, f1_a = prf(s['tp'], s['fp'], s['fn'])
            print(f"  {alan:<15} {s['tp']:>4} {s['fp']:>4} {s['fn']:>4} "
                  f"{p_a:>6.2f} {r_a:>6.2f} {f1_a:>6.2f}")

        print(f"\n--- BİLGİ ÇIKARIMI: Agent 1 → Agent 2 KATKISI ---")
        print(f"  {'Alan':<15} {'Iyilesme':>10} {'Korundu':>10} "
              f"{'Regresyon':>10} {'BilgiYok':>10}")
        for alan in ["gonderici", "alici_kurum", "konu", "tarih",
                     "belge_sayisi", "tc_kimlik", "imza_sahibi"]:
            s = cikarim_stats[alan]
            print(f"  {alan:<15} {s['iyilestirme']:>10} {s['korundu']:>10} "
                  f"{s['regresyon']:>10} {s['bilgi_yok']:>10}")

        print(f"\n--- MEVZUAT EŞLEŞME (ortalama) ---")
        for tur in sorted(mevzuat_stats.keys()):
            sayilar = mevzuat_stats[tur]
            ort = sum(sayilar) / len(sayilar) if sayilar else 0
            print(f"  {tur:25s}: ort {ort:.1f}, min {min(sayilar)}, max {max(sayilar)}")

    print(f"{'='*68}\n")


if __name__ == "__main__":
    main()
