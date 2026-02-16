import logging
import requests
from typing import List, Dict, Any
from .scraper import CalendarScraper
from core.utils import create_session

logger = logging.getLogger(__name__)

class CalendarService:
    def __init__(self):
        self.scraper = CalendarScraper()
        # Browser flow similar to Schedule: caller.aspx?curPage=101 -> st_akademik_takvim.aspx
        self.calendar_url = "https://obs.ozal.edu.tr/oibs/std/caller.aspx?curPage=101"
        # Referer should be index.aspx (the dashboard) as seen in browser/Schedule module
        self.dummy_referer = "https://obs.ozal.edu.tr/oibs/std/index.aspx?curOp=0"

    def get_calendar(self, cookies: Dict[str, str] = None) -> List[Dict[str, Any]]:
        """Fetches academic calendar events from OBS."""
        try:
            # internal session setup
            session = create_session()
            
            if cookies:
                session.cookies.update(cookies)
                logger.debug(f"CalendarService using cookies: {list(session.cookies.get_dict().keys())}")

            # Set headers to match browser/Schedule module exactly
            # This is crucial for iframe-based navigation in OBS
            session.headers.update({
                'Referer': self.dummy_referer,
                'Sec-Fetch-Dest': 'iframe',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'same-origin',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1',
            })
            
            logger.info(f"Navigating to calendar via caller: {self.calendar_url}")

            # 2. Fetch Calendar with redirects allowed
            response = session.get(self.calendar_url, timeout=15, allow_redirects=True)
            
            # Result validation
            if response.status_code == 200:
                current_url = response.url.lower()
                response_text = response.text

                # Check for redirects masquerading as 200 OK
                if "login.aspx" in current_url or "yönlendirme" in response_text.lower() or "redirect" in response_text.lower() or "frmlogin" in response_text.lower():
                     snippet = response_text[:500].replace('\n', ' ')
                     logger.warning(f"Redirect/Login detected in calendar response: {snippet}")
                     raise Exception("Session invalid or redirected by server. Please re-login.")
                
                # Check for 404 in content
                if "404" in current_url or "sayfa bulunamadı" in response_text.lower():
                     logger.error("Calendar page returned 404.")
                     raise Exception("Akademik takvim sayfasına ulaşılamadı (404).")

                events = self.scraper.parse_calendar_table(response_text)
                if events:
                    return events
                else:
                    logger.warning("Calendar table parsed but empty.")
                    # Return empty list instead of error if table exists but is empty
                    if "grd" in response_text.lower() or "table" in response_text.lower():
                        return []
                    else:
                        raise Exception("Calendar table structure changed or not found.")
            else:
                raise Exception(f"Failed to fetch calendar. Status Code: {response.status_code}")
            
        except Exception as e:
            logger.error(f"Error fetching calendar: {e}")
            raise e
