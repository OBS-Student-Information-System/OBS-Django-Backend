import logging
from typing import Dict, Any, Optional

from core.interfaces import IEnrolledCoursesService
from modules.enrolled_courses.scraper import EnrolledCoursesScraper

logger = logging.getLogger(__name__)


class EnrolledCoursesService(IEnrolledCoursesService):
    """
    Service layer for the Enrolled Courses (Alınan Dersler) module.
    Orchestrates the scraper, handles cookie wiring and standard envelope.
    """

    def __init__(self) -> None:
        self.scraper = EnrolledCoursesScraper()

    def update_session_cookies(self, cookies: Dict[str, str]) -> None:
        if cookies:
            self.scraper.session.cookies.update(cookies)

    def get_enrolled_courses(
        self,
        cookies: Dict[str, str] = None,
        term_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        if cookies:
            self.update_session_cookies(cookies)

        logger.info("Fetching enrolled courses...")
        result = self.scraper.fetch_enrolled_courses(term_id=term_id)

        if result.get("status") == "success":
            return {
                "status": "success",
                "data": result.get("data", []),
                "message": result.get(
                    "message", "Alınan dersler başarıyla getirildi"
                ),
            }

        return {
            "status": "error",
            "message": result.get(
                "message", "Alınan dersler alınırken bir hata oluştu."
            ),
            "error_code": result.get(
                "error_code", "ENROLLED_COURSES_FETCH_ERROR"
            ),
        }

