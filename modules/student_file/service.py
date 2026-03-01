import logging
from typing import Dict, Any
from core.interfaces import IStudentFileService
from modules.student_file.scraper import StudentFileScraper
from datetime import datetime

logger = logging.getLogger(__name__)

class StudentFileService(IStudentFileService):
    """
    Service layer for the 'Genel Bilgiler' (Student File) module.
    Responsible for orchestrating the synchronous scraper and validating/formatting responses.
    """
    def __init__(self):
        self.scraper = StudentFileScraper()

    def update_session_cookies(self, cookies: Dict[str, str]) -> None:
        """Updates the underlying scraper's session cookies."""
        if cookies:
             self.scraper.session.cookies.update(cookies)

    def get_student_file(self, cookies: Dict[str, str] = None) -> Dict[str, Any]:
        """
        Coordinates the fetching of the 16 student file categories.
        """
        if cookies:
            self.update_session_cookies(cookies)
            
        logger.info("Fetching Student File...")
        result = self.scraper.fetch_student_file()
        
        if result.get("status") == "success":
            # Add fetch timestamp metadata
            fetched_at = datetime.now().isoformat()
            result["data"]["fetched_at"] = fetched_at
            
            return {
                "status": "success",
                "data": result["data"],
                "message": "Öğrenci dosyası (Genel Bilgiler) verileri başarıyla çekildi."
            }
            
        return {
            "status": "error",
            "message": result.get("message", "Öğrenci dosyası verileri çekilirken bir hata oluştu."),
            "error_code": result.get("error_code", "STUDENT_FILE_FETCH_ERROR")
        }
