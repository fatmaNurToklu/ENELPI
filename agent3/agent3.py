"""
Agent 3 — Resmi Yazı Taslaklama
--------------------------------
Can'ın Agent 3 → Agent 4 veri sözleşmesi (v1.0) uygulaması.

Yaklaşım (sözleşme §0):
  Şablon + slot-filling
  - Deterministik iskelet (hitap, kapanış, uyarı, eksik-bilgi bloğu) → kod
  - Gövde paragrafı → yalnızca burayı Gemma2:9b üretir
  - Bu sayede LLM halüsinasyonu şablon güvenliğinden bağımsız

Pipeline:
  1. Agent 2 JSON'ı oku
  2. Şablon türünü seç (evrak_turu → sablon_turu)
  3. LLM ile gövde paragrafı üret
  4. Şablon + gövde + eksik bilgi + uyarı → tam taslak
  5. Gövdeyi kural tabanlı üslup kontrolünden geçir
  6. Durumu belirle
  7. Agent 3 çıktı JSON'ı döndür
"""

import json
import re
from datetime import datetime
from typing import Optional

from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage

from sablonlar import (
    SABLONLAR,
    UYARI_BLOGU,
    sablon_turu_sec,
    hitap_belirle,
    alici_kurum_atfi_olustur,
    alici_kurum_hitap_olustur,
    ilk_mevzuat_atfi_olustur,
    eksik_bilgi_blogu_olustur,
)
from uslup_kontrol import uslup_kontrol_et


# === LLM ===
llm = ChatOllama(
    model="gemma2:9b",
    base_url="http://localhost:11434",
    temperature=0.3,  # Biraz yaratıcılık ama tutarlı kalsın
)

SISTEM_PROMPTU = (
    "Sen bir Türk kamu evrakı yanıt uzmanısın. "
    "Sadece 1 paragraf resmi yazı gövdesi üretirsin. "
    "Hitap veya kapanış YAZMA — bunlar şablondan gelir. "
    "Resmi, nazik, kişisel olmayan bir dil kullan. "
    "İkinci tekil şahıs (sen, senin) YASAK. "
    "Sadece paragrafı döndür, başlık/açıklama ekleme."
)


# === ADIM 1: LLM ile gövde paragrafı üret ===
def govde_uret(cikartilan: dict,
               ozet: str,
               mevzuat: list,
               evrak_turu: str) -> str:
    """
    Sözleşme §0: Sadece gövde paragrafı LLM'e bırakılır.
    Prompt'a en fazla 2-3 mevzuat verilir (sözleşme §5).
    """
    # Mevzuat listesini kısıtla
    mevzuat_ozet = ""
    if mevzuat:
        secilenler = mevzuat[:3]
        mevzuat_ozet = "\n".join(
            f"- {m['kanun']} {m['madde']}: {m['metin'][:200]}"
            for m in secilenler
        )

    prompt = f"""Aşağıdaki bilgilere dayanarak, resmi bir yanıt yazısının SADECE GÖVDE PARAGRAFINI (1 paragraf, 2-4 cümle) üret:

Evrak türü: {evrak_turu}
Konu: {cikartilan.get('konu') or '(belirtilmemiş)'}
Gönderen: {cikartilan.get('gonderici') or '(belirtilmemiş)'}
Özet: {ozet}

İlgili mevzuat:
{mevzuat_ozet or '(yok)'}

Kurallar:
- SADECE gövde paragrafı, hitap ("Sayın X") veya kapanış ("Saygılarımızla") YAZMA
- İkinci tekil şahıs (sen, senin) KULLANMA — resmi çoğul kullan (siz, sizin)
- Argo, gündelik dil, emoji YASAK
- Türkçe, resmi, nezih bir üslup
- Mevzuata atıf yapabilirsin ama tekrar etmek zorunda değilsin
- 2-4 cümle yeterli"""

    try:
        yanit = llm.invoke([
            SystemMessage(content=SISTEM_PROMPTU),
            HumanMessage(content=prompt),
        ])
        govde = yanit.content.strip()
        # Markdown/code fence temizle
        govde = re.sub(r"^```[a-z]*\n?", "", govde)
        govde = re.sub(r"\n?```$", "", govde)
        # Hitap/kapanış sızıntısı temizle
        govde = re.sub(r"^(Sayın[^\n]+\n\n?)", "", govde, flags=re.IGNORECASE)
        govde = re.sub(r"\n\n?Saygılarımızla[^\n]*$", "", govde, flags=re.IGNORECASE)
        return govde.strip()
    except Exception as e:
        print(f"  [UYARI] govde_uret hatası: {e}")
        return ""


# === ADIM 2: Şablon + gövde birleştirme (deterministik) ===
def taslak_olustur(sablon_turu: str,
                   cikartilan: dict,
                   ilk_mevzuat_atfi: str,
                   govde: str,
                   eksik_alanlar: list,
                   uyari_ekle: bool,
                   evrak_turu: str) -> str:
    """
    Tam taslak metni oluşturur.
    Sıralama (sözleşme §5): [UYARI] → hitap+giriş → gövde → eksik-bilgi → kapanış
    """
    sablon = SABLONLAR.get(sablon_turu, SABLONLAR["GENEL_AMACLI"])

    hitap = hitap_belirle(cikartilan, evrak_turu)
    alici_kurum_atfi = alici_kurum_atfi_olustur(cikartilan)
    alici_kurum_hitap = alici_kurum_hitap_olustur(cikartilan)
    konu = cikartilan.get("konu") or "(belirtilmemiş)"

    # Şablon yer tutucularını doldur
    ust_blok = sablon["ust_blok"].format(
        hitap=hitap,
        konu=konu,
        alici_kurum_atfi=alici_kurum_atfi,
        alici_kurum_hitap=alici_kurum_hitap,
        ilk_mevzuat_atfi=ilk_mevzuat_atfi,
    )
    alt_blok = sablon["alt_blok"]

    # Bileşenleri birleştir (sözleşme §5 sıralaması)
    parcalar = []
    if uyari_ekle:
        parcalar.append(UYARI_BLOGU)
    parcalar.append(ust_blok)
    if govde:
        parcalar.append(govde)
    eksik_blok = eksik_bilgi_blogu_olustur(eksik_alanlar)
    if eksik_blok:
        parcalar.append(eksik_blok)
    parcalar.append(alt_blok)

    return "".join(parcalar)


# === ADIM 3: Durum belirleme ===
def durum_belirle(agent2_durum: str, govde: str) -> str:
    """
    Sözleşme §3 haritası:
      TAMAMLANDI      → TASLAK_HAZIR
      EKSIK_BILGI     → TASLAK_HAZIR_EKSIK_BILGI
      MANUEL_INCELEME → TASLAK_HAZIR_MANUEL_INCELEME_UYARILI
      Gövde boş       → URETILEMEDI
    """
    if not govde or not govde.strip():
        return "URETILEMEDI"

    haritalar = {
        "TAMAMLANDI": "TASLAK_HAZIR",
        "EKSIK_BILGI": "TASLAK_HAZIR_EKSIK_BILGI",
        "MANUEL_INCELEME": "TASLAK_HAZIR_MANUEL_INCELEME_UYARILI",
    }
    return haritalar.get(agent2_durum, "TASLAK_HAZIR")


# === ADIM 4: Kaynak bağlam özeti (sözleşme §2) ===
def kaynak_baglam_olustur(agent2_cikti: dict) -> dict:
    """
    Agent 4 için Agent 2 çıktısından asgari alt küme.
    Tam kopya değil — sadece durum, tür, eksik alan sayısı, mevzuat sayısı.
    """
    return {
        "evrak_turu": agent2_cikti["evrak_turu"],
        "agent2_durum": agent2_cikti["agent2_islem_metadata"]["durum"],
        "eksik_alanlar": agent2_cikti.get("eksik_alanlar", []),
        "mevzuat_sayisi": len(agent2_cikti.get("ilgili_mevzuat", [])),
    }


# === ANA PIPELINE ===
def taslak_uret(agent2_cikti: dict) -> dict:
    """
    Agent 2 çıktısını alır, sözleşme v1.0'a uygun Agent 3 çıktısı döndürür.
    """
    evrak_id = agent2_cikti["agent2_islem_metadata"]["evrak_id"]
    evrak_turu = agent2_cikti["evrak_turu"]
    agent2_durum = agent2_cikti["agent2_islem_metadata"]["durum"]
    cikartilan = agent2_cikti.get("cikartilan_bilgiler", {})
    mevzuat = agent2_cikti.get("ilgili_mevzuat", [])
    eksik_alanlar = agent2_cikti.get("eksik_alanlar", [])
    ozet = agent2_cikti.get("ozet", "")

    sablon_turu = sablon_turu_sec(evrak_turu)
    ilk_mevzuat_atfi = ilk_mevzuat_atfi_olustur(mevzuat)
    uyari_ekle = (agent2_durum == "MANUEL_INCELEME")

    # 1. LLM ile gövde üret
    govde = govde_uret(cikartilan, ozet, mevzuat, evrak_turu)

    # 2. Şablon + gövde birleştir
    taslak_metni = taslak_olustur(
        sablon_turu=sablon_turu,
        cikartilan=cikartilan,
        ilk_mevzuat_atfi=ilk_mevzuat_atfi,
        govde=govde,
        eksik_alanlar=eksik_alanlar,
        uyari_ekle=uyari_ekle,
        evrak_turu=evrak_turu,
    )

    # 3. Sadece gövdeyi üslup kontrolünden geçir (sözleşme §2)
    uslup_sonucu = uslup_kontrol_et(govde)

    # 4. Durum
    durum = durum_belirle(agent2_durum, govde)

    return {
        "sema_versiyonu": "1.0",
        "evrak_id": evrak_id,
        "kaynak_baglam": kaynak_baglam_olustur(agent2_cikti),
        "uretilen_taslak": {
            "sablon_turu": sablon_turu,
            "taslak_metni": taslak_metni,
            "eksik_alan_yer_tutucular": list(eksik_alanlar),
            "resmi_uslup_kontrolu": uslup_sonucu,
        },
        "durum": durum,
    }


if __name__ == "__main__":
    from pathlib import Path

    # Hızlı test: Agent 2 örnek çıktısı üzerinden
    ornek_yolu = Path(__file__).parent.parent / "agent2_cikti.json"
    if not ornek_yolu.exists():
        print(f"[HATA] {ornek_yolu} bulunamadı.")
        raise SystemExit(1)

    with open(ornek_yolu, encoding="utf-8") as f:
        ornekler = json.load(f)

    ciktilar = []
    for a2 in ornekler:
        print(f"\n=== {a2['agent2_islem_metadata']['evrak_id']} ===")
        cikti = taslak_uret(a2)
        print(json.dumps(cikti, ensure_ascii=False, indent=2))
        ciktilar.append(cikti)

    cikti_yolu = Path(__file__).parent.parent / "agent3_cikti.json"
    with open(cikti_yolu, "w", encoding="utf-8") as f:
        json.dump(ciktilar, f, ensure_ascii=False, indent=2)
    print(f"\n{cikti_yolu.name} kaydedildi.")
