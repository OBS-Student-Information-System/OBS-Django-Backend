import logging
import requests
from typing import Dict, Any
from core.tenant_config import get_config

logger = logging.getLogger(__name__)

class UserManualScraper:
    """
    Scraper layer for the User Manual module.
    Responsible for making the HTTP request to fetch the PDF and handling redirects.
    """
    def __init__(self):
        self.session = requests.Session()
        cfg = get_config()
        self.user_manual_url = cfg.user_manual_url
        self._default_referer = cfg.default_referer
        self._default_headers = cfg.default_headers
        
    def initialize_session(self, cookies: Dict[str, str]):
        """Initializes the request session with provided cookies."""
        self.session.cookies.update(cookies)
        self.session.headers.update(self._default_headers)
        
    def fetch_user_manual(self) -> Dict[str, Any]:
        """
        Fetches the User Manual PDF document.
        Handles redirects automatically like a browser.
        
        Returns:
            Dict containing success status, raw PDF bytes (if successful), and a message.
        """
        try:
            # Add specific headers required for downloading files
            self.session.headers.update({
                'Referer': self._default_referer,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'same-origin',
            })
            
            logger.info("Fetching User Manual PDF...")
            
            # Allow redirects as the caller.aspx typically redirects to the actual PDF
            response = self.session.get(
                self.user_manual_url,
                timeout=15,
                allow_redirects=True
            )
            
            # Check for session expiration (redirect to login page)
            if "login.aspx" in response.url.lower():
                logger.warning("Session expired during User Manual fetch. Redirected to login.")
                return {
                    "status": "error",
                    "message": "Oturum süresi doldu, lütfen tekrar giriş yapın."
                }
                
            if response.status_code == 200:
                # IMPORTANT: Since it's a PDF, we need to ensure the response is actually PDF content
                content_type = response.headers.get('Content-Type', '').lower()
                
                # Check either the Content-Type header or the magic bytes (%PDF)
                if 'pdf' in content_type or response.content.startswith(b'%PDF'):
                    pdf_size = len(response.content)
                    logger.debug(f"Successfully downloaded PDF. Size: {pdf_size} bytes")
                    
                    if pdf_size < 1000:
                        logger.warning(f"Downloaded PDF seems suspiciously small: {pdf_size} bytes")
                    
                    return {
                        "status": "success",
                        "data": response.content,
                        "message": "Success"
                    }
                else:
                    logger.error(f"Response is not a PDF. Content-Type: {content_type}")
                    return {
                        "status": "error",
                        "message": "Beklenen belge formatı alınamadı (PDF değil)."
                    }
            else:
                logger.error(f"Failed to fetch User Manual. Status Code: {response.status_code}")
                return {
                    "status": "error",
                    "message": f"Belge sunucusundan hata alındı (Kod: {response.status_code})"
                }
                
        except requests.exceptions.Timeout:
            logger.error("User Manual fetch timed out")
            return {
                "status": "error",
                "message": "Sunucu yanıt vermedi (Zaman aşımı)."
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Request Error fetching User Manual: {str(e)}")
            return {
                "status": "error",
                "message": "Belge indirilirken bir bağlantı hatası oluştu."
            }
        except Exception as e:
            logger.exception("Unexpected error fetching User Manual")
            return {
                "status": "error",
                "message": f"Beklenmeyen bir hata oluştu: {str(e)}"
            }
