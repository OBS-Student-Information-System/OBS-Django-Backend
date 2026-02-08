# OBS Backend - Service Oriented Architecture

OBS Mobile Application için geliştirilmiş, **Service-Oriented** (Servis Odaklı) bir Python Backend projesidir.

## 🏗 Mimari Felsefe: "The Facade"
Bu backend, mobil uygulamanın OBS sistemine erişmesi için bir **Vekil Sunucu (Proxy/Adapter)** görevi görür.

### 🔌 Service Layer & Frontend Decoupling
Frontend (Flutter Mobile App) **ASLA** backend'in veriyi nereden bulduğunu bilmez.
*   Veri şu an **Scraping** yöntemiyle [obs.ozal.edu.tr](https://obs.ozal.edu.tr) adresinden anlık çekilmektedir.
*   Gelecekte veri **PostgreSQL** veya başka bir **Veritabanından** gelebilir.
*   **ÖNEMLİ:** Backend'in veri kaynağı değişse bile, Frontend'e sunduğu JSON formatı (Contract) **ASLA** değişmeyecektir.

### 🚀 Stale-While-Revalidate Desteği
Backend, Frontend'in **Stale-While-Revalidate** (Önce önbelleği göster, sonra güncel veriyi çek) yapısına tam uyumludur.
1.  **Stateless Görünüm:** API her ne kadar session tabanlı bir siteyi scrape etse de, dışarıya **Stateless** bir REST API gibi davranır.
2.  **Kararlı Yapı:** Scraper hata alsa bile backend standart bir hata mesajı ("envelope") döner, böylece frontend önbellekteki veriyi göstermeye devam edebilir.

## 📂 Klasör Yapısı

*   **`api/`**: Giriş kapısı (Entry Point). HTTP isteklerini karşılar ve Router görevi görür.
*   **`modules/`**: İş mantığı (Business Logic).
    *   **`service.py`**: Dış dünyaya açılan kapı. Veriyi işler, formatlar. Scraper'ı veya Database'i çağırır.
    *   **`scraper.py`**: Kirli işleri yapar. HTML parse eder, siteye istek atar. "Data Source" katmanıdır.
*   **`core/`**: Ortak ayarlar, sabitler ve yardımcı fonksiyonlar.
*   **`scripts/`**: Yardımcı araçlar (Local Runner vb.).
*   **`tests/`**: Test dosyaları.

## 🛠 Kurulum ve Çalıştırma

1.  Sanal ortamı kurun:
    ```bash
    python -m venv venv
    ./venv/Scripts/activate
    ```
2.  Bağımlılıkları yükleyin:
    ```bash
    pip install -r requirements.txt
    ```
3.  Sunucuyu başlatın:
    ```bash
    python scripts/run_local.py
    ```
    Sunucu `http://localhost:8000` adresinde çalışacaktır.
