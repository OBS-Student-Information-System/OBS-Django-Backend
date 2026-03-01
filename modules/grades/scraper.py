"""
Grades Scraper Module.
Handles fetching grades and available semesters.
"""
from bs4 import BeautifulSoup
from typing import Dict, Any, List, Optional
from core.tenant_config import get_config
from core.utils import create_session, get_hidden_inputs, check_session_expiry
from core.exceptions import SessionExpiredError
from core.logger import setup_logger
from modules.grades.parser import parse_grades_table

logger = setup_logger(__name__)

class GradesScraper:
    def __init__(self, session=None):
        self.session = session if session else create_session()
        self._cfg = get_config()

    def fetch_grades(self, term_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetch grades, optionally changing semester first.
        Args:
            term_id: ID of the semester to switch to (e.g. "20241").
        """
        try:
            grades_url = self._cfg.grades_url
            sel = self._cfg.selectors
            self.session.headers.update({"Referer": grades_url})
            
            logger.info(f"Fetching grades. Term ID: {term_id if term_id else 'Default'}")

            response = self.session.get(grades_url, timeout=self._cfg.scraper.timeout_seconds)
            check_session_expiry(response)
            if response.status_code != 200:
                logger.error(f"Grades page access failed. Status: {response.status_code}")
                return {"status": "error", "message": "Not listesine erişilemedi", "error_code": "GRADES_PAGE_ERROR"}

            # Change semester if requested
            if term_id:
                logger.info(f"Switching semester to {term_id}...")
                soup = BeautifulSoup(response.content, 'lxml')
                hidden_data = get_hidden_inputs(soup)
                
                hidden_data.update({
                    "__EVENTTARGET": sel["TERM_DROPDOWN"],
                    "__EVENTARGUMENT": "",
                    sel["TERM_DROPDOWN"]: term_id,
                })
                
                response = self.session.post(grades_url, data=hidden_data, timeout=self._cfg.scraper.timeout_seconds)
                check_session_expiry(response)
                logger.debug(f"Semester switch response status: {response.status_code}")

            # Parse
            grades_list = parse_grades_table(response.text)
            logger.info(f"Parsed {len(grades_list)} grades.")

            # Scrape GPA (AGNO)
            soup = BeautifulSoup(response.content, 'lxml')
            gpa = None
            gpa_elem = soup.find(id=sel.get("GPA_LABEL"))
            
            if gpa_elem and gpa_elem.text.strip():
                gpa = gpa_elem.text.strip().replace(',', '.') 

            return {
                "status": "success",
                "data": grades_list,
                "gpa": gpa, # Return GPA
                "message": f"{len(grades_list)} ders notu bulundu"
            }
            
        except SessionExpiredError:
            logger.warning("Session expired during grades fetch")
            return {"status": "error", "message": "Oturum süresi doldu", "error_code": "SESSION_EXPIRED"}
        except Exception as e:
            logger.exception("Exception in fetch_grades")
            return {"status": "error", "message": f"Parse hatası: {str(e)}", "error_code": "PARSE_ERROR"}

    def get_available_terms(self) -> Dict[str, Any]:
        """Get list of available semesters."""
        try:
            grades_url = self._cfg.grades_url
            sel = self._cfg.selectors
            self.session.headers.update({"Referer": grades_url})
            logger.info("Fetching available terms...")
            
            response = self.session.get(grades_url)
            check_session_expiry(response)
            
            if response.status_code != 200:
                logger.error(f"Terms page access failed. Status: {response.status_code}")
                return {"status": "error", "message": "Dönem listesi alınamadı", "error_code": "TERMS_PAGE_ERROR"}

            soup = BeautifulSoup(response.content, 'lxml')
            term_select = soup.find('select', id=sel["TERM_DROPDOWN"])
            
            if not term_select:
                logger.warning(f"Term dropdown ({sel['TERM_DROPDOWN']}) not found.")
                return {"status": "error", "message": "Dönem dropdown'ı bulunamadı", "error_code": "DROPDOWN_NOT_FOUND"}
            
            terms = []
            for option in term_select.find_all('option'):
                tid = option.get('value')
                tname = option.get_text(strip=True)
                if tid and tname:
                    terms.append({"term_id": tid, "term_name": tname})
            
            logger.info(f"Found {len(terms)} terms.")
            return {
                "status": "success",
                "data": terms,
                "message": f"{len(terms)} dönem bulundu"
            }

        except SessionExpiredError:
            logger.warning("Session expired during terms fetch")
            return {"status": "error", "message": "Oturum süresi doldu", "error_code": "SESSION_EXPIRED"}
        except Exception as e:
            logger.exception("Exception in get_available_terms")
            return {"status": "error", "message": f"Dönem parse hatası: {str(e)}", "error_code": "PARSE_ERROR"}
