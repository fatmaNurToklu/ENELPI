# ⚠️ Ajan 1: Tesseract OCR Hatası ve Çözüm Rehberi

Bu doküman, görsel formatındaki resmi belgeler (PDF, JPG, PNG vb.) işlenirken Ajan 1'in gerçek modda çalışmak yerine **mock fallback** (yedek demo) durumuna düşmesini engellemek için yapılması gereken sistem kurulumlarını içerir.

---

## 🔍 Hatanın Sebebi
Görsel tabanlı belgeler işlenirken, Ajan 1 metni okuyabilmek için sisteminizde kurulu olan **Tesseract OCR** motorunu kullanmaya çalışır. Eğer Tesseract motoru sisteminizde yüklü değilse ya da sistem yoluna (`PATH`) eklenmemişse sistem şu hatayı verir:
`[Agent1Adapter] Agent 1 çalışma hatası: tesseract is not installed or it's not in your PATH.`

Bu durumda sistemin tamamen çökmemesi için otomatik olarak yedek demo (mock) verileri devreye girer.

---

## 🛠️ Çözüm Adımları (Windows Kurulumu)

Gerçek OCR akışını aktifleştirmek için aşağıdaki adımları takip edin:

### 1. Tesseract Yükleyicisini İndirin ve Kurun
1. [UB-Mannheim Tesseract Windows Installer](https://github.com/UB-Mannheim/tesseract/wiki) adresine gidin.
2. Listenin en üstündeki güncel sürüm Windows `.exe` dosyasını (örn. `tesseract-ocr-w64-setup-v5.x.x.exe`) indirin.
3. Kurulumu başlatın.
4. **Önemli:** Kurulum ekranındaki bileşen listesinde (Components) **"Additional script data"** ve **"Additional language data"** başlıklarının altından **Turkish** (Türkçe dil desteği - `tur`) seçeneğini mutlaka işaretleyin.
5. Kurulumu tamamlayın (Varsayılan kurulum yolu genellikle `C:\Program Files\Tesseract-OCR` şeklindedir).

### 2. Tesseract'ı Sistem Yoluna (PATH) Ekleyin
Sistemin komut satırından `tesseract` komutunu tanıyabilmesi için ortam değişkenini ayarlamanız gerekir:
1. Windows Arama çubuğuna **"Sistem ortam değişkenlerini düzenleyin"** yazın ve açın.
2. Açılan pencerede **"Ortam Değişkenleri..."** (Environment Variables) butonuna tıklayın.
3. **"Sistem değişkenleri"** (System Variables) kısmından **`Path`** değişkenini seçip **"Düzenle..."** butonuna basın.
4. Sağdaki menüden **"Yeni"** butonuna tıklayın ve Tesseract'ın kurulu olduğu klasör yolunu yapıştırın:
   `C:\Program Files\Tesseract-OCR`
5. Tüm pencereleri **"Tamam"** diyerek kapatın.

### 3. Değişiklikleri Doğrulayın ve Sistemi Yeniden Başlatın
1. Açık olan tüm terminal pencerelerini (VS Code terminali dahil) kapatın ve yeni bir komut satırı açın.
2. Aşağıdaki komutu çalıştırarak kurulumu doğrulayın:
   ```cmd
   tesseract --version
   ```
   Kurulum başarılıysa sürüm bilgisi ekrana gelecektir.
3. Projeyi yeniden başlatın:
   ```cmd
   python run.py
   ```

Artık resim veya taranmış PDF formatında evrak yüklediğinizde Ajan 1 gerçek zamanlı olarak belgedeki Türkçe metinleri okuyabilecektir.
