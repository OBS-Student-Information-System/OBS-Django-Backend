"""
Grades Service.
Acts as the intermediary between the API/Controller and the Data Layer (Scraper/DB).
Responsible for business logic, DTO transformation, and providing a stable interface.
"""
from typing import Dict, Any, Optional
from modules.grades.scraper import GradesScraper
from core.logger import setup_logger

logger = setup_logger(__name__)

class GradesService:
    def __init__(self, session=None):
        self.scraper = GradesScraper(session)

    def update_session_cookies(self, cookies: Dict[str, str]):
        """Updates the session with provided cookies."""
        if cookies:
            self.scraper.session.cookies.update(cookies)

    def get_grades(self, term_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Retrieves grades for the specified term.
        """
        # In the future, this could check a Cache/Database first before scraping
        result = self.scraper.fetch_grades(term_id)
        
        if result["success"]:
            # We can enrich the data here if needed (e.g., adding 'fetched_at' timestamp)
            import datetime
            result["fetched_at"] = datetime.datetime.now().isoformat()
            
        return result

    def get_terms(self) -> Dict[str, Any]:
        """
        Retrieves available terms.
        """
        return self.scraper.get_available_terms()
