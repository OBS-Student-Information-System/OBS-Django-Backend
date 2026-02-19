"""
Auth Parser Module.
Handles parsing of login page, dashboard, and error messages.
"""
from bs4 import BeautifulSoup
from typing import Dict, Any, Optional
import base64
from core.config import SELECTORS, ERROR_STRINGS
from core.utils import get_hidden_inputs, fix_url

def parse_login_page(html_content: bytes) -> Dict[str, Any]:
    """Parse login page for captcha and viewstate."""
    soup = BeautifulSoup(html_content, "lxml")
    title = soup.title.string if soup.title else "Baslik Yok"
    
    # Extract Hidden Inputs (ViewState)
    hidden_inputs = get_hidden_inputs(soup)
    
    # Captcha URL extraction is typically done via soup find, but since we need session to download it,
    # we return the src URL here and let the scraper handle the download.
    captcha_url = None
    img_tag = soup.find(id=SELECTORS["CAPTCHA_IMG"])
    if img_tag:
        src = img_tag.get("src")
        captcha_url = fix_url(src)

    return {
        "view_state_data": hidden_inputs,
        "captcha_url": captcha_url,
        "title": title
    }

def parse_login_error(html_content: bytes) -> Dict[str, Any]:
    """Parse login response for error messages."""
    soup = BeautifulSoup(html_content, 'lxml')
    error_elem = soup.find(id=SELECTORS["LOGIN_ERROR_LABEL"])
    
    error_text = error_elem.text.strip() if error_elem else ""
    if not error_text:
        return None

    # Refined Error Classification using Config Constants
    error_code = 'LOGIN_FAILED'
    
    def is_error(key):
        return any(s in error_text.lower() if s.islower() else s in error_text for s in ERROR_STRINGS[key])

    if is_error("CAPTCHA"):
        error_code = 'INVALID_CAPTCHA'
    elif is_error("CREDENTIALS"):
        error_code = 'INVALID_CREDENTIALS'
    
    return {
        "success": False,
        "message": error_text,
        "error_code": error_code
    }

def parse_student_info(html_content: bytes, current_student: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse student info from dashboard HTML.
    Updates 'current_student' dict with found info.
    """
    soup = BeautifulSoup(html_content, "lxml")
    result = current_student.copy()
    
    # --- Student Name ---
    if result["name"] == "Öğrenci":
        name_elem = soup.find(id=SELECTORS.get("STUDENT_NAME", "lblOgrenciAdSoyad"))
        if name_elem and name_elem.text.strip():
            result["name"] = name_elem.text.strip()
        else:
            span = soup.find("span", class_="user-name")
            if span:
                result["name"] = span.text.strip()
    
    # --- GPA (AGNO) ---
    if result["gpa"] is None:
        gpa_elem = soup.find(id=SELECTORS.get("GPA_LABEL", "lblAGNO"))
        if gpa_elem and gpa_elem.text.strip():
            raw_gpa = gpa_elem.text.strip()
            clean_gpa = raw_gpa.replace("AGNO:", "").replace("AGNO", "").strip().replace(",", ".")
            result["gpa"] = clean_gpa

    # --- Profile Photo URL ---
    # We return URL, scraper downloads it
    photo_url = None
    if result["profile_photo"] is None:
        photo_elem = soup.find(id=SELECTORS.get("PROFILE_PHOTO_IMG", "imgPhoto"))
        if photo_elem:
            photo_src = photo_elem.get("src")
            if photo_src:
                photo_url = fix_url(photo_src)
    
    return result, photo_url
