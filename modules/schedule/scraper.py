from bs4 import BeautifulSoup
from typing import List, Dict, Any
from bs4 import BeautifulSoup
from typing import List, Dict, Any
import logging
from modules.schedule.parser import parse_schedule_table

logger = logging.getLogger(__name__)

class ScheduleScraper:
    def parse_schedule(self, html_content: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Parses the schedule HTML and returns a dictionary of days (1-7).
        1: Monday, ..., 7: Sunday
        """
        return parse_schedule_table(html_content)
