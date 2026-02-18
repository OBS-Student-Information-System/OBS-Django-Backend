"""
Grades Scraper Module.
Handles fetching grades and available semesters.
"""
from bs4 import BeautifulSoup
from typing import Dict, Any, List, Optional
from core.config import GRADES_URL, SELECTORS
from core.utils import create_session, get_hidden_inputs
from core.logger import setup_logger
from modules.grades.parser import parse_grades_table

logger = setup_logger(__name__)

class GradesScraper:
    def __init__(self, session=None):
        self.session = session if session else create_session()

    def fetch_grades(self, term_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetch grades, optionally changing semester first.
        Args:
            term_id: ID of the semester to switch to (e.g. "20241").
        """
        try:
            # Important: OBS checks Referer for internal navigation security
            self.session.headers.update({"Referer": GRADES_URL})
            
            logger.info(f"Fetching grades. Term ID: {term_id if term_id else 'Default'}")

            # Initial GET to load page and ViewState
            response = self.session.get(GRADES_URL, timeout=10)
            if response.status_code != 200:
                logger.error(f"Grades page access failed. Status: {response.status_code}")
                return {"success": False, "message": "Not listesine erişilemedi", "error_code": "GRADES_PAGE_ERROR"}

            # Change semester if requested
            if term_id:
                logger.info(f"Switching semester to {term_id}...")
                soup = BeautifulSoup(response.content, 'lxml')
                hidden_data = get_hidden_inputs(soup)
                
                hidden_data.update({
                    "__EVENTTARGET": SELECTORS["TERM_DROPDOWN"],
                    "__EVENTARGUMENT": "",
                    SELECTORS["TERM_DROPDOWN"]: term_id
                })
                
                response = self.session.post(GRADES_URL, data=hidden_data, timeout=10)
                logger.debug(f"Semester switch response status: {response.status_code}")

            # Parse
            grades_list = parse_grades_table(response.text)
            logger.info(f"Parsed {len(grades_list)} grades.")

            # Scrape GPA (AGNO)
            soup = BeautifulSoup(response.content, 'lxml')
            gpa = None
            gpa_elem = soup.find(id=SELECTORS.get("GPA_LABEL"))
            
            if gpa_elem and gpa_elem.text.strip():
                gpa = gpa_elem.text.strip().replace(',', '.') 

            return {
                "success": True,
                "data": grades_list,
                "gpa": gpa, # Return GPA
                "message": f"{len(grades_list)} ders notu bulundu"
            }
            
        except Exception as e:
            logger.exception("Exception in fetch_grades")
            return {"success": False, "message": f"Parse hatası: {str(e)}", "error_code": "PARSE_ERROR"}

    def get_available_terms(self) -> Dict[str, Any]:
        """Get list of available semesters."""
        try:
            self.session.headers.update({"Referer": GRADES_URL})
            logger.info("Fetching available terms...")
            
            response = self.session.get(GRADES_URL)
            
            if response.status_code != 200:
                logger.error(f"Terms page access failed. Status: {response.status_code}")
                return {"success": False, "message": "Dönem listesi alınamadı", "error_code": "TERMS_PAGE_ERROR"}

            soup = BeautifulSoup(response.content, 'lxml')
            term_select = soup.find('select', id=SELECTORS["TERM_DROPDOWN"])
            
            if not term_select:
                logger.warning(f"Term dropdown ({SELECTORS['TERM_DROPDOWN']}) not found.")
                return {"success": False, "message": "Dönem dropdown'ı bulunamadı", "error_code": "DROPDOWN_NOT_FOUND"}
            
            terms = []
            for option in term_select.find_all('option'):
                tid = option.get('value')
                tname = option.get_text(strip=True)
                if tid and tname:
                    terms.append({"term_id": tid, "term_name": tname})
            
            logger.info(f"Found {len(terms)} terms.")
            return {
                "success": True,
                "data": terms,
                "message": f"{len(terms)} dönem bulundu"
            }

        except Exception as e:
            logger.exception("Exception in get_available_terms")
            return {"success": False, "message": f"Dönem parse hatası: {str(e)}", "error_code": "PARSE_ERROR"}
