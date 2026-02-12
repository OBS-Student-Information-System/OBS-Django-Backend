from bs4 import BeautifulSoup
from typing import List, Dict, Any
import re
import logging

logger = logging.getLogger(__name__)

class ScheduleScraper:
    def parse_schedule(self, html_content: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Parses the schedule HTML and returns a dictionary of days (1-7).
        1: Monday, ..., 7: Sunday
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        schedule = {}

        # Days mapping based on grid IDs in the provided HTML
        # grd0: Pazartesi, grd1: Salı, grd2: Çarşamba, grd3: Perşembe, grd4: Cuma
        # grd5: Cumartesi, grd6: Pazar (Assume pattern continues if they exist)
        
        day_map = {
            "grd0": "1", # Monday
            "grd1": "2", # Tuesday
            "grd2": "3", # Wednesday
            "grd3": "4", # Thursday
            "grd4": "5", # Friday
            "grd5": "6", # Saturday
            "grd6": "7", # Sunday
        }

        logger.info(f"DEBUG: Parsing schedule HTML length: {len(html_content)}")

        for grid_id, day_key in day_map.items():
            table = soup.find(id=grid_id)
            if not table:
                logger.warning(f"DEBUG: Table {grid_id} not found.")
                continue
            
            logger.info(f"DEBUG: Found table {grid_id} for day {day_key}")

            day_lessons = []
            rows = table.find_all('tr')
            
            logger.info(f"DEBUG: Table {grid_id} has {len(rows)} rows.")

            
            # Skip header row
            if len(rows) < 2:
                logger.debug(f"Skipping table {grid_id} (not enough rows)")
                continue

            for row in rows[1:]:
                cells = row.find_all('td')
                if len(cells) < 5:
                    logger.debug(f"Skipping row in {grid_id} (not enough cells: {len(cells)})")
                    continue
                
                # Check for "Tanımlı Ders Programı Bulunamadı"
                if "Bulunamadı" in row.text:
                    logger.info(f"Table {grid_id} is empty (Bulunamadı text found)")
                    continue

                # 0: Saat, 1: Kod, 2: Ad, 3: Derslik, 4: Hoca
                try:
                    time_range = cells[0].text.strip()
                    course_code = cells[1].text.strip()
                    course_name = cells[2].text.strip()
                    location = cells[3].text.strip()
                    lecturer = cells[4].text.strip()
                except Exception as e:
                    logger.error(f"Error parsing row cells in {grid_id}: {e}")
                    continue

                # Cleanup bracketed numbers in location/code if any (e.g. MDBF-AMFİ2[90])
                # We keep the original for now, but remove [xx] if strictly desired.
                # User asked for "MDBF-AMFİ2" but HTML has "MDBF-AMFİ2[90]". Let's clean it.
                location_clean = re.sub(r'\[.*?\]', '', location).strip()

                # Check for 'DarkGreen' style indicating Practice/Lab
                # Check style attribute of the row or cells
                is_practice = False
                style_str = row.get('style', '') or ''
                if 'DarkGreen' in style_str:
                    is_practice = True
                else:
                    # check first cell
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
                
                logger.info(f"Parsed lesson: {course_name} ({time_range})")
                day_lessons.append(lesson)
            
            if day_lessons:
                schedule[day_key] = day_lessons

        logger.info(f"Finished parsing. Found days: {list(schedule.keys())}")
        return schedule
