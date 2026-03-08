"""
Service layer for the GPA History (Dönem Ortalamaları) module.

Returns standard envelope: status, data, message, error_code.
"""
import logging
from typing import Dict, Any, List

from core.interfaces import IGpaHistoryService
from modules.gpa_history.scraper import GpaHistoryScraper

logger = logging.getLogger(__name__)


class GpaHistoryService(IGpaHistoryService):
    def __init__(self):
        self.scraper = GpaHistoryScraper()

    def update_session_cookies(self, cookies: Dict[str, str]) -> None:
        if cookies:
            self.scraper.session.cookies.update(cookies)

    def get_gpa_history(self, cookies: Dict[str, str] = None) -> Dict[str, Any]:
        if cookies:
            self.update_session_cookies(cookies)

        logger.info("Fetching GPA History...")
        result = self.scraper.fetch_gpa_history()

        if result.get("status") == "success":
            return {
                "status": "success",
                "data": result.get("data", []),
                "message": result.get("message", "Ortalama geçmişi başarıyla getirildi"),
            }

        return {
            "status": "error",
            "message": result.get("message", "Dönem ortalamaları alınırken bir hata oluştu."),
            "error_code": result.get("error_code", "GPA_HISTORY_FETCH_ERROR"),
        }
