"""
Agent 3 Batch Runner
--------------------
Bir klasördeki tüm Agent 2 çıktı JSON dosyalarını işler, her biri için
Agent 3 çıktısı üretir ve output klasörüne yazar.

Kullanım:
    python run_batch.py -i /path/to/agent2/json -o ./cikti_agent3
    python run_batch.py -i ../agent2/cikti_agent2 -o ./cikti_agent3 --limit 10
"""

import argparse
import json
import sys
import time
from pathlib import Path

from agent3 import taslak_uret


def main():
    parser = argparse.ArgumentParser(
        description="Agent 3 — Agent 2 çıktı klasörünü toplu işler."
    )
    parser.add_argument("-i", "--input-dir", type=Path, required=True,
                        help="Agent 2 JSON çıktılarının bulunduğu klasör")
    parser.add_argument("-o", "--output-dir", type=Path, required=True,
                        help="Agent 3 çıktılarının yazılacağı klasör")
    parser.add_argument("--limit", type=int, default=None,
                        help="Sadece ilk N evrağı işle (test için)")
    parser.add_argument("--skip-existing", action="store_true",
                        help="Output klasöründe zaten olanları atla")
    args = parser.parse_args()

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

    basarili = uretilemedi = atlanan = basarisiz = 0
    durum_sayaci = {}
    baslangic = time.time()

    for i, dosya in enumerate(json_dosyalari, 1):
        cikti_yolu = args.output_dir / dosya.name
        if args.skip_existing and cikti_yolu.exists():
            atlanan += 1
            continue

        try:
            with open(dosya, encoding="utf-8") as f:
                agent2_cikti = json.load(f)

            sonuc = taslak_uret(agent2_cikti)

            with open(cikti_yolu, "w", encoding="utf-8") as f:
                json.dump(sonuc, f, ensure_ascii=False, indent=2)

            d = sonuc["durum"]
            durum_sayaci[d] = durum_sayaci.get(d, 0) + 1
            if d == "URETILEMEDI":
                uretilemedi += 1
                durum_ikon = "X"
            else:
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
    print(f"  Basarili       : {basarili}")
    print(f"  Uretilemedi    : {uretilemedi}")
    print(f"  Atlanan        : {atlanan}")
    print(f"  Basarisiz      : {basarisiz}")
    print(f"\n  Durum dagilimi:")
    for durum, sayi in sorted(durum_sayaci.items()):
        print(f"    {durum:40s}: {sayi}")


if __name__ == "__main__":
    main()
