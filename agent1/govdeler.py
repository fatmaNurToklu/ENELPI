# -*- coding: utf-8 -*-
"""
11 evrak türü için Jinja2 metin gövdesi şablonları.
Her şablon, agent1_agent2_veri_sozlesmesi.md'deki taksonomi tablosundaki
evrak_turu değerleriyle birebir eşleşir.
"""

GOVDE_SABLONLARI = {

"DILEKCE": """{{ alici_kurum }} BAŞKANLIĞINA

Konu: {{ konu }}

{{ govde_metni }}

Gereğini saygılarımla arz ederim.

{% if tarih %}{{ tarih }}{% endif %}

{{ gonderici }}
{% if tc_kimlik %}T.C. Kimlik No: {{ tc_kimlik }}{% endif %}
İmza""",

"BILGI_EDINME_BASVURUSU": """T.C. {{ alici_kurum }} BAŞKANLIĞINA

Konu: Bilgi Edinme Talebi - {{ konu }}

4982 sayılı Bilgi Edinme Hakkı Kanunu kapsamında, {{ govde_metni }}

Bilgi Edinme Hakkı Kanunu'nun ilgili maddeleri uyarınca tarafıma bilgi verilmesini saygılarımla arz ederim.

{% if tarih %}{{ tarih }}{% endif %}

Ad Soyad: {{ gonderici }}
{% if tc_kimlik %}T.C. Kimlik No: {{ tc_kimlik }}{% endif %}
İmza""",

"SIKAYET_BASVURUSU": """{{ alici_kurum }} BAŞKANLIĞINA

Konu: Şikayet Başvurusu - {{ konu }}

{{ govde_metni }}

Konunun incelenerek tarafıma bilgi verilmesini ve gerekli işlemlerin yapılmasını saygılarımla arz ederim.

{% if tarih %}{{ tarih }}{% endif %}

{{ gonderici }}
{% if tc_kimlik %}T.C. Kimlik No: {{ tc_kimlik }}{% endif %}
İmza""",

"RESMI_UST_YAZI": """T.C.
{{ gonderici_kurum }}
{{ gonderici_birim }}

Sayı: {{ belge_sayisi }}
Konu: {{ konu }}

{{ alici_kurum }}

{{ govde_metni }}

Bilgilerinizi ve gereğini arz/rica ederim.

{% if tarih %}{{ tarih }}{% endif %}

{{ imza_sahibi }}
{{ imza_unvani }}""",

"CEVAP_YAZISI": """T.C.
{{ gonderici_kurum }}
{{ gonderici_birim }}

Sayı: {{ belge_sayisi }}
Konu: {{ konu }} Hk.

İlgi: {{ ilgi_yazi }}

{{ govde_metni }}

Bilgilerinize arz ederim.

{% if tarih %}{{ tarih }}{% endif %}

{{ imza_sahibi }}
{{ imza_unvani }}""",

"BILGILENDIRME_YAZISI": """T.C.
{{ gonderici_kurum }}
{{ gonderici_birim }}

Konu: {{ konu }}

{{ alici_kurum }}

{{ govde_metni }}

Bilgilerinize sunulur.

{% if tarih %}{{ tarih }}{% endif %}

{{ imza_sahibi }}
{{ imza_unvani }}""",

"TALIMAT_YAZISI": """T.C.
{{ gonderici_kurum }}
{{ gonderici_birim }}

Sayı: {{ belge_sayisi }}
Konu: {{ konu }}

{{ alici_kurum }}

{{ govde_metni }}

Belirtilen hususların ivedilikle yerine getirilmesi hususunda gereğini rica ederim.

{% if tarih %}{{ tarih }}{% endif %}

{{ imza_sahibi }}
{{ imza_unvani }}""",

"FATURA": """{{ gonderici_kurum }}

FATURA

Fatura No: {{ belge_sayisi }}
{% if tarih %}Tarih: {{ tarih }}{% endif %}

{{ govde_metni }}

Genel Toplam: {{ tutar }} TL (KDV Dahil)""",

"SOZLESME_PROTOKOL": """{{ konu }}

Taraf 1: {{ gonderici_kurum }}
Taraf 2: {{ alici_kurum }}

{{ govde_metni }}

İşbu protokol iki nüsha olarak {% if tarih %}{{ tarih }}{% endif %} tarihinde imzalanmıştır.

Taraf 1 Yetkilisi                Taraf 2 Yetkilisi
{{ imza_sahibi }}""",

"TUTANAK_RAPOR": """TUTANAK

{% if tarih %}Tarih: {{ tarih }}{% endif %}
Konu: {{ konu }}

{{ govde_metni }}

İşbu tutanak taraflarca okunarak imza altına alınmıştır.""",

"DIGER": """{{ gonderici_kurum }}

{{ govde_metni }}

{% if tarih %}{{ tarih }}{% endif %}""",
}
