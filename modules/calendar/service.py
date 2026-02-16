import logging
import requests
from typing import List, Dict, Any
from .scraper import CalendarScraper
from core.utils import create_session

logger = logging.getLogger(__name__)

class CalendarService:
    def __init__(self):
        self.scraper = CalendarScraper()
        self.calendar_url = "https://obs.ozal.edu.tr/oibs/std/st_akademik_takvim.aspx"

    def get_calendar(self, cookies: Dict[str, str] = None) -> List[Dict[str, Any]]:
        """Fetches academic calendar events from OBS."""
        try:
            # internal session setup
            session = create_session()
            
            if cookies:
                session.cookies.update(cookies)

            # 1. Fetch Main Body to find the dynamic calendar link
            # OBS systems often change URLs or use session-based params in links
            logger.info("Fetching main_body to discover calendar URL...")
            main_body_url = "https://obs.ozal.edu.tr/oibs/std/main_body.aspx"
            
            try:
                mb_response = session.get(main_body_url, timeout=10)
            except Exception as e:
                logger.error(f"Failed to fetch main_body: {e}")
                raise Exception("Ana sayfaya erişilemedi. Bağlantınızı kontrol edin.")

            if mb_response.status_code != 200:
                logger.error(f"Main body status code: {mb_response.status_code}")
                raise Exception("Ana sayfaya erişilemedi. Session geçersiz olabilir.")

            # 2. Parse Main Body to find "Akademik Takvim" link
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(mb_response.text, 'lxml')
            
            calendar_link = None
            # Strategy 1: Look for text "Akademik Takvim"
            for a in soup.find_all('a'):
                if a.get_text() and "Akademik Takvim" in a.get_text():
                    calendar_link = a.get('href')
                    logger.info(f"Found calendar link by text: {calendar_link}")
                    break
            
            # Strategy 2: Look for href containing "takvim"
            if not calendar_link:
                for a in soup.find_all('a'):
                    href = a.get('href')
                    if href and "takvim" in href.lower() and "aspx" in href.lower():
                        calendar_link = href
                        logger.info(f"Found calendar link by href: {calendar_link}")
                        break

            if not calendar_link:
                # Fallback to hardcoded URL if not found (maybe it's in a sub-menu loaded via JS)
                logger.warning("Could not find dynamic calendar link. Trying fallback...")
                target_url = self.calendar_url
            else:
                # Construct full URL
                from core.utils import fix_url
                target_url = fix_url(calendar_link)

            logger.info(f"Navigating to calendar URL: {target_url}")

            # 3. Fetch Calendar with correct Referer
            session.headers.update({'Referer': main_body_url})
            response = session.get(target_url, timeout=10)
            
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
