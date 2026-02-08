# Modules Directory

Business Logic (İş Mantığı) katmanıdır. Her modül kendi içinde bağımsızdır.

## Mimari: Service-Scraper Pattern

Bu projede **Separation of Concerns** (İşlerin Ayrılması) prensibi gereği her modül iki ana katmana ayrılmıştır:

### 1. Service Layer (`service.py`)
*   **Görev:** API (Controller) ile Data Source (Scraper) arasındaki köprüdür.
*   **Sorumlulukları:**
    *   Gelen veriyi doğrulamak.
    *   Scraper'ı çağırmak.
    *   Dönen "Ham" veriyi, API'nin beklediği "DTO" (Data Transfer Object) formatına çevirmek.
    *   İleride veritabanı entegrasyonu gelirse, Scraper yerine DatabaseRepository çağrılacak yer BURASIDIR.

### 2. Data Layer / Scraper (`scraper.py`)
*   **Görev:** Veriyi kaynaktan (OBS Web Sitesi) çekmek.
*   **Sorumlulukları:**
    *   HTTP istekleri atmak (Requests).
    *   HTML parse etmek (BeautifulSoup).
    *   ViewState, Cookie ve Redirect gibi "Web" detaylarıyla uğraşmak.
    *   **NOT:** Bu katman "Kirli" katmandır. Site değişirse burası bozulur, ama Service katmanı sayesinde uygulamanın geri kalanı korunur.

## Modüller
*   **`auth/`**: Giriş işlemleri, Captcha çözme, Session yönetimi.
*   **`grades/`**: Notları görüntüleme, dönem listeleme.
