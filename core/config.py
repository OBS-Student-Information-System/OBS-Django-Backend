"""
Configuration constants for OBS Backend.
"""

# ANA AYARLAR
OBS_DOMAIN = "https://obs.ozal.edu.tr"
OBS_ROOT = f"{OBS_DOMAIN}/oibs/std"

# URL SABİTLERİ
BASE_URL = f"{OBS_ROOT}/"
LOGIN_URL = f"{OBS_ROOT}/login.aspx"
DASHBOARD_URL = f"{OBS_ROOT}/duyuru_new.aspx" # AGNO here
GRADES_URL = f"{OBS_ROOT}/not_listesi_op.aspx"
SCHEDULE_URL = f"{OBS_ROOT}/caller.aspx?curPage=108"
TRANSCRIPT_URL = f"{OBS_ROOT}/caller.aspx?curPage=109"
CALENDAR_URL = f"{OBS_ROOT}/caller.aspx?curPage=101"
PERSONAL_INFO_CALLER_URL = f"{OBS_ROOT}/caller.aspx?curPage=100"
PERSONAL_INFO_FRAME_URL = f"{OBS_ROOT}/ogr_ozluk.aspx"
STUDENT_FILE_CALLER_URL = f"{OBS_ROOT}/caller.aspx?curPage=111"
STUDENT_FILE_FRAME_URL = f"{OBS_ROOT}/ogr_genel_bilgiler.aspx"
USER_MANUAL_URL = f"{OBS_ROOT}/caller.aspx?curPage=98" 
FOOD_MENU_URL = "https://sksdb.ozal.edu.tr/yemek_listesi"

# REFERER AYARLARI
DEFAULT_REFERER = f"{OBS_ROOT}/index.aspx?curOp=0"

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
    "SCREEN_HEIGHT": "txt_scrHeight",
    "STUDENT_NAME": "lblOgrenciAdSoyad",  # CORRECTED per User Request
    "GPA_LABEL": "lblAGNO",               # CORRECTED per User Request (AGNO only)
    "PROFILE_PHOTO_IMG": "imgPhoto",       # Student profile photo on dashboard
}

# HATA MESAJLARI (Backend'den dönen raw stringler)
ERROR_STRINGS = {
    "CAPTCHA": ["Güvenlik kodu hatalı", "captcha"],
    "CREDENTIALS": ["Kullanıcı adı veya şifresi geçersiz", "geçersiz"]
}
