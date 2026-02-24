import logging
from typing import Dict, Any, Optional
from core.utils import create_session
from bs4 import BeautifulSoup
from core.config import PERSONAL_INFO_CALLER_URL, PERSONAL_INFO_FRAME_URL, DEFAULT_REFERER

logger = logging.getLogger(__name__)

class PersonalInfoScraper:
    def __init__(self, session: Optional[Any] = None):
        self.session = session if session else create_session()
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
                    "phone3": get_input_val("txtCep3"),
                    "email1": get_input_val("txtEposta1"),
                    "email2": get_input_val("txtEposta2"),
                    "web": get_input_val("txtWeb"),
                    "social_media": get_input_val("txtMsn"),
                    "orcid": get_input_val("txtORCID")
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
                    "branch_code": get_input_val("txtBankaSubeKod"),
                    "account_number": get_input_val("txtBankaHesapNo"),
                    "iban": get_input_val("txtBankaIBAN"),
                    "account_holder": get_input_val("txtHesapSahibiAdSoyad")
                }
            }
            logger.info("Successfully parsed Personal Information.")
            return {"success": True, "data": data}
            
        except Exception as e:
            logger.exception("Error parsing Personal Info HTML")
            return {"success": False, "message": "HTML ayrıştırma hatası", "error_code": "P_INFO_PARSE_ERROR"}

    def update_personal_info(self, new_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Updates Personal Information on the OBS system.
        """
        if not self.session.cookies:
            logger.error("No cookies found, cannot update personal info.")
            return {"success": False, "message": "Oturum bulunamadı", "error_code": "NO_SESSION"}

        try:
            self.session.headers.update({
                'Referer': DEFAULT_REFERER,
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'same-origin',
            })
            _ = self.session.get(self.caller_url, timeout=10)
            
            self.session.headers.update({
                'Referer': self.caller_url,
                'Sec-Fetch-Dest': 'iframe'
            })
            response = self.session.get(self.frame_url, timeout=10)
            if response.status_code != 200:
                return {"success": False, "message": "Sayfa alınamadı", "error_code": "FETCH_FAILED"}
                
            soup = BeautifulSoup(response.text, 'html.parser')
            form_data = {}
            for input_tag in soup.find_all('input'):
                if input_tag.get('name'):
                    form_data[input_tag.get('name')] = input_tag.get('value', '')
                    
            for select_tag in soup.find_all('select'):
                if select_tag.get('name'):
                    selected_option = select_tag.find('option', selected=True)
                    if selected_option:
                        form_data[select_tag.get('name')] = selected_option.get('value', '')
                    else:
                        form_data[select_tag.get('name')] = ''
                        
            field_map = {
                "phone1": "txtCep1",
                "phone2": "txtCep2",
                "phone3": "txtCep3",
                "email1": "txtEposta1",
                "email2": "txtEposta2",
                "web": "txtWeb",
                "social_media": "txtMsn",
                "orcid": "txtORCID",
                
                "family_address": "txtAileAdres",
                "family_city": "cmbAileIl",
                "family_district": "cmbAileIlce",
                "family_postal_code": "txtAilePostaKod",
                "family_phone": "txtAileTelefon",
                
                "residential_address": "txtIkmAdres",
                "residential_city": "cmbIkmIl",
                "residential_district": "cmbIkmIlce",
                "residential_postal_code": "txtIkmPostaKod",
                "residential_phone": "txtIkmTel",
                
                "bank_name": "txtBankaAdi",
                "branch_name": "txtBankaSubeAdi",
                "branch_code": "txtBankaSubeKod",
                "account_number": "txtBankaHesapNo",
                "iban": "txtBankaIBAN",
                "account_holder": "txtHesapSahibiAdSoyad",
            }

            for key, val in new_data.items():
                if key in field_map:
                    form_data[field_map[key]] = val
                    
            form_data['__EVENTTARGET'] = 'btnKaydet'
            form_data['__EVENTARGUMENT'] = ''
            
            self.session.headers.update({
                'Referer': self.frame_url,
                'Content-Type': 'application/x-www-form-urlencoded',
                'Sec-Fetch-Dest': 'iframe',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-origin',
            })
            
            post_response = self.session.post(self.frame_url, data=form_data, timeout=10)
            
            if post_response.status_code != 200:
                logger.error(f"Failed to post Personal Info update. Status code: {post_response.status_code}")
                return {"success": False, "message": "Güncelleme isteği başarısız oldu", "error_code": "P_INFO_UPDATE_FAILED"}
                
            return {"success": True, "message": "Bilgiler başarıyla güncellendi."}

        except Exception as e:
            logger.exception("Error during Personal Info update")
            return {"success": False, "message": f"Bağlantı hatası: {str(e)}", "error_code": "P_INFO_UPDATE_ERROR"}
