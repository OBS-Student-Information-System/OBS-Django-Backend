"""
Schedule Parser Module.
Handles parsing of weekly schedule HTML tables.
"""
from bs4 import BeautifulSoup
from typing import List, Dict, Any
import re
import logging

logger = logging.getLogger(__name__)

def parse_schedule_table(html_content: str) -> Dict[str, List[Dict[str, Any]]]:
    """
    Parses the schedule HTML and returns a dictionary of days (1-7).
    1: Monday, ..., 7: Sunday
    """
    soup = BeautifulSoup(html_content, 'lxml')
    schedule = {}

    day_map = {
        "grd0": "1", # Monday
        "grd1": "2", # Tuesday
        "grd2": "3", # Wednesday
        "grd3": "4", # Thursday
        "grd4": "5", # Friday
        "grd5": "6", # Saturday
        "grd6": "7", # Sunday
    }

    for grid_id, day_key in day_map.items():
        table = soup.find(id=grid_id)
        if not table:
            continue
        
        day_lessons = []
        rows = table.find_all('tr')
        
        # Skip header row
        if len(rows) < 2:
            continue

        for row in rows[1:]:
            cells = row.find_all('td')
            if len(cells) < 5:
                continue
            
            if "Bulunamadı" in row.text:
                continue

            try:
                time_range = cells[0].text.strip()
                course_code = cells[1].text.strip()
                course_name = cells[2].text.strip()
                location = cells[3].text.strip()
                lecturer = cells[4].text.strip()
            except Exception as e:
                logger.error(f"Error parsing row cells in {grid_id}: {e}")
                continue

            location_clean = re.sub(r'\[.*?\]', '', location).strip()

            is_practice = False
            style_str = row.get('style', '') or ''
            if 'DarkGreen' in style_str:
                is_practice = True
            else:
                cell_style = cells[0].get('style', '') or ''
                if 'DarkGreen' in cell_style:
                    is_practice = True

            lesson = {
                "time": time_range,
                "code": course_code,
                "name": course_name,
                "location": location_clean,
                "lecturer": lecturer,
                "is_practice": is_practice
            }
            
            day_lessons.append(lesson)
        
        if day_lessons:
            schedule[day_key] = day_lessons

    return schedule
