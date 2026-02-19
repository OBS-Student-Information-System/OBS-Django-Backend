# Food Module

Üniversite yemekhanesinin günlük menüsünü çeken modüldür.

## 📌 Scraper Logic: "Public Scraper"
Diğer modüllerin aksine, bu modül **OBS Oturumu (Authentication) gerektirmez.** Üniversitenin halka açık web sitesinden veri çeker.

*   **URL:** `https://sksdb.ozal.edu.tr/yemek_listesi` (config'den gelen URL)
*   **Method:** `GET`
*   **SSL Verification:** `verify=False` (Sertifika hatalarını aşmak için devre dışı bırakılmıştır).

## 🧩 Parsing Logic
Basit bir CSS Selector yapısı kullanır:
*   Selector: `.box .box__content p`
*   Sıralama (Varsayım):
    1.  Ana Yemek
    2.  Yan Yemek (Pilav/Makarna)
    3.  Çorba
    4.  Tatlı/İçecek

## ⚠️ Known Issues
*   Web sitesi tasarımı değişirse (class isimleri değişirse) veri gelmez.
*   Sıralama sabit değildir, bazen çorba en başta yazılabilir. Bu scraper **sabit sıra** varsayımıyla çalışır, bu yüzden bazen "Ana Yemek" yerinde "Çorba" görünebilir.
