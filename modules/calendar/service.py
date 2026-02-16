import logging
from typing import List, Dict, Any
from .scraper import CalendarScraper

logger = logging.getLogger(__name__)

import requests

class CalendarService:
    def __init__(self):
        self.scraper = CalendarScraper()
        self.calendar_url = "https://obs.ozal.edu.tr/oibs/std/st_akademik_takvim.aspx"

    def get_calendar(self, cookies: Dict[str, str] = None) -> List[Dict[str, Any]]:
        """Fetches academic calendar events from OBS.
        
        Args:
            cookies: Optional authentication cookies for session validation.
            
        Returns:
            List of calendar event dictionaries containing title, start_date, end_date.
            
        Raises:
            Exception: If session is invalid, calendar cannot be parsed, or network fails.
        """
        try:
            # Create a session to persist cookies across requests
            session = requests.Session()
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Referer': 'https://obs.ozal.edu.tr/oibs/std/main_body.aspx',
                'Origin': 'https://obs.ozal.edu.tr',
            }
            
            session.headers.update(headers)

            if cookies:
                session.cookies.update(cookies)

            # 1. Visit main_body first to validate/refresh the session
            # This is crucial because accessing nested ASP.NET pages often requires a fresh referer context/cookies
            try:
                session.get(
                    "https://obs.ozal.edu.tr/oibs/std/main_body.aspx", 
                    timeout=5
                )
            except Exception as e:
                logger.warning(f"Main body refresh failed: {e}")
                # Continue anyway, initial cookies might still be valid

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
