from typing import List, Dict, Any
from modules.calendar.parser import parse_calendar_table

class CalendarScraper:
    def parse_calendar_table(self, html_content: str) -> List[Dict[str, Any]]:
        return parse_calendar_table(html_content)
