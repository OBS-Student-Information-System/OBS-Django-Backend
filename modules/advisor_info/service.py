import logging
from typing import Dict, Any

from core.interfaces import IAdvisorInfoService
from modules.advisor_info.scraper import AdvisorInfoScraper

logger = logging.getLogger(__name__)


class AdvisorInfoService(IAdvisorInfoService):
    """
    Service layer for the Advisor Info module.

    Orchestrates the scraper, handles cookie wiring and normalizes
    response/envelope for the HTTP API.
    """

    def __init__(self):
        self.scraper = AdvisorInfoScraper()

    def update_session_cookies(self, cookies: Dict[str, str]) -> None:
        if cookies:
            self.scraper.session.cookies.update(cookies)

    def get_advisor_info(self, cookies: Dict[str, str] = None) -> Dict[str, Any]:
        if cookies:
            self.update_session_cookies(cookies)

        logger.info("Fetching Advisor Info...")
        result = self.scraper.fetch_advisor_info()

        if result.get("status") == "success":
            return {
                "status": "success",
                "data": result.get("data", {}),
                "message": "Danışman bilgileri başarıyla çekildi.",
            }

        return {
            "status": "error",
            "message": result.get(
                "message", "Danışman bilgileri alınırken bir hata oluştu."
            ),
            "error_code": result.get("error_code", "ADVISOR_INFO_FETCH_ERROR"),
        }

    def get_advisor_schedule(self, cookies: Dict[str, str] = None) -> Dict[str, Any]:
        if cookies:
            self.update_session_cookies(cookies)

        logger.info("Fetching Advisor schedule...")
        result = self.scraper.fetch_advisor_schedule()

        if result.get("status") == "success":
            return {
                "status": "success",
                "data": result.get("data", {}),
                "message": "Danışman ders programı başarıyla çekildi.",
            }

        return {
            "status": "error",
            "message": result.get(
                "message", "Danışman ders programı alınırken bir hata oluştu."
            ),
            "error_code": result.get("error_code", "ADVISOR_SCHEDULE_FETCH_ERROR"),
        }

