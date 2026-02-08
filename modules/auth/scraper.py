"""
Authentication Scraper Module.
Handles login page fetching and login attempts.
"""
import base64
import requests
from bs4 import BeautifulSoup
from typing import Dict, Any, Optional
from core.config import LOGIN_URL, SELECTORS, ERROR_STRINGS
from core.utils import create_session, get_hidden_inputs, fix_url
from core.logger import setup_logger

logger = setup_logger(__name__)

class AuthScraper:
    def __init__(self, session: Optional[requests.Session] = None):
        self.session = session if session else create_session()

    def fetch_login_page(self) -> Dict[str, Any]:
        """
        Fetch login page and extract captcha/viewstate.
        Returns:
            Dict containing captcha_image (base64), view_state_data, cookies, or error.
        """
        try:
            logger.info("Fetching login page...")
            r = self.session.get(LOGIN_URL)
            
            if r.status_code != 200:
                logger.error(f"Failed to fetch login page. Status: {r.status_code}")
                return {"error": f"Siteye erişilemedi. Status: {r.status_code}"}

            soup = BeautifulSoup(r.content, "html.parser")
            title = soup.title.string if soup.title else "Baslik Yok"
            logger.debug(f"Page title: {title}")

            # Extract Captcha
            captcha_b64 = None
            img_tag = soup.find(id=SELECTORS["CAPTCHA_IMG"])
            
            if img_tag:
                src = img_tag.get("src")
                url = fix_url(src)
                
                # Download Captcha Image
                r_img = self.session.get(url)
                if r_img.status_code == 200:
                    captcha_b64 = base64.b64encode(r_img.content).decode('utf-8')
                    logger.debug("Captcha image downloaded and encoded.")
                else:
                    logger.warning(f"Failed to download captcha image. Status: {r_img.status_code}")
            else:
                logger.warning(f"Captcha element ({SELECTORS['CAPTCHA_IMG']}) not found on page.")

            # Extract Hidden Inputs (ViewState)
            hidden_inputs = get_hidden_inputs(soup)
            logger.debug(f"Extracted {len(hidden_inputs)} hidden inputs.")

            return {
                "captcha_image": captcha_b64,
                "view_state_data": hidden_inputs,
                "cookies": requests.utils.dict_from_cookiejar(self.session.cookies),
                "debug": f"Site: {title}"
            }

        except Exception as e:
            logger.exception("Exception in fetch_login_page")
            return {"error": f"Backend Hatasi: {str(e)}"}

    def attempt_login(self, username, password, captcha_code, view_state_data) -> Dict[str, Any]:
        """
        Attempts login to OBS.
        """
        try:
            logger.info(f"Attempting login for user: {username}")
            
            login_data = {
                **view_state_data,
                SELECTORS["USERNAME_FIELD"]: username,
                SELECTORS["PASSWORD_FIELD"]: password,
                SELECTORS["PASSWORD_FIELD_ALT"]: password,
                SELECTORS["CAPTCHA_FIELD"]: captcha_code,
                '__EVENTTARGET': SELECTORS["LOGIN_BTN"],
                '__EVENTARGUMENT': '',
                SELECTORS["SCREEN_WIDTH"]: '1920',
                SELECTORS["SCREEN_HEIGHT"]: '1080'
            }
            
            # Remove conflicting button key if exists
            login_data.pop(SELECTORS["LOGIN_BTN"], None)
            
            response = self.session.post(LOGIN_URL, data=login_data, allow_redirects=False)
            logger.debug(f"Login POST status: {response.status_code}")
            
            # Case 1: Successful login (Redirect)
            if response.status_code == 302:
                redirect_url = response.headers.get('Location', '')
                logger.info(f"Redirect detected to: {redirect_url}")
                
                if 'login.aspx' not in redirect_url.lower():
                    return {
                        "success": True,
                        "message": "Giriş başarılı",
                        "cookies": requests.utils.dict_from_cookiejar(self.session.cookies)
                    }
                else:
                    logger.warning("Redirected back to login.aspx.")
            
            # Case 2: Login Failed (Stayed on page, check for error message)
            soup = BeautifulSoup(response.content, 'html.parser')
            error_elem = soup.find(id=SELECTORS["LOGIN_ERROR_LABEL"])
            
            error_text = error_elem.text.strip() if error_elem else ""
            if error_text:
                logger.warning(f"Login failed with message: {error_text}")
                
                # Refined Error Classification using Config Constants
                error_code = 'LOGIN_FAILED'
                
                # Helper to check if any string in list matches
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
            
            # Case 3: Unknown State
            logger.error("Login failed with no error message and no redirect.")
            return {
                "success": False,
                "message": "Giriş başarısız. Bilinmeyen sunucu yanıtı.",
                "error_code": "UNKNOWN_ERROR"
            }
            
        except Exception as e:
            logger.exception("Exception in attempt_login")
            return {
                "success": False,
                "message": f"Sunucu hatası: {str(e)}",
                "error_code": "SERVER_ERROR"
            }

