import logging
import requests
from typing import List, Dict, Any
from .scraper import CalendarScraper
from core.utils import create_session

logger = logging.getLogger(__name__)

class CalendarService:
    def __init__(self):
        self.scraper = CalendarScraper()
        # Browser logs confirm this is the entry point
        self.calendar_url = "https://obs.ozal.edu.tr/oibs/std/caller.aspx?curPage=101"

    def get_calendar(self, cookies: Dict[str, str] = None) -> List[Dict[str, Any]]:
        """Fetches academic calendar events from OBS."""
        try:
            # internal session setup
            session = create_session()
            
            if cookies:
                session.cookies.update(cookies)

            # Use main_body as referer. 
            # In browser log, caller.aspx is called after main_body.
            session.headers.update({
                'Referer': 'https://obs.ozal.edu.tr/oibs/std/main_body.aspx'
            })
            
            logger.info(f"Navigating to calendar via caller: {self.calendar_url}")

            # 2. Fetch Calendar
            response = session.get(self.calendar_url, timeout=10)
            
            # Result validation
            if response.status_code == 200:
                # Check for redirects masquerading as 200 OK
                if "Yönlendirme" in response.text or "Redirect" in response.text or "frmLogin" in response.text:
                     # Log the response snippet for debugging
                     snippet = response.text[:500].replace('\n', ' ')
                     logger.warning(f"Redirect/Login detected in calendar response: {snippet}")
                     raise Exception("Session invalid or redirected by server. Please re-login.")
                
                # Check for 404 in content
                if "Sayfa Bulunamadı" in response.text or "404" in response.text:
                     logger.error("Calendar page returned 404 text.")
                     raise Exception("Akademik takvim sayfasına ulaşılamadı (404).")

                events = self.scraper.parse_calendar_table(response.text)
                if events:
                    return events
                else:
                    raise Exception("Calendar table could not be parsed or is empty.")
            else:
                raise Exception(f"Failed to fetch calendar. Status Code: {response.status_code}")
            
        except Exception as e:
            logger.error(f"Error fetching calendar: {e}")
            raise e
