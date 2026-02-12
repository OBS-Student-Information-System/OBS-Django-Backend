import requests
from typing import List, Dict, Any
from .scraper import CalendarScraper

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
            # Attempt to fetch the live page
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Referer': 'https://obs.ozal.edu.tr/oibs/std/main_body.aspx', # Mimic coming from dashboard
                'Origin': 'https://obs.ozal.edu.tr',
            }
            # Use cookies if provided (likely needed for auth)
            # WORKAROUND: Visit main_body first to "refresh" or "validate" the session on the server side
            # This is often needed in ASP.NET WebForms to set the correct Referer/Context
            try:
                requests.get(
                    "https://obs.ozal.edu.tr/oibs/std/main_body.aspx", 
                    headers=headers, 
                    cookies=cookies, 
                    timeout=5
                )
            except:
                pass # Ignore if this fails, just trying to help session

            response = requests.get(self.calendar_url, headers=headers, cookies=cookies, timeout=10)
            
            # Result validation
            if response.status_code == 200:
                events = self.scraper.parse_calendar_table(response.text)
                if events:
                    return events
                else:
                    # Check if it is a redirect page
                    if "Yönlendirme" in response.text or "Redirect" in response.text:
                         raise Exception("Session invalid or redirected by server. Please re-login.")
                    
                    raise Exception("Calendar table could not be parsed or is empty.")
            else:
                raise Exception(f"Failed to fetch calendar. Status Code: {response.status_code}")
            
        except Exception as e:
            logger.error(f"Error fetching calendar: {e}")
            raise e # Fail loudly as requested
