# Student File (Öğrenci Dosyası / Genel Bilgiler) Module

Öğrencinin OBS üzerindeki tüm özlük dışı durumunu, akademik geçmişini, aktif ders kayıt durumunu, onur belgelerini ve akademik tarihsel loglarını (ceza, kayıt dondurma vb.) toplayan merkezi modüldür.

## 📌 Architecture: Service → Scraper

### Service (`service.py`)
*   **Orchestrator Role:** Cookie validasyonunu yapar ve Scraper'ı tetikler.
*   **Data Formatting:** Gelen ham `dict` sözlüğünü, projenin standart API cevap formatına (JSON zarfına) oturtur.

### Scraper (`scraper.py`)
*   `fetch_student_file()`: Öğrenci dosyası `Genel Bilgiler` (Menu 0) sayfasını indirir ve parse eder. Diğer sekmeler (Menu 1-16) performans gereksinimleri sebebiyle şimdilik boş (`[]`) dönmek üzere ayarlanmıştır.
*   `_fetch_and_bypass_redirects()`: OBS sunucusunun kurduğu **Native Browser Security Check (ASP.NET Interstitial Firewall)** mekanizmasını aşar.
*   `_parse_genel_bilgiler()`: İlgili HTML Response üzerinden `txtInfo*` input nesnelerini ID ve name filter kullanarak çeker.

## 📌 Scraper Logic: "Interstitial Firewall Bypass"

Bu sayfa (`ogr_genel_bilgiler.aspx`) basit bir GET isteği ile çalışmaz. OBS altyapısı, botları engellemek için araya bir `Yönlendirme Yapılıyor (Redirecting...)` ekranı koyar.

Scraper'ın veri çekebilmesi için;
1.  **Sec-Fetch Headers:** `Sec-Fetch-Dest: iframe`, `Sec-Fetch-Mode: navigate`, `Sec-Fetch-Site: same-origin` headerları ile bir Chrome tarayıcısı taklit edilmek zorundadır.
2.  **Referer Chain:** İstek mutlaka `caller.aspx` üzerinden yapılmış gibi `Referer` başlığı taşımalıdır.
3.  **Bypass Interception:** Eğer hala araya boş bir Javascript yönlendirme formu (`redirect.aspx`) girerse, sunucu `__VIEWSTATE` ve kimlik gizli alanlarını (hidden inputs) bulup asıl sayfaya **otomatik POST** (`_fetch_and_bypass_redirects`) atmak zorundadır. Aksi halde tüm `input` değerleri HTML'de `""` (boş string) olarak döner.

## ⚠️ Known Issues
*   Tüm `Genel Bilgiler` verileri salt okunur (Read-Only) inputlar veya span'ler içerisindedir. HTML yapısı değişirse Regex (`soup.find(attrs)`) patlayabilir.
*   Şu an 16 alt modülün (`egitim_bilgileri`, `ceza_bilgileri` vb.) implementasyonu boştur (empty list döner). Projenin Faz-2 (Phase-2) aşamasında bu sekmelerin implemente edilmesi halinde `ThreadPoolExecutor` kullanılarak Asenkron POST işlemi (UpdatePanel scraping) devreye sokulmalıdır.
