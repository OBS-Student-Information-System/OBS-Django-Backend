# Calendar Module

Akademik Takvimi (Sınav tarihleri, tatiller vb.) çeken modüldür.

## 📌 Scraper Logic
*   **URL:** `GRADES_URL` veya benzeri bir "Dashboard" sayfasından ziyade, genellikle **Genel Duyurular** veya **Akademik Takvim** menüsündeki tabloyu hedefler.
*   **Method:** `GET`
*   **Parser:** `#grd` ID'li tabloyu arar.
    *   Sütun 1: Olay Adı
    *   Sütun 2: Başlangıç Tarihi
    *   Sütun 3: Bitiş Tarihi

## ⚠️ Known Issues
*   Tablo ID'si (`#grd`) değişirse çalışmaz.
*   Tarih formatı (DD.MM.YYYY) değişirse parsing hatası olabilir.
