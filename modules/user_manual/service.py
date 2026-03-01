import logging
import base64
from typing import Dict, Any
from .scraper import UserManualScraper

logger = logging.getLogger(__name__)

class UserManualService:
    """
    Business logic layer for the User Manual module.
    Responsible for orchestrating the scraper and formatting the response.
    """
    def __init__(self):
        self.scraper = UserManualScraper()

    def get_user_manual(self, cookies: Dict[str, str]) -> Dict[str, Any]:
        """
        Retrieves the User Manual PDF and encodes it as base64.
        
        Args:
            cookies: Session cookies required for OBS authentication.
            
        Returns:
            Dict containing the standard API response with the base64-encoded PDF.
        """
        if not cookies:
            return {
                "status": "error",
                "message": "Cookies are required"
            }

        # Initialize session with cookies
        self.scraper.initialize_session(cookies)
        
        # Fetch the PDF
        result = self.scraper.fetch_user_manual()
        
        if result.get("status") == "success":
            try:
                # Convert raw PDF bytes to Base64
                pdf_bytes = result["data"]
                pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
                
                logger.info(f"User Manual successfully encoded. Size: {len(pdf_bytes)} bytes")
                
                import datetime
                fetched_at = datetime.datetime.now().isoformat()
                
                return {
                    "status": "success",
                    "data": {
                        "pdf_base64": pdf_base64,
                        "size_bytes": len(pdf_bytes),
                        "fetched_at": fetched_at
                    },
                    "message": "Kullanım Kılavuzu başarıyla getirildi"
                }
            except Exception as e:
                logger.exception("Error encoding User Manual PDF")
                return {
                    "status": "error",
                    "message": f"PDF okuma hatası: {str(e)}"
                }
        else:
            return result
