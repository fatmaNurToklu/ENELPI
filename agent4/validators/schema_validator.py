"""
Agent 4 — JSON Şema Doğrulayıcı
Sözleşme referansı: agent4_orkestrasyon_sozlesmesi.md §3
"""

import json
import jsonschema
from typing import Dict, Any, Tuple

# ─── Agent 4 Nihai Çıktı Şeması (v1.0) ──────────────────────────────────────
AGENT4_CIKTI_SEMASI = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Agent4_Nihai_Cikti_Semasi_v1",
    "type": "object",
    "required": [
        "sema_versiyonu", "evrak_id", "sistem_durumu",
        "sistem_aksiyonu", "uretilen_taslak", "nihai_yonlendirme", "kullanici_mesaji"
    ],
    "properties": {
        "sema_versiyonu": {"type": "string", "const": "1.0"},
        "evrak_id": {"type": "string", "pattern": "^EVR-[0-9]{4}-[0-9]{4,}$"},
        "sistem_durumu": {
            "type": "string",
            "enum": [
                "OTOMATIK_ONAYLANABILIR",
                "INSAN_ONAYI_BEKLIYOR",
                "EKSIK_BILGI_TALEBI",
                "KRITIK_HATA_MANUEL_KUYRUK",
            ],
        },
        "sistem_aksiyonu": {
            "type": "string",
            "enum": [
                "ARSIFLE_VE_GONDER",
                "UI_ONAY_EKRANINA_DUSUR",
                "UI_INPUT_FORMU_AC",
                "MANUEL_INCELEME_MASASINA_AT",
            ],
        },
        "uretilen_taslak": {
            "type": ["object", "null"],
            "properties": {
                "taslak_metni": {"type": "string"},
                "sablon_turu": {"type": "string"},
                "uslup_uygun_mu": {"type": "boolean"},
            },
        },
        "nihai_yonlendirme": {
            "type": ["object", "null"],
            "properties": {
                "hedef_birim": {
                    "type": "string",
                    "enum": [
                        "INSAN_KAYNAKLARI", "BILGI_ISLEM", "HUKUK_MUSAVIRLIGI",
                        "YAZI_ISLERI", "DESTEK_HIZMETLERI", "STRATEJI_GELISTIRME",
                        "MANUEL_BELIRSIZ",
                    ],
                },
                "gerekce": {"type": "string"},
                "yonlendirme_guven_skoru": {"type": "number", "minimum": 0, "maximum": 1},
            },
        },
        "kullanici_mesaji": {"type": "string"},
    },
}

# ─── Agent 3 Girdi Şeması (v1.0) — doğrulama için ───────────────────────────
AGENT3_CIKTI_SEMASI = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Agent3_Cikti_Semasi_v1",
    "type": "object",
    "required": ["sema_versiyonu", "evrak_id", "kaynak_baglam", "uretilen_taslak", "durum"],
    "properties": {
        "sema_versiyonu": {"type": "string", "const": "1.0"},
        "evrak_id": {"type": "string", "pattern": "^EVR-[0-9]{4}-[0-9]{4,}$"},
        "kaynak_baglam": {
            "type": "object",
            "required": ["evrak_turu", "agent2_durum", "eksik_alanlar", "mevzuat_sayisi"],
            "properties": {
                "evrak_turu": {"type": "string"},
                "agent2_durum": {"type": "string", "enum": ["TAMAMLANDI", "EKSIK_BILGI", "MANUEL_INCELEME"]},
                "eksik_alanlar": {"type": "array", "items": {"type": "string"}},
                "mevzuat_sayisi": {"type": "integer", "minimum": 0},
            },
        },
        "uretilen_taslak": {
            "type": "object",
            "required": ["sablon_turu", "taslak_metni", "eksik_alan_yer_tutucular", "resmi_uslup_kontrolu"],
        },
        "durum": {
            "type": "string",
            "enum": [
                "TASLAK_HAZIR",
                "TASLAK_HAZIR_EKSIK_BILGI",
                "TASLAK_HAZIR_MANUEL_INCELEME_UYARILI",
                "URETILEMEDI",
            ],
        },
    },
}


def validate_agent3_output(data: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Agent 3'ün çıktısını şemaya göre doğrular.
    Returns: (geçerli_mi, hata_mesajı)
    """
    try:
        jsonschema.validate(instance=data, schema=AGENT3_CIKTI_SEMASI)
        return True, ""
    except jsonschema.ValidationError as e:
        return False, f"Agent3 şema hatası: {e.message} (yol: {' → '.join(str(p) for p in e.path)})"
    except Exception as e:
        return False, f"Beklenmeyen doğrulama hatası: {str(e)}"


def validate_agent4_output(data: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Agent 4'ün nihai çıktısını şemaya göre doğrular.
    Returns: (geçerli_mi, hata_mesajı)
    """
    try:
        jsonschema.validate(instance=data, schema=AGENT4_CIKTI_SEMASI)
        return True, ""
    except jsonschema.ValidationError as e:
        return False, f"Agent4 şema hatası: {e.message} (yol: {' → '.join(str(p) for p in e.path)})"
    except Exception as e:
        return False, f"Beklenmeyen doğrulama hatası: {str(e)}"


def validate_json_string(json_str: str, schema: Dict) -> Tuple[bool, Dict, str]:
    """
    Ham JSON string'i parse edip şemaya göre doğrular.
    Returns: (geçerli_mi, parsed_data, hata_mesajı)
    """
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        return False, {}, f"JSON parse hatası: {str(e)}"

    try:
        jsonschema.validate(instance=data, schema=schema)
        return True, data, ""
    except jsonschema.ValidationError as e:
        return False, data, f"Şema hatası: {e.message}"
