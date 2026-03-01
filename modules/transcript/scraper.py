"""
Transcript Scraper Module.
Handles fetching academic transcript PDF from OBS.
"""
import requests
from typing import Dict, Any
from core.logger import setup_logger
from core.utils import create_session
from core.tenant_config import get_config

logger = setup_logger(__name__)


class TranscriptScraper:
    """Scraper for fetching student transcript PDF."""
    
    def __init__(self, session: requests.Session = None):
        """Initialize scraper with optional session.
        
        Args:
            session: Optional requests session. Creates new one if not provided.
        """
        self.session = session if session else create_session()
        cfg = get_config()
        self.transcript_url = cfg.transcript_url
        self._default_referer = cfg.default_referer
    
    def fetch_transcript(self) -> Dict[str, Any]:
        """Fetches transcript PDF from OBS.
        
        Returns:
            Dict containing PDF binary data or error information:
            {
                "success": bool,
                "data": bytes,  # PDF binary content
                "error": str    # Error message if failed
            }
            
        Raises:
            Exception: If network request fails or session is invalid.
        """
        try:
            logger.info(f"Fetching transcript from: {self.transcript_url}")
            
            # Set headers to mimic browser
            self.session.headers.update({
                'Referer': self._default_referer,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'same-origin',
            })
            
            # Make request - allow redirects to follow to actual PDF
            response = self.session.get(
                self.transcript_url,
                timeout=15,
                allow_redirects=True
            )
            
            if response.status_code == 200:
                # Check if we got a PDF
                content_type = response.headers.get('Content-Type', '').lower()
                
                if 'pdf' in content_type or response.content.startswith(b'%PDF'):
                    logger.info(f"Successfully fetched PDF. Size: {len(response.content)} bytes")
                    return {
                        "status": "success",
                        "data": response.content
                    }
                else:
                    # Might be redirected to error page
                    response_text = response.text.lower()
                    
                    if 'login.aspx' in response.url.lower() or 'yönlendirme' in response_text:
                        logger.error("Session expired - redirected to login")
                        return {
                            "status": "error",
                            "error": "Session expired. Please re-login."
                        }
                    
                    if 'deferror.aspx' in response.url.lower():
                        logger.error("Server returned error page")
                        return {
                            "status": "error",
                            "error": "Server error occurred while fetching transcript."
                        }
                    
                    logger.warning(f"Response is not a PDF. Content-Type: {content_type}")
                    return {
                        "status": "error",
                        "error": "Received invalid response from server."
                    }
            else:
                logger.error(f"Failed to fetch transcript. Status: {response.status_code}")
                return {
                    "status": "error",
                    "error": f"Server returned status code: {response.status_code}"
                }
                
        except requests.exceptions.Timeout:
            logger.error("Request timed out")
            return {
                "status": "error",
                "error": "Request timed out. Please try again."
            }
        except Exception as e:
            logger.exception(f"Error fetching transcript: {e}")
            return {
                "status": "error",
                "error": f"Error: {str(e)}"
            }
