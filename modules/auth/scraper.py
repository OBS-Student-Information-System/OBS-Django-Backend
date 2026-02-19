"""
Authentication Scraper Module.
Handles login page fetching and login attempts.
"""
import base64
import requests
from bs4 import BeautifulSoup
from typing import Dict, Any, Optional
from core.config import LOGIN_URL, SELECTORS, ERROR_STRINGS, OBS_DOMAIN, DEFAULT_REFERER
from core.utils import create_session, fix_url
from core.logger import setup_logger
from modules.auth.parser import parse_login_page, parse_login_error, parse_student_info

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
            r = self.session.get(LOGIN_URL, timeout=30)
            
            if r.status_code != 200:
                logger.error(f"Failed to fetch login page. Status: {r.status_code}")
                return {"error": f"Siteye erişilemedi. Status: {r.status_code}"}

            # Parse using new parser module
            parsed_data = parse_login_page(r.content)
            
            # Download Captcha Image if URL found
            captcha_b64 = None
            if parsed_data.get("captcha_url"):
                try:
                    r_img = self.session.get(parsed_data["captcha_url"])
                    if r_img.status_code == 200:
                        captcha_b64 = base64.b64encode(r_img.content).decode('utf-8')
                        logger.debug("Captcha image downloaded and encoded.")
                except Exception as e:
                    logger.warning(f"Failed to download captcha image: {e}")

            return {
                "captcha_image": captcha_b64,
                "view_state_data": parsed_data["view_state_data"],
                "cookies": requests.utils.dict_from_cookiejar(self.session.cookies),
                "debug": f"Site: {parsed_data['title']}"
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
            
            response = self.session.post(LOGIN_URL, data=login_data, allow_redirects=False, timeout=45)
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
                        full_redirect_url = f"{OBS_DOMAIN}{redirect_url}"
                    else:
                        full_redirect_url = fix_url(redirect_url)
                    
                    logger.info(f"Following redirect to finalize authentication: {full_redirect_url}")
                    
                    try:
                        self.session.get(full_redirect_url, timeout=30)
                        logger.info("Successfully visited landing page.")
                    except Exception as e:
                        logger.warning(f"Failed to follow redirect: {e}")

                    student_info = self._scrape_student_info(full_redirect_url)
                    return {
                        "success": True,
                        "message": "Giriş başarılı",
                        "cookies": requests.utils.dict_from_cookiejar(self.session.cookies),
                        "student_name": student_info.get("name", "Öğrenci"),
                        "profile_photo": student_info.get("profile_photo"),
                        "gpa": student_info.get("gpa")
                    }
                else:
                    logger.warning("Redirected back to login.aspx.")
            
            # Case 2: Login Failed (Stayed on page, check for error message)
            error_result = parse_login_error(response.content)
            if error_result:
                logger.warning(f"Login failed with message: {error_result['message']}")
                return error_result
            
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

    def _scrape_student_info(self, dashboard_url: str) -> Dict[str, Any]:
        """
        Helper to scrape student name, profile photo, and GPA (AGNO) from the dashboard page.
        Returns a dict with 'name', 'profile_photo', and 'gpa'.
        """
        result = {"name": "Öğrenci", "profile_photo": None, "gpa": None}
        
        try:
            # We explicitly want to check the dashboard for AGNO
            from core.config import DASHBOARD_URL
            
            # Prioritize DASHBOARD_URL for AGNO
            targets = [DASHBOARD_URL, dashboard_url]
            
            headers = {
                 "Referer": DEFAULT_REFERER
            }

            for url in targets:
                if not url: continue
                
                try:
                    logger.debug(f"Scraping student info from: {url}")
                    r = self.session.get(url, headers=headers, timeout=15)
                    
                    if r.status_code == 200:
                        # Use parser for student info
                        result, photo_url = parse_student_info(r.content, result)
                        
                        # Download photo if URL found
                        if photo_url:
                            try:
                                photo_response = self.session.get(photo_url, timeout=10)
                                if photo_response.status_code == 200 and len(photo_response.content) > 100:
                                    result["profile_photo"] = base64.b64encode(photo_response.content).decode('utf-8')
                                    logger.info("Profile photo downloaded.")
                            except Exception as e:
                                logger.warning(f"Failed to download profile photo: {e}")

                        # If we have name and GPA, we can stop (photo is bonus)
                        if result["name"] != "Öğrenci" and result["gpa"] is not None:
                            break
                        
                except Exception as e:
                    logger.warning(f"Failed attempt for {url}: {e}")
                    continue
                
        except Exception as e:
            logger.warning(f"Failed to scrape student info: {e}")
        
        return result

