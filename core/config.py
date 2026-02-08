"""
Configuration constants for OBS Backend.
"""

# URL SABİTLERİ
BASE_URL = "https://obs.ozal.edu.tr/oibs/std/"
LOGIN_URL = "https://obs.ozal.edu.tr/oibs/std/login.aspx"
GRADES_URL = "https://obs.ozal.edu.tr/oibs/std/not_listesi_op.aspx"
SCHEDULE_URL = "https://obs.ozal.edu.tr/oibs/std/ders_programi.aspx" # Future use

# HEADER AYARLARI
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1"
}

# HTML SELECTORS (Magic Strings)
SELECTORS = {
    "CAPTCHA_IMG": "imgCaptchaImg",
    "LOGIN_ERROR_LABEL": "lblSonuclar",
    "GRADES_TABLE": "grd_not_listesi",
    "TERM_DROPDOWN": "cmbDonemler",
    "LOGIN_BTN": "btnLogin",
    "USERNAME_FIELD": "txtParamT01",
    "PASSWORD_FIELD": "txtParamT02",
    "PASSWORD_FIELD_ALT": "txtParamT1",
    "CAPTCHA_FIELD": "txtSecCode",
    "SCREEN_WIDTH": "txt_scrWidth",
    "SCREEN_HEIGHT": "txt_scrHeight"
}

# HATA MESAJLARI (Backend'den dönen raw stringler)
ERROR_STRINGS = {
    "CAPTCHA": ["Güvenlik kodu hatalı", "captcha"],
    "CREDENTIALS": ["Kullanıcı adı veya şifresi geçersiz", "geçersiz"]
}
