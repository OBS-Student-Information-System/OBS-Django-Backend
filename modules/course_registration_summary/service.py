import logging
from typing import Any, Dict

from core.interfaces import ICourseRegistrationSummaryService
from modules.course_registration_summary.scraper import CourseRegistrationSummaryScraper

logger = logging.getLogger(__name__)


class CourseRegistrationSummaryService(ICourseRegistrationSummaryService):
    """Service layer for Course Registration Summary module."""

    def __init__(self) -> None:
        self.scraper = CourseRegistrationSummaryScraper()

    def update_session_cookies(self, cookies: Dict[str, str]) -> None:
        if cookies:
            self.scraper.session.cookies.update(cookies)

    def get_course_registration_summary(
        self,
        cookies: Dict[str, str] = None,
    ) -> Dict[str, Any]:
        if cookies:
            self.update_session_cookies(cookies)

        logger.info("Fetching course registration summary...")
        result = self.scraper.fetch_course_registration_summary()

        if result.get("status") == "success":
            return {
                "status": "success",
                "data": result.get("data", {}),
                "message": result.get(
                    "message", "Ders kayıt özeti başarıyla getirildi"
                ),
            }

        return {
            "status": "error",
            "message": result.get(
                "message", "Ders kayıt özeti alınırken bir hata oluştu."
            ),
            "error_code": result.get(
                "error_code", "COURSE_REG_SUMMARY_FETCH_ERROR"
            ),
        }
