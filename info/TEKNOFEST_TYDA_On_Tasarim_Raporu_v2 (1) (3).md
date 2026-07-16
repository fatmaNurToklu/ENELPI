Takım Adı: ENELPİ 

Takım ID: 1002407 



# İÇİNDEKİLER 

|İÇİNDEKİLER................................................................................................................................1|
|---|
|ŞEKİL LİSTESİ..............................................................................................................................1|
|TABLO LİSTESİ.............................................................................................................................2|



|KISALTMALAR.............................................................................................................................. 2|
|---|
|1. TAKIM YAPISI VE GÖREV DAĞILIMI...................................................................................3|
|2. PROJE ÖZETİ........................................................................................................................4|
|3. ALGORİTMALAR VE SİSTEM MİMARİSİ.............................................................................4|
|3.1. Veri Setleri.......................................................................................................................4|
|3.2. Algoritmalar.....................................................................................................................5|
|3.3. Akış Şeması....................................................................................................................7|
|4. ÖZGÜNLÜK...........................................................................................................................9|
|5. PROJE TAKVİMİ....................................................................................................................9|
|6. SONUÇLAR VE İNCELEME................................................................................................11|
|7. KAYNAKÇA..........................................................................................................................12|



# ŞEKİL LİSTESİ 

**Şekil 3.3:** Uçtan Uca Çok Ajanlı (Multi-Agent) Kamu Evrak Orkestrasyonu Akış Şeması 

# TABLO LİSTESİ 

**Tablo 1.1:** Takım Rolleri ve Görev Dağılım Matrisi 

**Tablo 3.1:** Evrak Türü Taksonomisi ve Zorunlu Alan Doğrulama Kuralları 

**Tablo 5.1:** Proje Geliştirme Kilometre Taşları ve Zaman Planı 

# KISALTMALAR 

|Kısaltma|Açıklama|
|---|---|
|LLM|Large Language Model (Büyük Dil Modeli)|
|OCR|Optical Character Recognition (Optik Karakter Tanıma)|
|RAG|Retrieval-Augmented Generation (Veri Geri Çağırımlı<br>Üretim)|
|TYDA|Türkçe Yapay Zeka Dil Ajanları|
|API|Application Programming Interface (Uygulama<br>Programlama Arayüzü)|
|JSON|JavaScript Object Notation (JavaScript Nesne Notasyonu)|
|NER|Named Entity Recognition (Varlık İsmi Tanıma)|
|SGD|Stochastic Gradient Descent (Stastik Gradyan İnişi)|
|TF-IDF|Term Frequency-Inverse Document Frequency (Terim<br>Frekansı-Ters Belge Frekansı)|
|CER|Character Error Rate (Karakter Hata Oranı)|
|WER|Word Error Rate (Sözcük Hata Oranı)|
|NLP|Natural Language Processing (Doğal Dil İşleme)|
|UI|User Interface (Kullanıcı Arayüzü)|
|KVKK|Kişisel Verilerin Korunması Kanunu|



# 1. TAKIM YAPISI VE GÖREV DAĞILIMI 

Sistemin geliştirme süreçleri, 4 kişilik takımımız arasında ajanların sorumluluklarına göre paylaştırılmıştır. Her takım üyesi, kendi ajanının geliştirilmesinden, test edilmesinden ve API sözleşmelerine uygun çıktı üretmesinden sorumludur. 

|**Ekip Üyesi**|**Takım Rolü**|**Sistem Bileşeni**<br>**Sorumluluğu**|**Geliştirme ve**<br>**Dokümantasyon**<br>**Alanı**|
|---|---|---|---|
|**Yusuf Kalkan**|Agent 1<br>Geliştiricisi / Veri<br>Mimarı|Evrak Okuma,<br>OCR ve<br>Sınıflandırma|Metin ön işleme<br>ve sınıflandırma,<br>sentetik veri<br>üretim<br>otomasyonu,<br>teknik rapor<br>yazımı.|
|**Fatma Nur Toklu**<br>**(Kaptan)**|Agent 2<br>Geliştiricisi / NLP<br>Uzmanı|İçerik Analizi ve<br>Mevzuat<br>Eşleştirme|Anlamsal varlık<br>çıkarımı (NER),<br>eksik bilgi analizi,<br>RAG mimarisinin<br>kurulması.|
|**Muhammed Can**<br>**Akbaş**|Agent 3<br>Geliştiricisi /<br>Yazılım Mimarı|Resmî Yazı<br>Taslaklama|Deterministik<br>şablon motoru,<br>slot-filling LLM<br>optimizasyonu,<br>üslup ve resmî<br>biçem kontrolü.|
|**Yasin Taha İnal**|Agent 4<br>Geliştiricisi /<br>Sistem<br>Entegratörü|Birim Yönlendirme<br>ve Orkestrasyon|LangGraph<br>kurulumu, human-<br>in-the-loop ve<br>kullanıcı arayüzü|



|**Ekip Üyesi**|**Takım Rolü**|**Sistem Bileşeni**<br>**Sorumluluğu**|**Geliştirme ve**<br>**Dokümantasyon**<br>**Alanı**|
|---|---|---|---|
||||tasarımı.|



Tablo 1.1: Takım Rolleri ve Görev Dağılım Matrisi 

# 2. PROJE ÖZETİ 

Yarışma hazırlık sürecinin ilk aşamasında, kamu kurumlarındaki resmî yazışma pratikleri ve yasal mevzuatlar ("Resmî Yazışmalarda Uygulanacak Usul ve Esaslar Hakkında Yönetmelik") derinlemesine incelenmiştir. Şu ana kadar gerçekleştirilen ön çalışmalar kapsamında projenin en kritik bileşeni olan "Ajanlar Arası İletişim Protokolleri ve Veri Sözleşmeleri (API Contracts v1.0)" tamamen tamamlanmış ve dondurulmuştur. Bağımsız ajanların birbirini engellemeden paralel olarak kodlanabilmesi amacıyla Agent 1→2, Agent 2→3 ve Agent 3→4 arasındaki JSON şemaları tasarlanmış ve takıma dağıtılmıştır. 

Teknik bileşenler düzeyinde; Agent 1 için OpenCV tabanlı eğiklik düzeltme (deskew) ve gürültü giderme algoritmalarının prototipleri test edilmiştir. Agent 2 için kullanılacak mevzuat metinlerinin vektörleştirilmesi amacıyla ChromaDB entegrasyon şeması çıkarılmıştır. Agent 3 tarafında slot-filling yaklaşımı için gerekli deterministik HTML/Jinja2 şablon iskeletleri oluşturulmuş, Agent 4 için ise LangGraph üzerindeki durum yapısı Python dilinde tanımlanmıştır. Sistem şu an mimari tasarım evresini tamamlamış ve sentetik veri üretimi ile model entegrasyonu aşamasına geçiş yapmıştır. 

# 3. ALGORİTMALAR VE SİSTEM MİMARİSİ 

## 3.1. Veri Setleri 

Şartnamede yer alan "Yarışmada gerçek kamu verisi kullanılmayacaktır" (Madde 6.5) kuralına tam uyum sağlamak amacıyla projenin test ve eğitim süreçlerinde tamamen yapay veriler kullanılacaktır. Bu stratejinin seçilme sebebi, kamu verilerinin gizlilik içermesi ve KVKK kısıtlamaları nedeniyle erişilebilir olmamasıdır. Ayrıca sentetik veri üretimi, uç durum senaryolarının sisteme yapay olarak beslenmesine olanak tanımaktadır. 

Veri seti üretim hattında, Python Faker ve Jinja2 kütüphaneleri kullanılarak resmî standartlara uygun boş belge şablonları doldurulacaktır. Metin gövdeleri ise büyük dil modelleri aracılığıyla kurgusal olaylar ve şahıslar üzerinden çeşitlendirilecektir. Eğitilen modeller üzerinde veri çeşitliliğinin etkisini ölçmek adına, veri setinde 11 farklı resmi evrak türü (Dilekçe, Resmî Üst Yazı, Fatura, Tutanak vb.) dengeli bir dağılımla temsil edilecektir. Üretilen belgeler taranmış görüntü (görsel noise eklenmiş PDF/JPEG) ve dijital metin katmanı olmak üzere iki farklı modda sisteme beslenerek OCR motorunun doğruluğu ve esnekliği test edilecektir. 

|**Evrak Türü**|**Zorunlu Alanlar**|
|---|---|
|**DİLEKÇE**|Gönderici, TC Kimlik, Konu, Tarih|
|**BİLGİ EDİNME BAŞVURUSU**|Gönderici, TC Kimlik, Alıcı Kurum, Konu|
|**ŞİKAYET BAŞVURUSU**|Gönderici, TC Kimlik, Konu|
|**RESMÎ ÜST YAZI**|Gönderici, Alıcı Kurum, Belge Sayısı,<br>Konu, Tarih, İmza Sahibi|
|**CEVAP YAZISI**|Gönderici, Alıcı Kurum, Belge Sayısı,<br>Konu, Tarih|
|**BİLGİLENDİRME YAZISI**|Gönderici, Alıcı Kurum, Konu, Tarih|
|**TALİMAT YAZISI**|Gönderici, Alıcı Kurum, Konu, Tarih, İmza<br>Sahibi|
|**FATURA**|Gönderici, Tarih, Belge Sayısı|
|**SÖZLEŞME/PROTOKOL**|Gönderici, Alıcı Kurum, Tarih, Konu|
|**TUTANAK/RAPOR**|Tarih, Konu|





<!-- Start of picture text -->
DİĞER<br><!-- End of picture text -->

Sabit liste yok — Agent 2 genel amaçlı kontrol uygular 

Tablo 3.1: Evrak Türü Taksonomisi ve Zorunlu Alan Doğrulama Kuralları 

## 3.2. Algoritmalar 

Sistem, tek bir LLM modeline devasa promptlar yüklemek yerine, görevleri mikroservis benzeri yapılara bölen hibrit algoritmalardan oluşmaktadır. Modüller düzeyinde tercih edilen algoritmalar ve gerekçeleri şunlardır: 

- **OCR ve Görüntü İşleme (Agent 1):** Taranmış görüntülerden metin çıkarımı için Tesseract 5.3 motoru seçilmiştir. OCR öncesinde belgenin okunabilirliğini artırmak amacıyla OpenCV kitaplığı ile adaptif eşikleme (adaptive thresholding) ve gürültü azaltma algoritmaları uygulanacaktır. 

- **Metin Sınıflandırma (Agent 1):** OCR'dan çıkan temiz metnin türünü belirlemek amacıyla TF-IDF vektörleştirme ve Stokastik Gradyan İnişi (SGD) tabanlı doğrusal sınıflandırıcıdan oluşan hızlı bir makine öğrenmesi hattı kurulacaktır. Bu algoritmanın seçilme nedeni, LLM'lere kıyasla çok daha düşük hesaplama maliyetiyle yüksek doğruluk sunmasıdır. 

- **Anlamsal Analiz ve RAG (Agent 2):** Sistemin bilgi çıkarımı ve mevzuat eşleştirme katmanını oluşturmaktadır. Agent 1'den JSON v1.0 sözleşmesi aracılığıyla gelen sınıflandırılmış metin üzerinde sırasıyla varlık çıkarımı (NER), mevzuat eşleştirme (RAG) ve özet üretimi gerçekleştirilmektedir. Varlık çıkarımında; gönderici, alıcı kurum, TC kimlik numarası, tarih ve belge sayısı gibi zorunlu alanlar Gemma 2 (9B/27B) modeli aracılığıyla metinden çıkarılmaktadır. Gemma 2, GQA mekanizması ve bilgi damıtma tekniğiyle eğitilmiş açık kaynaklı bir büyük dil modelidir [3]. Yapılandırılmış JSON çıktısıyla ayrıştırma hataları minimize edilmekte [9]; Türkçe kamu belgelerinde NER uygulaması ise morfolojik karmaşıklık nedeniyle literatürde özel bir zorluk alanı olarak ele alınmaktadır [11]. 

   - Mevzuat eşleştirme aşamasında, ilgili yasal referanslar ChromaDB vektör veritabanında kosinüs benzerliği algoritmasıyla sorgulanmaktadır. RAG mimarisi, modelin parametre dışı bilgiye dinamik erişimini sağlayarak halüsinasyon riskini önemli ölçüde azaltmaktadır [12][13]. Agent 2 çıktısı; eksik alanlar tespit edildiğinde EKSIK_BILGI, Agent 1 güven skoru 0.70'in altında kaldığında ise 

MANUEL_INCELEME durumu atanarak LangGraph interrupt mekanizmasıyla insan denetimine yönlendirilmektedir [2]. 

- **Şablon ve Slot-Filling (Agent 3):** Resmi yazı taslağının üretiminde tamamen LLM'e güvenmek yerine, hitap ve kapanış gibi alanların deterministik şablonlarla basıldığı, sadece gövde metninin Gemma 2 tarafından doldurulduğu "Slot-Filling" algoritması kurgulanmıştır. Bu şablon-tabanlı, bölüm bölüm üretim yaklaşımı, kamu yönetimi alanında yarı-yapılandırılmış belge üretimi için literatürde önerilen semantik şablon tabanlı çoklu-ajan mimarileriyle örtüşmektedir [10]. LLM seçiminde Qwen2-7B ile Gemma 2 (9B) arasında karşılaştırma yapılmış; yapılandırılmış çıktı güvenilirliğini ölçen bağımsız bir kıyaslamada Gemma-9B'nin, Qwen-7B'ye kıyasla belirgin şekilde daha az biçim bozulması (format collapse) gösterdiği ve ham çıktı güvenilirliği (ROS) ile biçim tutarlılığı açısından daha stabil sonuçlar ürettiği bulgusuna dayanılarak Gemma 2 (9B) tercih edilmiştir [9]. Resmi üslup kontrolü ise Regex kalıpları ve yasaklı/izinli kelime listelerinden oluşan kural tabanlı bir denetim motoruyla gerçekleştirilecektir. Agent 3'ün Agent 4'e devrettiği çıktı, "TASLAK_HAZIR", "TASLAK_HAZIR_EKSIK_BILGI", 

   - "TASLAK_HAZIR_MANUEL_INCELEME_UYARILI" ve "URETILEMEDI" durumlarından oluşan bir durum sözleşmesi (Agent 3→4 API Contract v1.0) ile tanımlanmıştır; bu sayede hitap, kapanış ve eksik-bilgi yer tutucuları gibi format unsurlarının modelin serbest üretimine değil deterministik şablona bağlı kalması, Agent 4 tarafında da garanti altına alınmış olur. 

- **Durum Yönetimi ve Yönlendirme (Agent 4):** Ajanların orkestrasyonu LangGraph durum makinesi altyapısıyla yönetilecektir. Kurum içi birim yönlendirme kararı ise, Agent 2'den gelen özet ve mevzuat bağlamı kullanılarak Few-Shot Prompting yöntemiyle çalışan yapılandırılmış bir LLM kararına bağlanmıştır. Bu tasarım tercihi, LLM tabanlı otonom ajanların karmaşık ve çok adımlı görevlerde planlama (planning) ve aksiyon (action) adımlarından oluşan döngüsel yapılara ihtiyaç duyduğunu ortaya koyan güncel literatürle örtüşmektedir [5]. Yönlendirme kararının isabetini artırmak için seçilen Few-Shot Prompting yaklaşımı, modellerin sınıflandırma görevlerinde prompt içinde verilen örneklerle en yüksek doğruluğa ulaştığını gösteren çalışmalara dayanmaktadır [6]. Ayrıca modelin parantez unutması veya düz metin üretmesi gibi ayrıştırma (parser) hatalarını tamamen elemek amacıyla, yönlendirme kararına ait model çağrıları yapılandırılmış JSON çıktı modunda gerçekleştirilecek ve bu sayede sistemin ticari kararlılığı artırılacaktır [8]. 

## 3.3. Akış Şeması 

Sistemin uçtan uca çalışma akışı, LangGraph üzerindeki düğümler (nodes) ve koşullu kenarlar (conditional edges) aracılığıyla şu şekilde yürütülmektedir: Evrak Girişi → Agent 

1 (OCR & Sınıflandırma) → JSON v1.0 Sözleşmesi → Agent 2 (Bilgi Çıkarımı & RAG) → JSON v1.0 Sözleşmesi → Agent 3 (Şablon Taslaklama & Üslup Kontrolü) → Agent 4 (Durum Orkestrasyonu). Eğer Agent 1 veya 3'ten gelen güven skoru eşik değerin (<0.70) altındaysa akış "İnsan Onay Kuyruğu" düğümüne yönlendirilir. Agent 2'de zorunlu alanlarda eksiklik bulunursa LangGraph "Interrupt" tetiklenerek grafik dondurulur, kullanıcı arayüzünden bilgi girişi alındıktan sonra süreç Agent 2 düğümüne geri beslenir (loopback). Bu insan katılımlı (human-in-the-loop) kesinti mekanizması, LLM tabanlı ajanların halüsinasyon veya eksik veriyle karşılaşma riskine karşı sistem güvenilirliğini maksimize eden bir yaklaşım olarak literatürde desteklenmektedir [7]. 



<!-- Start of picture text -->
Sekil 3.1 — Sistem Akig Semasi<br>EVRAK GiRDisi<br>Taranmis Goriintii | PDF | Dijital Metin<br>Agent 1 — Evrak Okuma & Siniflandirma (Yusuf)<br>OCR / Metin Okuma Evrak Siniflandirma Veri Seti + Rapor<br>Tesseract 5.3 | TF-IDF + SGD > Kurgu evraklar<br>OpenCV on isleme 11 evrak trl Dokiimantasyon<br>Hayir Giiven Skoru<br>‘eee’ 20.70?<br>iinsan Onay -<br>'<br>‘Fe apesKuyruguES aS NR HU]' fonea RNbasin ee TR Se<br>» JSON v1.0 Sézlesmesi (Agent 1 — Agent 2) '<br>Agent 2 — Icerik Analizi & Mevzuat Eslestirme (Nur)<br>Bilgi Cikarimi Eksik Bilgi Mevzuat RAG Ozetle<br>2 ae Gemma2:9b Taksonomi ChromaDB Gemma2<br>4 NER/Alanlar Zorunlu alanlar nomic-embed-text :9b<br>i '<br>I,<br>8 tl » JSON v1.0 Sézlesmesi (Agent 2 — Agent 3) \<br>Agent 3 — Resmi Yaz: Taslaklama (Can)<br>Taslak Uretimi Uslup Kontrolii Sunum Hazirligi<br>| Slot-Filling i 4 Regex kaliplari imal PPTX / PDF<br>Gemmaz2 + Sablon | Kural Motoru Final raporu<br>Agent 4 — Birim Yonlendirme & Orkestrasyon (Yasin)<br>Birim Yénlendirme LangGraph Orkestrasyon Kullanici Arayiizii<br>Few-Shot LLM Durum makinesi Bilgilendirme<br>Kurum eslestirme Pipeline yénetimi Eksik bilgi talebi<br>CIKTI<br>Yénlendirilmig Resmi Yazi + Kullanici Bildirimi<br><!-- End of picture text -->

# 4. ÖZGÜNLÜK 

Projemizin literatüre ve mevcut uygulamalara getirdiği en büyük özgünlük, büyük dil modellerini serbest metin üreten kontrolsüz yapılar olarak değil, "Katı Veri Sözleşmeleri" ve "Durum Makineleri" ile sınırlandırılmış deterministik bileşenler olarak konumlandırmasıdır. Sektördeki birçok uygulama tek bir devasa prompt ile uçtan uca sonuç üretmeye çalışırken, bu durum halüsinasyon riskini ve izlenebilirliği imkansız kılmaktadır. Geliştirdiğimiz mikroservis tabanlı ajan mimarisinde, her ajanın sorumluluk sınırı keskindir ve her aşamanın çıktısı JSON şemalarıyla doğrulanabilir (explainable AI). 

Ayrıca, Agent 3 bünyesinde tasarladığımız kural tabanlı iskelet ile LLM üretimli gövde metninin birleştirildiği "Hibrit Slot-Filling" yaklaşımı, resmi yazışma kurallarının görsel bütünlüğünü yüksek oranda korumayı hedeflemektedir; bu tasarım, kamu yönetimi belge üretiminde şablon-güdümlü çoklu-ajan mimarilerinin halüsinasyonu azalttığını gösteren güncel çalışmalarla da örtüşmektedir [10]. Son olarak, LangGraph'in interrupt yetenekleriyle kurgulanan "Eksik Bilgi Geri Besleme Döngüsü", statik bir boru hattını dinamik ve insanla etkileşimli bir sisteme dönüştürerek operasyonel esneklik açısından literatüre katkı sunmaktadır. 

# 5. PROJE TAKVİMİ 

Projenin belirlenen süre içerisinde olgunluğa ulaşması amacıyla, 12 Temmuz Ön Değerlendirme aşamasından başlayarak TEKNOFEST final sürecine kadar uzanan kilometre taşları Tablo 5.1'de planlanmıştır. 

|**Kilometre Taşı**|**Tarih Aralığı**|**Sorumlu**|**Hedeflenen Çıktılar**|
|---|---|---|---|
|**M01: Mimari**<br>**Tasarım &**<br>**Sözleşmeler**|12.06.2026 -<br>12.07.2026|Tüm Ekip|JSON şemaları<br>onayı, ön tasarım<br>raporu teslimi.|
|**M02: Sentetik Veri**<br>**& OCR (Agent 1)**|13.07.2026 -<br>26.07.2026|Yusuf Kalkan|Kurgusal evrak<br>üretimi, Tesseract<br>ve OpenCV boru<br>hattı testleri.|



|**Kilometre Taşı**|**Tarih Aralığı**|**Sorumlu**|**Hedeflenen Çıktılar**|
|---|---|---|---|
|**M03: RAG & NLP**<br>**Analizi (Agent 2)**|27.07.2026 -<br>10.08.2026|Fatma Nur Toklu<br>(Kaptan)|ChromaDB<br>kurulumu, mevzuat<br>eşleştirme, NER<br>optimizasyonu.|
|**M04: Taslaklama**<br>**Motoru (Agent 3)**|11.08.2026 -<br>20.08.2026|Muhammed Can<br>Akbaş|Jinja2 şablonlarının<br>kodlanması, resmi<br>üslup denetleyicisi,<br>slot-filling.|
|**M05: Orkestrasyon**<br>**& UI (Agent 4)**|21.08.2026 -<br>31.08.2026|Yasin Taha İnal|LangGraph<br>entegrasyonu,<br>arayüz testleri, eksik<br>bilgi kesinti<br>mekanizması.|
|**M06: Demo & Final**<br>**Sunumu**|01.09.2026 - Final|Tüm Ekip|Gerçek zamanlı<br>stabilite testleri,<br>GitHub repo<br>aktarımı, sunum.|



Tablo 5.1: Proje Geliştirme Kilometre Taşları ve Zaman Planı 

# 6. SONUÇLAR VE İNCELEME 

Proje şu an ön tasarım aşamasında olduğundan, elde edilen ilk deneysel sonuçlar Agent 1'in veri üretim hattı ve OCR prototipi üzerinedir. Geliştirilen sentetik veri üretim scripti aracılığıyla 165 adet kurgusal resmi evrak (Dilekçe ve Üst Yazı varyasyonları) yapay olarak üretilmiştir. Bu belgeler üzerine OpenCV ile adaptif eşikleme uygulanmış ve Tesseract 5.3 motoruyla metin okuma testleri gerçekleştirilmiştir. Yapılan ilk testler sonucunda Karakter Hata Oranı (Character Error Rate - CER) %4.7, Sözcük Hata Oranı (Word Error Rate - WER) ise %11.2 olarak ölçülmüştür. Bu sonuçlar, temizlenmiş metin 

katmanının Agent 2'deki anlamsal NER modellerini besleyebilecek olgunlukta olduğunu göstermektedir. 

Sınıflandırma modülünde TF-IDF + SGD Classifier kombinasyonu ile yapılan ilk kurgusal çapraz doğrulama (cross-validation) testlerinde, 11 evrak türü arasında %92'lik bir F1Skoru elde edilmiştir. Geliştirme sürecinde yaşanan en büyük sorun, taranmış görüntülerdeki katlanma veya tarayıcı gürültülerinin OCR güven skorunu aniden düşürmesidir. Bu sorunun üstesinden gelebilmek adına OpenCV'nin Gauss Bulanıklığı (Gaussian Blur) ve morfolojik açma (morphological opening) filtreleri boru hattına eklenerek CER oranı aşağı çekilmiştir. Edinilen en büyük tecrübe, veri sözleşmelerindeki tiplerin katı tutulmasının, ajanlar entegre edilirken oluşabilecek veri tipi uyuşmazlıklarını (Type Error) sıfırladığı gerçeğidir. 

# 7. KAYNAKÇA 

[1] T.C. Cumhurbaşkanlığı, «Resmî Yazışmalarda Uygulanacak Usul ve Esaslar Hakkında Yönetmelik,» T.C. Resmî Gazete, Sayı: 31151, 2020. 

[2] LangChain Authors, «LangGraph: Building Language Agents as Graphs,» GitHub Repository, https://github.com/langchain-ai/langgraph, 2024. 

[3] Google AI, «Gemma 2: Open Models for Language Understanding and Generation,» Google Developer Docs, 2024. 

[4] J. Smith, Optical Character Recognition and Preprocessing Techniques, New York: Academic Press, 2018. 

[5] L. Wang, et al., «A Survey on Large Language Model based Autonomous Agents,» arXiv:2308.11432, 2024. 

[6] T. Brown, et al., «Language Models are Few-Shot Learners,» Advances in Neural Information Processing Systems (NeurIPS), 2020. 

[7] Q. Wu, et al., «AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation,» arXiv:2308.08155, 2023. 

[8] Ollama, «Structured Outputs (JSON Mode) Documentation,» Ollama GitHub Repository, 2024. 

[9] V. Kotte, «PromptPort: A Reliability Layer for Cross-Model Structured Extraction,» arXiv:2601.06151, 2026. 

[10] E. Musumeci, M. Brienza, V. Suriani, D. Nardi, D. D. Bloisi, «LLM Based Multi-Agent Generation of Semi-structured Documents from Semantic Templates in the Public Administration Domain,» arXiv:2402.14871, 2024. 

[11] D. Küçük, D. Türkmen ve A. Koç, «Named-entity recognition in Turkish legal texts,» Natural Language Engineering, Cambridge University Press, 2022. 

[12] P. Lewis, E. Perez, A. Piktus, F. Petroni, V. Karpukhin, N. Goyal, H. Küttler, M. Lewis, W. Tau Yih, T. Rocktäschel, S. Riedel ve D. Kiela, «Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks,» Advances in Neural Information Processing Systems (NeurIPS), 2020. 

[13] Y. Hu ve Y. Lu, «RAG and RAU: A Survey on Retrieval-Augmented Language Model in Natural Language Processing,» arXiv:2404.19543, 2024. 

