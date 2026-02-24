import logging
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup

from core.interfaces import IScraper
from core.session import SessionManager
from core.config import PERSONAL_INFO_CALLER_URL, PERSONAL_INFO_FRAME_URL, DEFAULT_REFERER

logger = logging.getLogger(__name__)

class PersonalInfoScraper(IScraper):
    def __init__(self):
        self.session_manager = SessionManager()
        self.session = self.session_manager.get_session()
        self.caller_url = PERSONAL_INFO_CALLER_URL
        self.frame_url = PERSONAL_INFO_FRAME_URL

    def fetch_personal_info(self) -> Dict[str, Any]:
        """
        Fetches the Personal Information frame.
        We must first hit the caller.aspx?curPage=100 to initialize the page session,
        then fetch the actual frame ogr_ozluk.aspx.
        """
        if not self.session.cookies:
            logger.error("No cookies found, cannot fetch personal info.")
            return {"success": False, "message": "Oturum bulunamadı", "error_code": "NO_SESSION"}

        try:
            # Step 1: Hit Caller
            self.session.headers.update({
                'Referer': DEFAULT_REFERER,
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'same-origin',
            })
            
            logger.info("Accessing Personal Info caller page...")
            _ = self.session.get(self.caller_url, timeout=10)
            
            # Step 2: Fetch the actual Frame
            logger.info("Fetching Personal Info frame...")
            self.session.headers.update({
                'Referer': self.caller_url,
                'Sec-Fetch-Dest': 'iframe'
            })
            
            response = self.session.get(self.frame_url, timeout=10)
            
            if response.status_code != 200:
                logger.error(f"Failed to fetch Personal Info frame. Status code: {response.status_code}")
                return {"success": False, "message": "Özlük Bilgileri sayfası alınamadı", "error_code": "P_INFO_FETCH_FAILED"}
                
            # Check for redirect to login (Session expired)
            if "login.aspx" in response.url.lower():
                 logger.warning("Session expired, redirected to login.")
                 return {"success": False, "message": "Oturum süresi doldu", "error_code": "SESSION_EXPIRED"}
                 
            return self._parse_personal_info(response.text)

        except Exception as e:
            logger.exception("Error during Personal Info fetch")
            return {"success": False, "message": f"Bağlantı hatası: {str(e)}", "error_code": "P_INFO_SCRAPE_ERROR"}

    def _parse_personal_info(self, html: str) -> Dict[str, Any]:
        """
        Parses the Personal Info HTML and extracts relevant fields based on the provided IDs.
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        # Helper to extract value from input
        def get_input_val(ele_id: str) -> str:
            element = soup.find('input', id=ele_id)
            return element.get('value', '').strip() if element else ""
            
        # Helper to extract selected option text from select
        def get_select_text(ele_id: str) -> str:
            select = soup.find('select', id=ele_id)
            if select:
                selected = select.find('option', selected=True)
                if selected and selected.text.strip() and selected.text.strip().lower() != "seçiniz":
                    return selected.text.strip()
            return ""

        try:
            data = {
                "contact": {
                    "phone1": get_input_val("txtCep1"),
                    "phone2": get_input_val("txtCep2"),
                    "email1": get_input_val("txtEposta1"),
                    "email2": get_input_val("txtEposta2"),
                },
                "address": {
                    "family": {
                        "address": get_input_val("txtAileAdres"),
                        "city": get_select_text("cmbAileIl"),
                        "district": get_select_text("cmbAileIlce"),
                        "postal_code": get_input_val("txtAilePostaKod"),
                        "phone": get_input_val("txtAileTelefon")
                    },
                    "residential": {
                        "address": get_input_val("txtIkmAdres"),
                        "city": get_select_text("cmbIkmIl"),
                        "district": get_select_text("cmbIkmIlce"),
                        "postal_code": get_input_val("txtIkmPostaKod"),
                        "phone": get_input_val("txtIkmTel")
                    }
                },
                "financial": {
                    "bank_name": get_input_val("txtBankaAdi"),
                    "branch_name": get_input_val("txtBankaSubeAdi"),
                    "iban": get_input_val("txtBankaIBAN"),
                    "account_holder": get_input_val("txtHesapSahibiAdSoyad")
                }
            }
            logger.info("Successfully parsed Personal Information.")
            return {"success": True, "data": data}
            
        except Exception as e:
            logger.exception("Error parsing Personal Info HTML")
            return {"success": False, "message": "HTML ayrıştırma hatası", "error_code": "P_INFO_PARSE_ERROR"}
