# Schedule Module

Haftalık ders programını çeken modüldür.

## 📌 Scraper Logic: "Multi-Table Parsing"
Ders programı tek bir tabloda değil, haftanın günlerini temsil eden **ayrı tablolarda** tutulur.

*   **URL:** `SCHEDULE_URL`
*   **Method:** `GET`
*   **Structure:**
    *   `#grd0` → Pazartesi
    *   `#grd1` → Salı
    *   ...
    *   `#grd6` → Pazar

## 🧩 Parsing Rules
*   Her tablo satır satır okunur.
*   "Tanımlı Ders Programı Bulunamadı" metni varsa o gün boştur.
*   **Stil Kontrolü:** `DarkGreen` stili (arka plan rengi), dersin **Uygulama/Laboratuvar** olduğunu belirtir. Scraper bunu `is_practice: true` olarak işaretler.

## ⚠️ Known Issues
*   Regex ile derslik adındaki `[Kapasite]` bilgisi (örn: `MDBF-AMFİ2[90]`) temizlenir. Regex değişirse derslik adları bozuk gelebilir.
