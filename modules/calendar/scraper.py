from bs4 import BeautifulSoup
from typing import List, Dict, Any

class CalendarScraper:
    def parse_calendar_table(self, html_content: str) -> List[Dict[str, Any]]:
        soup = BeautifulSoup(html_content, 'lxml')
        events = []
        
        table = soup.find('table', {'id': 'grd'})
        if not table:
            return []

        # Iterate over rows, skipping header (th)
        rows = table.find_all('tr')
        for row in rows:
            # Skip header row
            if row.find('th'):
                continue
                
            cells = row.find_all('td')
            if len(cells) < 3:
                continue
                
            # Column 0: Name (text inside td)
            name = cells[0].get_text(strip=True)
            
            # Column 1: Start Date (span id starts with grd_lblBasTar)
            start_date_span = cells[1].find('span', id=lambda x: x and x.startswith('grd_lblBasTar'))
            start_date = start_date_span.get_text(strip=True) if start_date_span else ""
            
            # Column 2: End Date (span id starts with grd_lblBitTar)
            end_date_span = cells[2].find('span', id=lambda x: x and x.startswith('grd_lblBitTar'))
            end_date = end_date_span.get_text(strip=True) if end_date_span else ""
            
            if name and start_date:
                events.append({
                    "name": name,
                    "start_date": start_date,
                    "end_date": end_date
                })
        
        return events
