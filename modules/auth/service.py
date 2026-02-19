from typing import Dict, Any, Optional
import base64
from modules.auth.scraper import AuthScraper
from core.logger import setup_logger
from core.interfaces import IAuthService

logger = setup_logger(__name__)

class AuthService(IAuthService):
    def __init__(self, scraper=None, session=None):
        # Allow injecting scraper for testing
        self.scraper = scraper or AuthScraper(session)

    def get_session(self):
        """Returns the underlying session (useful for stateful chaining)."""
        return self.scraper.session

    def update_session_cookies(self, cookies: Dict[str, str]):
        """Updates the session with provided cookies."""
        if cookies:
            self.scraper.session.cookies.update(cookies)

    def prepare_login(self) -> Dict[str, Any]:
        """
        Prepares the login page logic.
        Orchestrates fetching page and downloading captcha.
        """
        # Fetch raw data from scraper
        data = self.scraper.fetch_login_page()
        
        if "error" in data:
            return data

        # Business Logic: Download Captcha if URL exists
        captcha_b64 = None
        captcha_url = data.get("captcha_url")
        
        if captcha_url:
            try:
                # Use the scraper's session to ensure cookies are sent if needed
                r_img = self.scraper.session.get(captcha_url)
                if r_img.status_code == 200:
                    captcha_b64 = base64.b64encode(r_img.content).decode('utf-8')
                    logger.debug("Captcha image downloaded and encoded by Service.")
            except Exception as e:
                logger.warning(f"Failed to download captcha image: {e}")

        # Construct Response (DTO)
        return {
            "captcha_image": captcha_b64,
            "view_state_data": data["view_state_data"],
            "cookies": data["cookies"],
            "debug": data["debug"]
        }

    def login(self, username, password, captcha_code, view_state_data) -> Dict[str, Any]:
        """
        Executes the login logic.
        """
        # Here we could add extra business logic, e.g., logging login attempts to a DB
        return self.scraper.attempt_login(username, password, captcha_code, view_state_data)

