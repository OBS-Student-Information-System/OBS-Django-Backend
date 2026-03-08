"""
Service layer for Department Schedule (Bölüm Programı).
Returns standard envelope: status, data, message, error_code.
"""
import logging
from typing import Dict, Any, Optional

from core.interfaces import IDepartmentScheduleService
from modules.department_schedule.scraper import DepartmentScheduleScraper

logger = logging.getLogger(__name__)


class DepartmentScheduleService(IDepartmentScheduleService):
    def __init__(self):
        self.scraper = DepartmentScheduleScraper()

    def update_session_cookies(self, cookies: Dict[str, str]) -> None:
        if cookies:
            self.scraper.session.cookies.update(cookies)

    def get_department_schedule(
        self,
        cookies: Dict[str, str] = None,
        term_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        if cookies:
            self.update_session_cookies(cookies)

        logger.info("Fetching Department Schedule (term_id=%s)...", term_id)
        result = self.scraper.fetch_department_schedule(term_id=term_id)

        if result.get("status") == "success":
            return {
                "status": "success",
                "data": result.get("data", {}),
                "message": result.get("message", "Bölüm programı başarıyla getirildi"),
            }

        return {
            "status": "error",
            "message": result.get("message", "Bölüm programı alınırken bir hata oluştu."),
            "error_code": result.get("error_code", "DEPARTMENT_SCHEDULE_FETCH_ERROR"),
        }
