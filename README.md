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

## 🔄 Kritik İş Akışları (Key Workflows)

### 🔐 Login Flow & Cookie Relay
1.  **Init:** Client -> Backend (`init_login`) -> Backend OBS'den Captcha ve ViewState çeker.
2.  **Auth:** Client -> Backend (`login`) -> Backend OBS'ye POST atar.
    *   *Kritik:* Eğer redirect gelirse, backend `start.aspx` sayfasına giderek cookie'leri sabitler.
3.  **Session:** Backend -> Client'a şifrelenmiş veya ham `Session Cookies` döner. Client bunu saklar.

### 📝 Grades Flow
1.  **Request:** Client -> Backend (`get_grades`) + `Cookies`.
2.  **Restoration:** Backend cookie'leri requests session'ına yükler.
3.  **Switching:** Eğer dönem değişikliği isteniyorsa, Backend `__EVENTTARGET` postback simülasyonu ile dönem değiştirir.
4.  **Parsing:** HTML tablo parse edilir ve JSON array döner.

### 📜 Transcript Flow (Iframe/Caller)
1.  **Request:** Client -> Backend (`get_transcript`).
2.  **Navigation:** Scraper, tarayıcı taklidi yaparak (`Sec-Fetch-Dest: document`) doğrudan `caller.aspx` adresine gider.
3.  **Result:** OBS'den dönen PDF stream'i yakalanır ve client'a verilir (veya base64/binary).

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
