"""
Agent 2 Batch Runner
--------------------
Bir klasördeki tüm Agent 1 çıktısı JSON dosyalarını işler, her biri için
Agent 2 çıktısı üretir ve output klasörüne yazar.

Kullanım:
    python run_batch.py --input-dir /path/to/agent1/json --output-dir ./cikti_agent2
    python run_batch.py -i ../../cikti/json -o ./cikti_agent2 --limit 10
"""

import argparse
import json
import sys
import time
from pathlib import Path

from agent2 import (
    agent1_girdisini_isle,
    bilgi_cikar,
    mevzuat_ara,
    eksik_bilgi_tespit,
    ozetle,
    cikti_olustur,
)


def evrak_isle(agent1_json: dict) -> dict:
    """Tek bir Agent 1 çıktısını işleyip Agent 2 çıktısına çevirir."""
    metin, evrak_turu, on_cikarimlar = agent1_girdisini_isle(agent1_json)

    if metin is None:
        return None  # BASARISIZ, manuel kuyruğa

    cikartilan = bilgi_cikar(metin, evrak_turu, on_cikarimlar)
    mevzuat = mevzuat_ara(cikartilan.get("konu") or metin[:100], evrak_turu)
    eksikler = eksik_bilgi_tespit(cikartilan, evrak_turu)
    ozet = ozetle(metin, cikartilan, mevzuat, eksikler)

    return cikti_olustur(agent1_json, evrak_turu, cikartilan, mevzuat, eksikler, ozet)


def main():
    parser = argparse.ArgumentParser(
        description="Agent 2 — Agent 1 çıktı klasörünü toplu işler."
    )
    parser.add_argument(
        "-i", "--input-dir", type=Path, required=True,
        help="Agent 1 JSON çıktılarının bulunduğu klasör"
    )
    parser.add_argument(
        "-o", "--output-dir", type=Path, required=True,
        help="Agent 2 çıktılarının yazılacağı klasör"
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Sadece ilk N evrağı işle (test için)"
    )
    parser.add_argument(
        "--skip-existing", action="store_true",
        help="Output klasöründe zaten olan evrakları atla"
    )
    args = parser.parse_args()

    # ~/ ve göreli yol kısayollarını genişlet
    args.input_dir = args.input_dir.expanduser().resolve()
    args.output_dir = args.output_dir.expanduser().resolve()

    if not args.input_dir.is_dir():
        print(f"[HATA] input-dir bulunamadı: {args.input_dir}", file=sys.stderr)
        sys.exit(1)

    args.output_dir.mkdir(parents=True, exist_ok=True)

    json_dosyalari = sorted(args.input_dir.glob("*.json"))
    if args.limit:
        json_dosyalari = json_dosyalari[:args.limit]

    print(f"Toplam {len(json_dosyalari)} dosya işlenecek.")
    print(f"Input:  {args.input_dir}")
    print(f"Output: {args.output_dir}\n")

    basarili = 0
    basarisiz = 0
    atlanan = 0
    manuel_kuyruk = 0
    baslangic = time.time()

    for i, dosya in enumerate(json_dosyalari, 1):
        cikti_yolu = args.output_dir / dosya.name

        if args.skip_existing and cikti_yolu.exists():
            atlanan += 1
            continue

        try:
            with open(dosya, encoding="utf-8") as f:
                agent1_cikti = json.load(f)

            sonuc = evrak_isle(agent1_cikti)

            if sonuc is None:
                manuel_kuyruk += 1
                durum_ikon = "M"
            else:
                with open(cikti_yolu, "w", encoding="utf-8") as f:
                    json.dump(sonuc, f, ensure_ascii=False, indent=2)
                basarili += 1
                durum_ikon = "OK"

            gecen = time.time() - baslangic
            hiz = i / gecen if gecen > 0 else 0
            kalan = (len(json_dosyalari) - i) / hiz if hiz > 0 else 0
            print(
                f"[{i:>3}/{len(json_dosyalari)}] {dosya.name} [{durum_ikon}] "
                f"({hiz:.1f}/s, ~{kalan:.0f}s kaldı)"
            )

        except Exception as e:
            basarisiz += 1
            print(f"[{i:>3}/{len(json_dosyalari)}] {dosya.name} [HATA] {e}",
                  file=sys.stderr)

    toplam_sure = time.time() - baslangic
    print(f"\n{'='*60}")
    print(f"BITTI - Toplam süre: {toplam_sure:.1f}s")
    print(f"  Basarili         : {basarili}")
    print(f"  Manuel kuyruk    : {manuel_kuyruk}")
    print(f"  Atlanan (mevcut) : {atlanan}")
    print(f"  Basarisiz        : {basarisiz}")


if __name__ == "__main__":
    main()
