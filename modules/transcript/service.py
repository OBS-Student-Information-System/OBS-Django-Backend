"""
Transcript Service Module.
Business logic layer for transcript operations.
"""
import base64
from typing import Dict, Any
from core.logger import setup_logger
from core.utils import create_session
from .scraper import TranscriptScraper

logger = setup_logger(__name__)


class TranscriptService:
    """Service for managing transcript operations.
    
    Handles session management, PDF fetching, and base64 encoding.
    """
    
    def __init__(self, scraper=None, session=None):
        """Initialize service with optional session and scraper.
        
        Args:
            scraper: Optional scraper instance for testing.
            session: Optional requests session for maintaining cookies.
        """
        self.session = session if session else create_session()
        self.scraper = scraper or TranscriptScraper(self.session)
    
    def update_session_cookies(self, cookies: Dict[str, str]):
        """Updates the session with provided cookies.
        
        Args:
            cookies: Dictionary of cookie name-value pairs.
        """
        if cookies:
            self.session.cookies.update(cookies)
            logger.debug(f"Updated session with {len(cookies)} cookies")
    
    def get_transcript(self) -> Dict[str, Any]:
        """Fetches transcript PDF and converts to base64.
        
        Returns:
            Dict containing:
            {
                "success": bool,
                "data": {
                    "pdf_base64": str,     # Base64 encoded PDF
                    "size_bytes": int,     # Original PDF size
                    "fetched_at": str      # ISO timestamp
                },
                "message": str,
                "error_code": str  # Optional, only on error
            }
        """
        try:
            logger.info("TranscriptService: Fetching transcript")
            
            # Fetch PDF from scraper
            result = self.scraper.fetch_transcript()
            
            if result["success"]:
                pdf_bytes = result["data"]
                
                # Convert to base64
                pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
                
                # Add timestamp
                import datetime
                fetched_at = datetime.datetime.now().isoformat()
                
                logger.info(f"Successfully encoded PDF to base64. Original size: {len(pdf_bytes)} bytes")
                
                return {
                    "success": True,
                    "data": {
                        "pdf_base64": pdf_base64,
                        "size_bytes": len(pdf_bytes),
                        "fetched_at": fetched_at
                    },
                    "message": "Transcript fetched successfully"
                }
            else:
                # Scraper returned error
                logger.error(f"Scraper failed: {result.get('error')}")
                return {
                    "success": False,
                    "message": result.get("error", "Failed to fetch transcript"),
                    "error_code": "FETCH_FAILED"
                }
                
        except Exception as e:
            logger.exception(f"Error in get_transcript: {e}")
            return {
                "success": False,
                "message": f"Server error: {str(e)}",
                "error_code": "SERVER_ERROR"
            }
