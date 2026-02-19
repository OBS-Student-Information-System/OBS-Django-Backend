"""
Authentication Service.
Acts as the intermediary between the API/Controller and the Data Layer (Scraper/DB).
Responsible for business logic, DTO transformation, and providing a stable interface.
"""
from typing import Dict, Any, Optional
from modules.auth.scraper import AuthScraper
from core.logger import setup_logger

logger = setup_logger(__name__)

class AuthService:
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
        """
        return self.scraper.fetch_login_page()

    def login(self, username, password, captcha_code, view_state_data) -> Dict[str, Any]:
        """
        Executes the login logic.
        """
        # Here we could add extra business logic, e.g., logging login attempts to a DB
        return self.scraper.attempt_login(username, password, captcha_code, view_state_data)
