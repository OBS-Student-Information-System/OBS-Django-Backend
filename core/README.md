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

### `logger.py`
*   Merkezi loglama yapılandırması.
*   Tüm modüller `.print()` yerine `logger.info()` veya `logger.error()` kullanır.
