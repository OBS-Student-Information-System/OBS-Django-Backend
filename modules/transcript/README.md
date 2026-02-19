# Transcript Module

Öğrenci transkriptini **PDF** formatında çeken modüldür.

## 📌 Scraper Logic: "The Caller Pattern"
Bu modül, OBS'in "Iframe içinde sayfa yükleme" mantığını (Caller) kullanır.

*   **URL:** `https://obs.ozal.edu.tr/oibs/std/caller.aspx?curPage=109`
*   **Page ID:** `109` (Transkript sayfası)
*   **Logic:**
    1.  Tarayıcı gibi davranarak (`Referer`, `Sec-Fetch-*` headerları) doğrudan caller sayfasına istek atar.
    2.  OBS, bu istek sonucunda doğrudan **PDF dosyası** stream eder (veya PDF'i içeren bir response döner).
    3.  Modül, gelen verinin `Content-Type`'ının PDF olup olmadığını kontrol eder.

## 🚨 Critical Headers
Bu istek için aşağıdaki headerlar **ZORUNLUDUR**, aksi takdirde OBS "Doğrudan erişim yasak" diyebilir veya login'e atabilir:
```python
{
    'Referer': 'https://obs.ozal.edu.tr/oibs/std/index.aspx?curOp=0',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'same-origin',
}
```

## ⚠️ Known Issues
*   Session timeout olduğunda PDF yerine HTML login sayfası dönebilir. Scraper bunu `PDF header` kontrolü ile algılar.
