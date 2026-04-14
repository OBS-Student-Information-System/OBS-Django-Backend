import logging
from typing import Any, Dict, Optional

from core.interfaces import ICurriculumStatusService
from modules.curriculum_status.scraper import CurriculumStatusScraper

logger = logging.getLogger(__name__)


class CurriculumStatusService(ICurriculumStatusService):
    def __init__(self) -> None:
        self.scraper = CurriculumStatusScraper()

    def update_session_cookies(self, cookies: Dict[str, str]) -> None:
        if cookies:
            self.scraper.session.cookies.update(cookies)

    def get_curriculum_status(
        self,
        cookies: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        if cookies:
            self.update_session_cookies(cookies)

        logger.info("Fetching curriculum status...")
        result = self.scraper.fetch_curriculum_status()

        if result.get("status") == "success":
            return {
                "status": "success",
                "data": result.get("data", {}),
                "message": result.get(
                    "message", "Müfredat durumu başarıyla getirildi"
                ),
            }

        return {
            "status": "error",
            "message": result.get(
                "message", "Müfredat durumu alınırken bir hata oluştu."
            ),
            "error_code": result.get(
                "error_code", "CURRICULUM_STATUS_FETCH_ERROR"
            ),
        }
