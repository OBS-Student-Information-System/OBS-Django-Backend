import logging
from typing import Dict, Any

from core.interfaces import IPersonalInfoService
from modules.personal_info.scraper import PersonalInfoScraper
from datetime import datetime

logger = logging.getLogger(__name__)

class PersonalInfoService(IPersonalInfoService):
    def __init__(self):
        self.scraper = PersonalInfoScraper()
        
    def update_session_cookies(self, cookies: Dict[str, str]) -> None:
        """Updates the underlying scraper's session cookies."""
        if cookies:
             self.scraper.session_manager.update_cookies(cookies)

    def get_personal_info(self, cookies: Dict[str, str] = None) -> Dict[str, Any]:
        """
        Orchestrates the scraping of Personal Information and returning standard JSON envelope.
        """
        if cookies:
            self.update_session_cookies(cookies)
            
        logger.info("Fetching Personal Information...")
        result = self.scraper.fetch_personal_info()
        
        if result["success"]:
            # Add fetch timestamp metadata
            fetched_at = datetime.now().isoformat()
            result["data"]["fetched_at"] = fetched_at
            
            return {
                "success": True,
                "data": result["data"],
                "message": "Özlük Bilgileri başarıyla getirildi"
            }
            
        # Return error envelope
        return {
            "success": False,
            "message": result.get("message", "Bilinmeyen bir hata oluştu"),
            "error_code": result.get("error_code", "UNKNOWN_ERROR")
        }
