# User Manual Module

Kullanım Kılavuzu belgesini **PDF** formatında çeken modüldür.

## 📌 Scraper Logic: "The Caller Pattern"
Bu modül, OBS'in "Iframe içinde sayfa yükleme" mantığını (Caller) kullanır. Transkript modülü ile aynı mekanizmayı paylaşır.

*   **URL:** `https://obs.ozal.edu.tr/oibs/std/caller.aspx?curPage=98` (Bu URL config içerisinden, üniversite özelinde yapılandırılır)
*   **Page ID:** Genellikle `98` (Kullanım Kılavuzu PDF'ini barındıran sayfa)
*   **Logic:**
    1.  Tarayıcı gibi davranarak (`Referer`, `Sec-Fetch-*` headerları) doğrudan caller sayfasına istek atar.
    2.  Sunucunun 302 yönlendirmelerini (redirects) `allow_redirects=True` ile takip eder, çünkü `caller.aspx` genellikle `zfs.aspx?gkm=...` gibi başka bir URL'e yönlendirir.
    3.  OBS, bu istek sonucunda doğrudan **PDF dosyası** stream eder.
    4.  Modül, gelen verinin `Content-Type`'ının PDF olup olmadığını ve `%PDF` binary imzasını taşıyıp taşımadığını kontrol eder.
    5.  Ham PDF byte verisi, servis katmanında **Base64** formatına çevrilerek Client'a (Mobile App) iletilir.

## 🚨 Critical Headers
Bu istek için aşağıdaki headerlar **ZORUNLUDUR**, aksi takdirde OBS "Doğrudan erişim yasak" diyebilir veya hataya düşürebilir:
```python
{
    'Referer': 'https://obs.ozal.edu.tr/oibs/std/index.aspx?curOp=0',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'same-origin',
}
```

## ⚠️ Known Issues
*   Session timeout olduğunda PDF yerine HTML login sayfası dönebilir. Scraper bunu `"login.aspx" in response.url` kontrolü ve `Content-Type` doğrulaması ile engeller.
