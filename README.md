# OBS Backend

OBS Mobil Uygulaması için geliştirilmiş, **Service-Oriented** Python Backend.

> Klasör adında "Django" geçse de, sadelik ve performans adına saf **Python `http.server`** kullanılmaktadır. Vercel üzerinde serverless function olarak deploy edilir.

## Mimari

```
Client (Flutter)  ──POST──▶  api/index.py  ──ActionDispatcher──▶  Service  ──▶  Scraper
                                                                      │
                                                          Standard JSON Envelope
                                                       { status, data, message }
```

Backend, OBS web portalına bir **Adapter/Facade** görevi görür:

- **Stateless API** — Oturum cookie'leri client tarafında saklanır; backend her istekte cookie'leri alır, işini yapar, sonucu döner.
- **Kararlı Contract** — Veri kaynağı (scraping, DB, API) ne olursa olsun, frontend'e sunulan JSON yapısı değişmez.
- **Standard Envelope** — Her yanıt `{ "status": "success" | "error", "data": ..., "message": "...", "error_code": "..." }` formatındadır.
- **SWR Uyumlu** — Frontend Stale-While-Revalidate kullanır; backend hata alsa bile standart envelope döndüğü için frontend önbelleği göstermeye devam eder.

## Proje Yapısı

```
OBS-Django-Backend/
├── api/
│   └── index.py                 # Giriş noktası — HTTP handler + ActionDispatcher
├── core/
│   ├── exceptions.py            # Custom exception sınıfları
│   ├── factory.py               # ServiceFactory (Dependency Injection)
│   ├── interfaces.py            # Servis arayüzleri (ABC)
│   ├── logger.py                # Loglama yapılandırması
│   ├── router.py                # ActionDispatcher (action → handler eşlemesi)
│   ├── tenant_config.py         # Tenant config yükleyici ve doğrulayıcı
│   ├── types.py                 # TypedDict DTO tanımları
│   └── utils.py                 # Ortak yardımcılar (create_session, get_hidden_inputs vb.)
├── config/
│   └── tenant.json              # Tenant yapılandırması (URL'ler, selector'lar, endpoint'ler)
├── modules/
│   ├── auth/                    # Giriş, captcha, oturum
│   ├── grades/                  # Notlar, dönem seçimi
│   ├── enrolled_courses/        # Alınan dersler
│   ├── schedule/                # Haftalık ders programı
│   ├── department_schedule/     # Bölüm ders programı
│   ├── transcript/              # Transkript (PDF)
│   ├── student_file/            # Öğrenci dosyası
│   ├── personal_info/           # Kişisel bilgiler
│   ├── advisor_info/            # Danışman bilgileri
│   ├── gpa_history/             # GNO geçmişi
│   ├── calendar/                # Akademik takvim
│   ├── food/                    # Yemek listesi (public)
│   └── user_manual/             # Kullanım kılavuzu (PDF)
├── scripts/
│   └── run_local.py             # Yerel geliştirme sunucusu
├── tests/                       # Testler
├── requirements.txt
└── README.md
```

Her modül aynı katmanlı yapıyı izler:

| Katman | Dosya | Sorumluluk |
|---|---|---|
| **Service** | `service.py` | İş mantığı, veriyi formatlar, scraper'ı çağırır |
| **Scraper** | `scraper.py` | HTTP istekleri, HTML parse, veri çıkarma |
| **Parser** | `parser.py` | *(opsiyonel)* Saf fonksiyon: HTML → Dict dönüşümü |

## API Referansı

Tüm istekler **tek bir POST endpoint**'ine gönderilir. İstek gövdesindeki `action` alanı hangi handler'ın çalışacağını belirler.

```
POST /api
Content-Type: application/json

{
  "action": "get_grades",
  "cookies": { "ASP.NET_SessionId": "...", ... },
  "term_id": "20252"       // opsiyonel, bazı action'lar için
}
```

### Kayıtlı Action'lar

| Action | Açıklama | Auth |
|---|---|---|
| `init_login` | Captcha ve ViewState çeker | - |
| `login` | OBS'ye giriş yapar, session cookie döner | - |
| `get_grades` | Not listesi (dönem seçimi destekler) | Cookie |
| `get_available_terms` | Kullanılabilir dönem listesi | Cookie |
| `get_enrolled_courses` | Alınan dersler (dönem seçimi destekler) | Cookie |
| `get_schedule` | Haftalık ders programı | Cookie |
| `get_department_schedule` | Bölüm ders programı (sınıf seçimi destekler) | Cookie |
| `get_transcript` | Transkript (PDF) | Cookie |
| `get_student_file` | Öğrenci dosyası | Cookie |
| `get_personal_info` | Kişisel bilgiler | Cookie |
| `update_personal_info` | Kişisel bilgi güncelleme | Cookie |
| `get_advisor_info` | Danışman bilgileri | Cookie |
| `get_advisor_schedule` | Danışman ders programı | Cookie |
| `get_gpa_history` | GNO geçmişi | Cookie |
| `get_academic_calendar` | Akademik takvim | - |
| `food_menu` | Yemek listesi | - |
| `get_user_manual` | Kullanım kılavuzu (PDF) | Cookie |

### Yanıt Formatı

**Başarılı:**
```json
{
  "status": "success",
  "data": [ ... ],
  "message": "Veriler başarıyla getirildi"
}
```

**Hata:**
```json
{
  "status": "error",
  "message": "Oturum süresi doldu",
  "error_code": "SESSION_EXPIRED"
}
```

Yaygın hata kodları: `SESSION_EXPIRED`, `NO_SESSION`, `*_FETCH_ERROR`, `*_SCRAPE_ERROR`

## Scraping Desenleri

### Caller-Frame Pattern
OBS'nin iframe yapısı nedeniyle bazı sayfalar iki adımda yüklenir:
1. `caller.aspx?curPage=X` sayfasına GET (navigasyon akışı için gerekli)
2. Asıl frame sayfasına GET (`Sec-Fetch-Dest: iframe`, `Referer: caller URL`)

Bu desen: `grades`, `enrolled_courses`, `department_schedule`, `transcript`, `schedule` vb. modüllerde kullanılır.

### ASP.NET Postback Simülasyonu
Dönem/sınıf değişikliği gibi dropdown seçimleri, ASP.NET `__EVENTTARGET` postback mekanizmasıyla simüle edilir. Hidden field'lar (`__VIEWSTATE`, `__EVENTVALIDATION`) mevcut sayfadan parse edilir ve POST edilir.

### Session Lifecycle
- Client, login sonrası aldığı cookie'leri her istekte gönderir
- Backend, oturum süresinin dolup dolmadığını URL redirect (`login.aspx`) ve sayfa içeriği kontrolü ile tespit eder
- Oturum dolmuşsa `SESSION_EXPIRED` döner, frontend kullanıcıyı login'e yönlendirir

## Multi-Tenant Yapılandırma

Tüm URL'ler, HTML selector'lar ve endpoint path'leri `config/tenant.json` dosyasından okunur. Hardcoded değer kullanılmaz. Yapılandırma `core/tenant_config.py` tarafından yüklenir ve doğrulanır.

```json
{
  "tenant_id": "mtu",
  "institution": { "name": "...", "obs_base_url": "https://..." },
  "scraper": {
    "obs_domain": "...",
    "selectors": { "TERM_DROPDOWN": "cmbDonemler", ... },
    "endpoints": { "grades_caller": "caller.aspx?curPage=...", ... }
  }
}
```

## Kurulum

```bash
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # macOS / Linux

pip install -r requirements.txt
python scripts/run_local.py  # http://localhost:8000
```

## Teknolojiler

- **Python 3.10+** — Runtime
- **requests** — HTTP client
- **BeautifulSoup4 + lxml** — HTML parsing
- **Vercel** — Serverless deployment
