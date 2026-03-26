import logging
from typing import Any, Dict, Optional

from core.interfaces import IInteractiveTranscriptService
from modules.interactive_transcript.scraper import (
    InteractiveTranscriptScraper,
)

logger = logging.getLogger(__name__)


class InteractiveTranscriptService(IInteractiveTranscriptService):
    """Service layer for the Interactive Transcript (Native Transcript) module."""

    def __init__(self) -> None:
        self.scraper = InteractiveTranscriptScraper()

    def update_session_cookies(self, cookies: Dict[str, str]) -> None:
        if cookies:
            self.scraper.session.cookies.update(cookies)

    def get_interactive_transcript(
        self,
        cookies: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        if cookies:
            self.update_session_cookies(cookies)

        logger.info("Fetching interactive transcript...")
        result = self.scraper.fetch_interactive_transcript()

        if result.get("status") == "success":
            return {
                "status": "success",
                "data": result.get("data", {}),
                "message": result.get(
                    "message", "İnteraktif transkript başarıyla getirildi"
                ),
            }

        return {
            "status": "error",
            "message": result.get(
                "message", "İnteraktif transkript alınırken bir hata oluştu."
            ),
            "error_code": result.get(
                "error_code", "INTERACTIVE_TRANSCRIPT_FETCH_ERROR"
            ),
        }

