from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage
from typing import Optional
import json
import chromadb
from chromadb.utils.embedding_functions import OllamaEmbeddingFunction
from mevzuat_db import mevzuat_listesi
import re
from datetime import datetime

# === MODEL TANIMLAMALARI ===
# LLM: Metin analizi ve özetleme için Gemma2:9b
llm = ChatOllama(
    model="gemma2:9b",
    base_url="http://localhost:11434",
    temperature=0
)

# Embedding: Mevzuat metinlerini vektöre çevirmek için nomic-embed-text
embedding_fn = OllamaEmbeddingFunction(
    url="http://localhost:11434/api/embeddings",
    model_name="nomic-embed-text"
)

# ChromaDB: Vektörlerin saklandığı yerel veritabanı bağlantısı
chroma_client = chromadb.PersistentClient(path="./chroma_veri")
try:
    koleksiyon = chroma_client.get_collection(
        name="mevzuat",
        embedding_function=embedding_fn
    )
except Exception as e:
    raise RuntimeError(
        "ChromaDB 'mevzuat' koleksiyonu bulunamadı. "
        "Önce `python chroma_yukle.py` çalıştırın."
    ) from e

SISTEM_PROMPTU = """Sen bir Türk kamu evrakı analiz uzmanısın.
Sana verilen resmi evrak metninden yapısal bilgileri çıkar ve SADECE JSON döndür.
Başka hiçbir açıklama ekleme."""

# === VALİDASYON YARDIMCILARI ===
TARIH_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# Resmi belge sayısı: "E-12345678-123.45-6789" gibi kalıplar
BELGE_SAYISI_REGEX = re.compile(r"^[A-Z]?-?\d[\d\-\./]{3,}$")
TC_REGEX = re.compile(r"^\d{11}$")

def _tarihi_normalize_et(deger):
    """LLM string döndürmüş olabilir; ISO 8601 (YYYY-MM-DD) değilse null."""
    if not deger or not isinstance(deger, str):
        return None
    deger = deger.strip()
    if TARIH_REGEX.match(deger):
        return deger
    # DD.MM.YYYY → YYYY-MM-DD dönüşümü
    m = re.match(r"^(\d{2})[\.\/](\d{2})[\.\/](\d{4})$", deger)
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    return None

def _belge_sayisini_normalize_et(deger):
    """Sayfa sayısı gibi düz integer'ları eleme; sadece resmi belge no formatı geçer."""
    if deger is None:
        return None
    if isinstance(deger, int):
        # Salt integer büyük ihtimalle sayfa sayısı — belge no değil
        return None
    if isinstance(deger, str) and BELGE_SAYISI_REGEX.match(deger.strip()):
        return deger.strip()
    return None

def _tc_kimligi_normalize_et(deger):
    if not deger or not isinstance(deger, str):
        return None
    d = deger.strip()
    return d if TC_REGEX.match(d) else None

def cikartilan_bilgileri_temizle(cikartilan: dict) -> dict:
    """LLM çıktısındaki bozuk formatları null'a çevir."""
    cikartilan["tarih"] = _tarihi_normalize_et(cikartilan.get("tarih"))
    cikartilan["belge_sayisi"] = _belge_sayisini_normalize_et(cikartilan.get("belge_sayisi"))
    cikartilan["tc_kimlik"] = _tc_kimligi_normalize_et(cikartilan.get("tc_kimlik"))

    # Boş stringleri ve placeholder değerleri null'a çevir
    for k, v in list(cikartilan.items()):
        if isinstance(v, str):
            if not v.strip() or v.strip().lower() in BOS_DEGERLER:
                cikartilan[k] = None

    # gonderici == gonderici_kurum bug'ını düzelt
    if (cikartilan.get("gonderici") and cikartilan.get("gonderici_kurum")
            and cikartilan["gonderici"] == cikartilan["gonderici_kurum"]):
        # Kurumsal ipuçları varsa gonderici_kurum kalır, gonderici null olur
        kurumsal_kelimeler = ["Başkanlığı", "Müdürlüğü", "Daire", "Kurumu",
                              "Koordinatörlüğü", "Genel Müdürlük"]
        if any(k in cikartilan["gonderici"] for k in kurumsal_kelimeler):
            cikartilan["gonderici"] = None
        else:
            cikartilan["gonderici_kurum"] = None

    # Unvan filtresi: gonderici ve imza_sahibi sadece unvandan oluşamaz
    for alan in ["gonderici", "imza_sahibi"]:
        v = cikartilan.get(alan)
        if v and not _isim_gecerli_mi(v):
            cikartilan[alan] = None

    return cikartilan


def halusinasyon_filtrele(cikartilan: dict, metin: str) -> dict:
    """
    LLM'in çıkardığı isim/kurum değerlerini metinde ara. Metinde
    hiçbir kelimesi geçmeyen değerleri null'a çevir (halüsinasyon savunması).
    Regex/format validasyonu geçen alanlara (tarih, tc_kimlik, belge_sayisi)
    dokunmuyoruz.
    """
    if not metin:
        return cikartilan

    metin_lower = metin.lower()

    for alan in ["gonderici", "gonderici_kurum", "alici_kurum",
                 "imza_sahibi", "konu"]:
        v = cikartilan.get(alan)
        if not v or not isinstance(v, str):
            continue

        v_lower = v.lower().strip()
        # Doğrudan geçiyorsa OK
        if v_lower in metin_lower:
            continue

        # Kelime bazlı: en az yarısı metinde varsa OK
        kelimeler = [k for k in v_lower.split() if len(k) > 2]
        if kelimeler:
            eslesen = sum(1 for k in kelimeler if k in metin_lower)
            if eslesen >= max(1, len(kelimeler) // 2 + len(kelimeler) % 2):
                continue

        # Metinde bulunamadı → halüsinasyon şüphesi → null
        cikartilan[alan] = None

    return cikartilan

# Veri sözleşmesindeki taksonomi tablosu — evrak türüne göre zorunlu alanlar
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
    "DIGER": []
}

# === ÖN KONTROL: AGENT 1 GİRDİSİ ===
# Veri sözleşmesi §5: durum=BASARISIZ ise NLP çalıştırma, manuel kuyruğa yönlendir
def agent1_girdisini_isle(agent1_json: dict):
    """
    Agent 1'den gelen JSON'ı parse eder.
    BASARISIZ durumda (None, None, None) döndürür — pipeline bu durumda manuel kuyruğa yönlendirir.
    Döndürür: (metin, evrak_turu, on_cikarimlar)
    """
    durum = agent1_json["agent1_islem_metadata"]["durum"]

    if durum == "BASARISIZ":
        return None, None, None

    metin = agent1_json["metin_icerigi"].get("temizlenmis_metin")
    evrak_turu = agent1_json["siniflandirma_sonucu"]["evrak_turu"]
    on_cikarimlar = agent1_json.get("on_cikarimlar") or {}

    return metin, evrak_turu, on_cikarimlar

BOS_CIKARIM = {
    "gonderici": None, "gonderici_kurum": None, "alici_kurum": None,
    "konu": None, "tarih": None, "belge_sayisi": None,
    "tc_kimlik": None, "imza_sahibi": None, "ekler": None,
}

# LLM'in null'a çevirmesi gereken placeholder değerler
BOS_DEGERLER = {"none", "null", "yok", "belirsiz", "belirli değil",
                 "belirtilmemis", "belirtilmemiş", "boş", "-", ""}

# Bu ifadeler İSİM değil UNVAN'dır — imza_sahibi/gonderici alanına yazılamaz
UNVANLAR = {
    "şube müdürü", "daire başkanı", "genel müdür", "genel müdür yardımcısı",
    "müdür", "başkan", "başkan yardımcısı", "başkan vekili", "vali",
    "kaymakam", "belediye başkanı", "koordinatör", "uzman", "memur",
    "yönetici", "sorumlu", "başhekim", "hekim", "doktor",
    "genel sekreter", "sekreter", "danışman", "denetçi",
    "il müdürü", "ilçe müdürü", "bölge müdürü", "birim amiri",
    "daire başkan yardımcısı", "şef", "amir",
}


def _isim_gecerli_mi(deger: str) -> bool:
    """
    Bir değerin gerçek kişi ismi olup olmadığını kontrol eder.
    Sadece unvandan oluşan değerleri reddeder.
    """
    if not deger or not isinstance(deger, str):
        return False
    d = deger.strip().lower()
    if d in UNVANLAR:
        return False
    # Kelime sayısı 1 ve unvan ise reddet (örn "Müdür")
    if len(d.split()) == 1 and d in UNVANLAR:
        return False
    return True


# === REGEX PRE-EXTRACT ===
def regex_ile_cikar(metin: str) -> dict:
    """
    LLM'e vermeden önce metinden regex ile bariz alanları çıkarır.
    LLM'in halüsinasyon şansını azaltır.
    """
    bulgular = {}

    # Konu: satırı
    m = re.search(r"Konu\s*:\s*(.+?)(?:\n|$)", metin, re.IGNORECASE)
    if m:
        konu = m.group(1).strip().rstrip(".")
        # "None", "boş" gibi placeholder'ları reddet
        if konu and konu.lower() not in BOS_DEGERLER:
            bulgular["konu"] = konu

    # Sayı: E-... formatında belge numarası
    m = re.search(r"Sayı\s*:\s*(E?-?\d[\d\.\-\/]{3,})", metin, re.IGNORECASE)
    if m:
        bulgular["belge_sayisi"] = m.group(1).strip()

    # Tarih: DD.MM.YYYY veya YYYY-MM-DD
    for pat in [r"\b(\d{2})\.(\d{2})\.(\d{4})\b", r"\b(\d{4})-(\d{2})-(\d{2})\b"]:
        m = re.search(pat, metin)
        if m:
            g = m.groups()
            # İlk pattern DD.MM.YYYY, ikincisi zaten ISO
            if len(g[0]) == 2:
                bulgular["tarih"] = f"{g[2]}-{g[1]}-{g[0]}"
            else:
                bulgular["tarih"] = f"{g[0]}-{g[1]}-{g[2]}"
            break

    # TC Kimlik: 11 haneli sayı, "T.C. Kimlik No:" başlığından sonra ideal
    m = re.search(r"T\.?C\.?\s*Kimlik\s*No\.?\s*:?\s*(\d{11})", metin, re.IGNORECASE)
    if m:
        bulgular["tc_kimlik"] = m.group(1)

    # İmza sahibi: metnin sonunda genelde "İmza" kelimesinden ÖNCE gelen isim
    # Örnek: "Ahmet Yılmaz\nGenel Müdür\nİmza" veya "Ahmet Yılmaz\nİmza"
    imza_pat = re.search(
        r"([A-ZÇĞİÖŞÜ][a-zçğıöşü]+(?:\s+[A-ZÇĞİÖŞÜ][a-zçğıöşü\.]+){1,4})\s*(?:\n[^\n]*?)?\n?İmza",
        metin
    )
    if imza_pat:
        aday = imza_pat.group(1).strip()
        # Kurumsal başlıkları ve unvanları eleme
        if (not any(kelime in aday for kelime in ["Başkanlığı", "Müdürlüğü", "Daire", "Kurumu"])
                and _isim_gecerli_mi(aday)):
            bulgular["imza_sahibi"] = aday

    # Gonderici: "T.C. Kimlik No" satırından ÖNCE gelen isim (dilekçelerde)
    m = re.search(
        r"([A-ZÇĞİÖŞÜ][a-zçğıöşü]+(?:\s+[A-ZÇĞİÖŞÜ][a-zçğıöşü\.]+){1,4})\s*\n\s*T\.?C\.?\s*Kimlik",
        metin
    )
    if m:
        aday = m.group(1).strip()
        if (not any(kelime in aday for kelime in ["Başkanlığı", "Müdürlüğü", "Daire", "Kurumu"])
                and _isim_gecerli_mi(aday)):
            bulgular["gonderici"] = aday

    # "Ad Soyad: X" formatı
    m = re.search(r"Ad\s+Soyad\s*:\s*([^\n]+)", metin, re.IGNORECASE)
    if m:
        aday = m.group(1).strip()
        # Placeholder ve unvan kontrolü
        if (aday.lower() not in BOS_DEGERLER
                and not any(kelime in aday for kelime in ["Başkanlığı", "Müdürlüğü", "Daire"])
                and _isim_gecerli_mi(aday)):
            bulgular["gonderici"] = aday

    return bulgular

# === ADIM 1: BİLGİ ÇIKARIMI ===
def bilgi_cikar(metin: str, evrak_turu: str, on_cikarimlar: Optional[dict] = None) -> dict:
    """
    Bilgi çıkarma sırası:
      1. Agent 1'in on_cikarimlar'ı (en güvenilir, ground truth)
      2. Regex pre-extract (metinde bariz pattern varsa)
      3. LLM (kalan boş alanlar için, sıkı prompt)

    Bu üç aşamalı yaklaşım halüsinasyon riskini minimize eder.
    """
    on_cikarimlar = on_cikarimlar or {}

    # 1. Seed = Agent 1'in çıkardıkları
    seed = dict(BOS_CIKARIM)
    for k in BOS_CIKARIM.keys():
        if k in on_cikarimlar and on_cikarimlar[k] not in (None, "", []):
            seed[k] = on_cikarimlar[k]

    # 2. Regex ile Agent 1'in bulamadıklarını doldur
    regex_bulgulari = regex_ile_cikar(metin) if metin else {}
    for k, v in regex_bulgulari.items():
        if seed.get(k) is None:
            seed[k] = v

    dolu_alanlar = {k: v for k, v in seed.items() if v is not None}
    bos_alanlar = [k for k, v in seed.items() if v is None]

    if not bos_alanlar:
        return cikartilan_bilgileri_temizle(seed)

    # 3. Kalan boş alanlar için LLM (halüsinasyon karşıtı sıkı prompt)
    kullanici_promptu = f"""Evrak metni:
\"\"\"
{metin}
\"\"\"

Evrak türü: {evrak_turu}

Halihazırda tespit edilmiş alanlar (BUNLARA DOKUNMA, aynen kullan):
{json.dumps(dolu_alanlar, ensure_ascii=False, indent=2)}

Sadece şu boş alanları metinden çıkar: {bos_alanlar}

ALAN KURALLARI:
- gonderici: Gönderen kişinin ADI SOYADI (2-4 kelime). Bu bir KİŞİDİR, kurum değil. Kurumsal ifadeler ("Genel Müdürlük", "Koordinatörlüğü" vb.) yasak.
- gonderici_kurum: Sadece kurum adı. gonderici ile AYNI OLAMAZ.
- alici_kurum: Alıcı kurum adı. Metinde "None", "boş", "belirsiz" gibi placeholder varsa NULL.
- konu: 'Konu:' başlığından sonraki kısa satır (max 15 kelime). Placeholder ise null.
- tarih: YYYY-MM-DD. Metinde açık tarih yoksa null.
- belge_sayisi: 'Sayı:' başlığından sonraki resmi numara (örn "E-12345678-123.45-6789"). SAYFA SAYISI DEĞİL.
- tc_kimlik: 11 haneli. Metinde açıkça geçmiyorsa NULL. ASLA UYDURMA.
- imza_sahibi: Metnin SONUNDA, imza bölümünde geçen kişinin ADI SOYADI (2-4 kelime). "Şube Müdürü", "Daire Başkanı", "Genel Müdür" gibi UNVANLAR kişi ismi DEĞİLDİR → null döndür. Sadece unvan varsa (isim yoksa) null.
- ekler: Sadece açıkça "Ek:", "Ekler:" veya "EK-1" olarak listelenmiş belgeler.

MUTLAK KURALLAR:
1. Bir değeri metinde AÇIKÇA göremiyorsan → NULL yaz. Tahmin etme. Uydurma.
2. "None", "boş", "belirsiz", "belirtilmemiş", "-" → NULL olarak yorumla.
3. gonderici = gonderici_kurum OLAMAZ. Aynı değer iki alana yazılmaz.
4. Kurum ismini kişi ismi olarak (gonderici, imza_sahibi) yazma.
5. Sadece tek geçerli JSON döndür, açıklama ekleme."""

    try:
        yanit = llm.invoke([
            SystemMessage(content=SISTEM_PROMPTU),
            HumanMessage(content=kullanici_promptu)
        ])
        temiz = re.sub(r"^```[a-z]*\n?", "", yanit.content.strip())
        temiz = re.sub(r"\n?```$", "", temiz).strip()
        llm_sonuc = json.loads(temiz)
    except Exception as e:
        print(f"  [UYARI] bilgi_cikar hatası: {e}. Sadece seed kullanılıyor.")
        llm_sonuc = {}

    # LLM çıktısı seed'i override edemez — Agent 1'in çıkardığı ground truth kalır
    sonuc = dict(BOS_CIKARIM)
    for k in BOS_CIKARIM.keys():
        if seed[k] is not None:
            sonuc[k] = seed[k]  # Agent 1'in çıkardığı öncelikli
        elif k in llm_sonuc:
            sonuc[k] = llm_sonuc[k]

    # LLM'in doldurduğu alanları halüsinasyon açısından filtrele
    # (regex/format geçenlere dokunmuyoruz — sadece isim/kurum alanları)
    llm_alanlar = {k for k in bos_alanlar if seed.get(k) is None}
    llm_sonuc_temiz = {k: sonuc[k] for k in llm_alanlar if k in sonuc}
    # Seed'i koru, LLM alanlarını filtrele
    filtrelenmis = halusinasyon_filtrele(llm_sonuc_temiz.copy(), metin)
    for k, v in filtrelenmis.items():
        sonuc[k] = v

    return cikartilan_bilgileri_temizle(sonuc)

# === ADIM 2: MEVZUAT EŞLEŞTIRME ===
def mevzuat_ara(konu: str, evrak_turu: str, top_k: int = 3, distance_esik: float = 1.2) -> list:
    """
    ChromaDB'den mevzuat çeker.
    - evrak_turleri metadata'sı virgülle ayrılmış string → split ile listeye çevir
    - Distance eşiğinden büyükler elenir (semantik olarak uzak)
    - En fazla top_k sonuç döner
    """
    if not konu:
        return []

    try:
        sonuclar = koleksiyon.query(
            query_texts=[konu],
            n_results=len(mevzuat_listesi)
        )
    except Exception as e:
        print(f"  [UYARI] mevzuat_ara hatası: {e}")
        return []

    filtreli = []
    for i in range(len(sonuclar["ids"][0])):
        meta = sonuclar["metadatas"][0][i]
        mesafe = sonuclar["distances"][0][i] if sonuclar.get("distances") else 0

        # Bug fix: metadata string olarak saklanmış, split ile listeye çevir
        turler = [t.strip() for t in meta["evrak_turleri"].split(",")]

        if evrak_turu in turler and mesafe <= distance_esik:
            filtreli.append({
                "kanun": meta["kanun"],
                "madde": meta["madde"],
                "metin": sonuclar["documents"][0][i]
            })

        if len(filtreli) >= top_k:
            break

    return filtreli

# === ADIM 3: EKSİK BİLGİ TESPİTİ ===
def eksik_bilgi_tespit(cikartilan: dict, evrak_turu: str) -> list:
    zorunlular = ZORUNLU_ALANLAR.get(evrak_turu, [])
    eksikler = []
    for alan in zorunlular:
        if not cikartilan.get(alan):
            eksikler.append(alan)
    return eksikler

# === ADIM 4: ÖZETLEME ===
def ozetle(metin: str, cikartilan: dict, mevzuat: list, eksikler: list) -> str:
    mevzuat_str = ", ".join([f"{m['kanun']} {m['madde']}" for m in mevzuat])
    eksik_str = ", ".join(eksikler) if eksikler else "yok"

    prompt = f"""Aşağıdaki evrak analiz edilmiştir. Resmi yazı taslağı hazırlayacak ajana 2-3 cümleyle net bir özet yaz.
Sadece metinde geçen bilgileri kullan, kendinden ekleme yapma.
Sadece özeti yaz, başka açıklama ekleme.

Evrak metni: {metin}
Gönderen: {cikartilan.get('gonderici')}
Konu: {cikartilan.get('konu')}
İlgili mevzuat: {mevzuat_str}
Eksik alanlar: {eksik_str}"""

    try:
        yanit = llm.invoke([
            SystemMessage(content="Sen bir Türk kamu evrakı analiz uzmanısın."),
            HumanMessage(content=prompt)
        ])
        return yanit.content.strip()
    except Exception as e:
        print(f"  [UYARI] ozetle hatası: {e}")
        return f"Özet oluşturulamadı. Evrak türü: {cikartilan.get('konu') or 'bilinmiyor'}."

# === ÇIKTI OLUŞTURMA ===
def cikti_olustur(agent1_json: dict, evrak_turu: str, cikartilan: dict, mevzuat: list, eksikler: list, ozet: str) -> dict:
    meta = agent1_json["agent1_islem_metadata"]
    
    if meta.get("manuel_inceleme_onerisi"):
        durum = "MANUEL_INCELEME"
    elif eksikler:
        durum = "EKSIK_BILGI"
    else:
        durum = "TAMAMLANDI"
    
    return {
        "sema_versiyonu": "1.0",
        "agent2_islem_metadata": {
            "evrak_id": meta["evrak_id"],
            "islem_zamani": datetime.now().isoformat(),
            "durum": durum,
            "manuel_inceleme_onerisi": meta.get("manuel_inceleme_onerisi", False),
            "agent1_durum": meta["durum"],
            "agent1_siniflandirma_skoru": agent1_json["siniflandirma_sonucu"]["siniflandirma_guven_skoru"]
        },
        "evrak_turu": evrak_turu,
        "cikartilan_bilgiler": cikartilan,
        "ilgili_mevzuat": mevzuat,
        "eksik_alanlar": eksikler,
        "ozet": ozet
    }

if __name__ == "__main__":
    with open("../ornek.json", encoding="utf-8") as f:
        ornekler = json.load(f)

    ciktilar = []

    # Agent 1 ürettiği örnek JSON'lar üzerinde uçtan uca test
    for evrak in ornekler:
        print(f"\n=== {evrak['agent1_islem_metadata']['evrak_id']} ===")
        metin, evrak_turu, on_cikarimlar = agent1_girdisini_isle(evrak)

        # BASARISIZ evrak — bu karar Agent 4'ün orkestrasyon katmanına sinyal verir
        if metin is None:
            print("BASARISIZ — manuel kuyruğa yönlendirildi.")
            continue

        sonuc = bilgi_cikar(metin, evrak_turu, on_cikarimlar)
        print(json.dumps(sonuc, ensure_ascii=False, indent=2))

        mevzuat = mevzuat_ara(sonuc.get("konu") or metin[:50], evrak_turu)
        print(json.dumps(mevzuat, ensure_ascii=False, indent=2))

        eksikler = eksik_bilgi_tespit(sonuc, evrak_turu)
        print("Eksik alanlar:", eksikler)

        ozet = ozetle(metin, sonuc, mevzuat, eksikler)
        print("Özet:", ozet)
        cikti = cikti_olustur(evrak, evrak_turu, sonuc, mevzuat, eksikler, ozet)
        print(json.dumps(cikti, ensure_ascii=False, indent=2))
        
        ciktilar.append(cikti)

    with open("../agent2_cikti.json", "w", encoding="utf-8") as f:
        json.dump(ciktilar, f, ensure_ascii=False, indent=2)
    print("\nagent2_cikti.json kaydedildi.")