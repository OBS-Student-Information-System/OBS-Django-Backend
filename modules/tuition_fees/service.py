import logging
from typing import Any, Dict

from core.interfaces import ITuitionFeesService
from modules.tuition_fees.scraper import TuitionFeesScraper

logger = logging.getLogger(__name__)


class TuitionFeesService(ITuitionFeesService):
    """Service layer for Tuition & Fees module."""

    def __init__(self) -> None:
        self.scraper = TuitionFeesScraper()

    def update_session_cookies(self, cookies: Dict[str, str]) -> None:
        if cookies:
            self.scraper.session.cookies.update(cookies)

    def get_tuition_fees(self, cookies: Dict[str, str] = None) -> Dict[str, Any]:
        if cookies:
            self.update_session_cookies(cookies)

        logger.info("Fetching tuition fees...")
        result = self.scraper.fetch_tuition_fees()

        if result.get("status") == "success":
            return {
                "status": "success",
                "data": result.get("data", {}),
                "message": result.get("message", "Harç bilgileri başarıyla getirildi"),
            }

        return {
            "status": "error",
            "message": result.get("message", "Harç bilgileri alınırken bir hata oluştu."),
            "error_code": result.get("error_code", "TUITION_FEES_FETCH_ERROR"),
        }
