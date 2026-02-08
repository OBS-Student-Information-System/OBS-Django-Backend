# Scripts Directory

Bu klasör, geliştirme ve operasyon süreç yardımcı araçlarını içerir.

## `run_local.py`
*   **Amaç:** Backend'i yerel makinede (Localhost) çalıştırmak.
*   **Nasıl Çalışır?** Standard Python `http.server` kütüphanesini kullanarak `api/index.py` dosyasındaki `handler` sınıfını ayağa kaldırır.
*   **Vercel Simülasyonu:** Vercel ortamındaki Serverless Function yapısını yerelde taklit eder, böylece `vercel dev` kurmaya gerek kalmadan geliştirme yapılabilir.
