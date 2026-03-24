import logging
from typing import Any, Dict

from core.interfaces import IOfferedCoursesService
from modules.offered_courses.scraper import OfferedCoursesScraper

logger = logging.getLogger(__name__)


class OfferedCoursesService(IOfferedCoursesService):
    """Service layer for Offered Department Courses."""

    def __init__(self) -> None:
        self.scraper = OfferedCoursesScraper()

    def update_session_cookies(self, cookies: Dict[str, str]) -> None:
        if cookies:
            self.scraper.session.cookies.update(cookies)

    def get_offered_courses(self, cookies: Dict[str, str] = None) -> Dict[str, Any]:
        if cookies:
            self.update_session_cookies(cookies)

        logger.info("Fetching offered courses...")
        result = self.scraper.fetch_offered_courses()

        if result.get("status") == "success":
            return {
                "status": "success",
                "data": result.get("data", []),
                "message": result.get("message", "Açılan dersler başarıyla getirildi"),
            }

        return {
            "status": "error",
            "message": result.get("message", "Açılan dersler alınırken bir hata oluştu."),
            "error_code": result.get("error_code", "OFFERED_COURSES_FETCH_ERROR"),
        }
