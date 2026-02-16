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

            soup = BeautifulSoup(r.content, "lxml")
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
                    # CRITICAL FIX: Follow the redirect (start.aspx?gkm=...) to fully activate the session
                    # Many ASP.NET apps require visiting the landing page with the token to set final cookies
                    
                    # If redirect URL starts with /, it's already an absolute path from domain root
                    if redirect_url.startswith('/'):
                        full_redirect_url = f"https://obs.ozal.edu.tr{redirect_url}"
                    else:
                        full_redirect_url = fix_url(redirect_url)
                    
                    logger.info(f"Following redirect to finalize authentication: {full_redirect_url}")
                    
                    try:
                        self.session.get(full_redirect_url)
                        logger.info("Successfully visited landing page.")
                    except Exception as e:
                        logger.warning(f"Failed to follow redirect: {e}")

                    return {
                        "success": True,
                        "message": "Giriş başarılı",
                        "cookies": requests.utils.dict_from_cookiejar(self.session.cookies),
                        "student_name": self._scrape_student_name(full_redirect_url)
                    }
                else:
                    logger.warning("Redirected back to login.aspx.")
            
            # Case 2: Login Failed (Stayed on page, check for error message)
            soup = BeautifulSoup(response.content, 'lxml')
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

    def _scrape_student_name(self, dashboard_url: str) -> str:
        """
        Helper to scrape student name. Tries multiple potential dashboard URLs.
        """
        try:
            # 1. Try the redirect URL first
            targets = [dashboard_url]
            
            # 2. Add standard OBS dashboard paths
            base_url = "https://obs.ozal.edu.tr/oibs/std/"
            targets.append(f"{base_url}index.aspx?curOp=0") # User provided specific URL
            targets.append(f"{base_url}default.aspx")
            targets.append(f"{base_url}index.aspx")
            
            headers = {
                 "Referer": "https://obs.ozal.edu.tr/oibs/std/login.aspx"
            }

            for url in targets:
                if not url: continue
                
                try:
                    logger.debug(f"Scraping name from: {url}")
                    r = self.session.get(url, headers=headers)
                    if r.status_code == 200:
                        soup = BeautifulSoup(r.content, "lxml")
                        # Try specific ID first
                        name_elem = soup.find(id=SELECTORS.get("STUDENT_NAME", "lblOgrenciAdSoyad"))
                        if name_elem and name_elem.text.strip():
                            logger.info(f"Check 1: Found name via ID in {url}")
                            return name_elem.text.strip()
                        
                        # Fallback: Try bold span inside header if ID fails
                        # Some OBS versions put name in a span under .user-info
                        span = soup.find("span", class_="user-name")
                        if span:
                            logger.info(f"Check 2: Found name via class in {url}")
                            return span.text.strip()
                except Exception as e:
                    logger.warning(f"Failed attempt for {url}: {e}")
                    continue
                
        except Exception as e:
            logger.warning(f"Failed to scrape student name: {e}")
        
        return "Öğrenci"

