# Authentication Module

## 🏗 Architecture Refactor (2026)

Bu modül **Separation of Concerns (SoC)** prensibine tam uyumlu hale getirilmiştir.

### 1. Service Layer (`service.py`)
*   **Rol:** Orchestrator (Yönetici).
*   **Sorumlulukları:**
    *   `IAuthService` arayüzünü implemente eder.
    *   Scraper'dan ham veriyi alır.
    *   **Karar Mekanizması:** Captcha indirilmeli mi? Hata var mı? Bu kararları VERİR.
    *   **DTO:** Veriyi `TypedDict` formatında döner.

### 2. Scraper Layer (`scraper.py`)
*   **Rol:** Dumb Fetcher (Akılsız Getirici).
*   **Sorumlulukları:**
    *   Sadece HTTP isteği atar ve HTML parse eder.
    *   "Captcha indireyim mi?" diye DÜŞÜNMEZ. Sadece URL'i bulur ve döner.
    *   Business Logic barındırmaz.

### 3. Parser Layer (`parser.py`)
*   **Rol:** Pure Function.
*   **Sorumlulukları:**
    *   HTML -> Dict dönüşümü yapar.
    *   Yan etkisi (Side Effect) yoktur.
