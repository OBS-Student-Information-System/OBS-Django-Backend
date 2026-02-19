import requests
from typing import Dict, List, Any
import logging
from bs4 import BeautifulSoup
from .scraper import ScheduleScraper
from core.utils import create_session
from core.config import SCHEDULE_URL, DEFAULT_REFERER

logger = logging.getLogger(__name__)

class ScheduleService:
    """Service for fetching and managing weekly class schedules.
    
    Handles session management, cookie updates, and schedule data retrieval
    from the university OBS system via web scraping.
    """
    def __init__(self):
        self.scraper = ScheduleScraper()
        self.session = create_session()
        # Browser flow: std_time_table.aspx → 302 → caller.aspx?curPage=108 → actual schedule
        self.schedule_url = SCHEDULE_URL
        # Referer should be index.aspx (the dashboard) as seen in browser
        self.dummy_referer = DEFAULT_REFERER

    def update_session_cookies(self, cookies: Dict[str, str]):
        """Updates the session with provided cookies."""
        if cookies:
            self.session.cookies.update(cookies)

    def get_schedule(self, cookies: Dict[str, str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """Fetches weekly class schedule from OBS.
        
        Args:
            cookies: Optional authentication cookies. If not provided, uses session cookies.
            
        Returns:
            Dict mapping day numbers ("1"-"5") to lists of lesson dictionaries.
            
        Raises:
            Exception: If session is expired, server returns error pages, or network fails.
        """
        try:
            # If cookies provided in method call, update session (backward compatibility)
            if cookies:
                self.update_session_cookies(cookies)

            # Log cookie keys
            if self.session.cookies:
                logger.debug(f"ScheduleService using cookies: {list(self.session.cookies.get_dict().keys())}")
            else:
                logger.warning("ScheduleService has NO cookies in session.")

            # Set headers to match browser exactly (from Network tab)
            self.session.headers.update({
                'Referer': self.dummy_referer,
                # Remove Origin - browser doesn't send it for GET requests
                'Sec-Fetch-Dest': 'iframe',  # Browser uses iframe, not document
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'same-origin',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1',
            })

            logger.info(f"Fetching schedule via dispatcher: {self.schedule_url}")
            # Allow redirects so caller.aspx can route us to the actual schedule page
            response = self.session.get(self.schedule_url, timeout=10, allow_redirects=True)

            if response.status_code == 200:
                current_url = response.url.lower()
                response_text = response.text

                # Check for known error pages
                if "login.aspx" in current_url or "yönlendirme" in response_text or "redirect" in response_text:
                    logger.error("Backend detected redirect to login.aspx.")
                    raise Exception("Session expired or invalid.")
                
                if "deferror.aspx" in current_url:
                    logger.error("Backend detected redirect to DefError.aspx.")
                    # Log the error content to see if there's a specific message
                    error_soup = BeautifulSoup(response_text, 'html.parser')
                    error_msg = error_soup.get_text().strip().replace('\n', ' ')
                    logger.error(f"DefError Content: {error_msg[:200]}...") # Log first 200 chars
                    raise Exception("Server returned DefError. The session might be invalid or the page requires specific navigation.")

                if "404.aspx" in current_url:
                    logger.error("Backend detected redirect to 404.aspx.")
                    raise Exception("Server returned 404 Error.")
                
                logger.info(f"Schedule response length: {len(response_text)}")
                
                schedule = self.scraper.parse_schedule(response_text)
                return schedule
            else:
                logger.error(f"Failed to fetch schedule. Status: {response.status_code}")
                raise Exception(f"Failed to fetch schedule. Status: {response.status_code}")

        except Exception as e:
            logger.error(f"Error fetching schedule: {e}")
            raise e
