# API Directory

Bu klasör, backend'in **HTTP Giriş Kapısıdır (Entry Point)**.

## `index.py`
Bu dosya **Vercel Serverless Function** yapısına uygun olarak tasarlanmıştır ancak yerel sunucuda (`scripts/run_local.py`) da çalışabilir. Vercel terk edilmiştir ve artık yerelde çalışmaktadır.

### Görevleri (Controller Role)
1.  **Routing:** Gelen POST isteğindeki `action` parametresine göre (`login`, `get_grades` vb.) isteği ilgili Servise yönlendirir.
2.  **Deserialization:** HTTP Body'sindeki JSON verisini Python objesine (Dictionary) çevirir.
3.  **Response Handling:** Servislerden dönen sonucu `200 OK`, `401 Unauthorized` veya `500 Internal Server Error` gibi uygun HTTP kodlarıyla paketleyip JSON olarak döner.
4.  **Logging:** İsteklerin giriş ve çıkışlarını loglar.

**ÖNEMLİ:** Bu dosyada **İş Mantığı (Business Logic) BULUNMAZ.** Sadece trafiği yönetir.
