# Grades Module

Öğrenci notlarını (Not Listesi) çeken ve dönem değiştirme işlemini yöneten modüldür.

## 📌 Architecture: Service → Scraper → Parser

### Service (`service.py`)
*   Orchestrator. Cookie yönetimi ve DTO dönüşümü yapar.
*   `get_grades(term_id)`: Belirtilen dönemin notlarını getirir.
*   `get_terms()`: Mevcut dönem listesini getirir.

### Scraper (`scraper.py`)
*   `fetch_grades(term_id)`: Sayfayı çeker, gerekirse `__EVENTTARGET` Postback ile dönem değiştirir.
*   `get_available_terms()`: Dropdown'dan dönem listesini parse eder.
*   AGNO (Genel Not Ortalaması) bu sayfadan da çekilir (`lblAGNO`).

### Parser (`parser.py`)
*   `parse_grades_table(html)`: HTML tablosunu `List[GradeItem]` formatına çevirir.
*   Vize, Final, Büt ve Harf Notu ayrıştırılır.

## 📌 Scraper Logic: "Postback Simulation"
ASP.NET Postback mekanizması kullanılarak dönem değişimi sağlanır:
1.  İlk `GET` ile sayfa ve ViewState yüklenir.
2.  `__EVENTTARGET = "cmbDonemler"` ile dönem dropdown'u simüle edilir.
3.  Yeni dönemin notları POST yanıtında gelir.

## ⚠️ Known Issues
*   `lxml` parser kullanılır. Eğer HTML yapısı bozuksa fallback yoktur.
*   Not tablosu ID'si (`grd_not_listesi`) değişirse çalışmaz.
