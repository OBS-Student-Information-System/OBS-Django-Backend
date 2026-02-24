# Core Directory

Projenin **Ortak Altyapı** katmanıdır. Tüm modüllerin kullandığı paylaşılan kodlar burada bulunur.

## Dosyalar

### `config.py`
*   **Magic Strings Vault:** Uygulama genelindeki tüm sabit değerler buradadır.
*   HTML Selector ID'leri (`imgCaptchaImg` vb.).
*   URL Adresleri.
*   Hata Mesajları.
*   **Amaç:** OBS'in yapısı değişirse kodun içinde kaybolmak yerine sadece bu dosyayı güncelleyerek sistemi ayakta tutmak.

### `utils.py`
*   Yardımcı fonksiyonlar.
*   `create_session()`: Headerları ayarlanmış güvenli request oturumu oluşturur.
*   `get_hidden_inputs()`: ASP.NET ViewState verilerini çeker.
*   `fix_url()`: Relative URL'leri absolute URL'lere çevirir.

### `router.py`
*   **ActionDispatcher:** Gelen request'leri `action` parametresine göre ilgili handler fonksiyonuna yönlendirir.
*   Open/Closed Principle'a uygun: Yeni action eklemek için mevcut kodu değiştirmek gerekmez, sadece `register()` çağrılır.

### `logger.py`
*   Merkezi loglama yapılandırması.
*   Tüm modüller `.print()` yerine `logger.info()` veya `logger.error()` kullanır.

## 🏗 Enterprise Architecture (New)

### `factory.py` (Dependency Injection)
*   **ServiceFactory:** Tüm servislerin üretiminden sorumlu merkezi fabrika.
*   Kodun içinde `AuthService()` demek yerine `ServiceFactory.create_auth_service()` denir.

### `interfaces.py` (Dependency Inversion)
*   **ABCs:** `IAuthService`, `IGradesService` gibi soyut sınıflar.
*   Modüller birbirine değil, bu arayüzlere bağımlıdır.

### `types.py` (Type Safety)
*   **TypedDicts:** `LoginResponse`, `GradeItem` gibi veri yapıları.
*   `Dict[str, Any]` belirsizliğini ortadan kaldırır ve IDE/Linter desteği sağlar.
