# Calendar Module

Akademik Takvimi (Sınav tarihleri, tatiller vb.) çeken modüldür.

## 📌 Scraper Logic: "Caller Pattern"
*   **URL:** `CALENDAR_URL` → `caller.aspx?curPage=101` (Iframe tabanlı navigasyon).
*   **Method:** `GET` (Redirect'ler takip edilir: `allow_redirects=True`).
*   **Headers:** `Sec-Fetch-Dest: iframe` ve `Referer: index.aspx` zorunludur.
*   **Parser:** `#grd` ID'li tabloyu arar.
    *   Sütun 1: Olay Adı
    *   Sütun 2: Başlangıç Tarihi
    *   Sütun 3: Bitiş Tarihi

## ⚠️ Known Issues
*   Tablo ID'si (`#grd`) değişirse çalışmaz.
*   Tarih formatı (DD.MM.YYYY) değişirse parsing hatası olabilir.
*   Session timeout olduğunda login sayfasına redirect algılanır ve hata fırlatılır.

