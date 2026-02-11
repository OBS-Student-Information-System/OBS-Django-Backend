import requests
from typing import List, Dict, Any
from .scraper import CalendarScraper

class CalendarService:
    def __init__(self):
        self.scraper = CalendarScraper()
        self.calendar_url = "https://obs.ozal.edu.tr/oibs/std/st_akademik_takvim.aspx"

    def get_calendar(self) -> List[Dict[str, Any]]:
        try:
            # Attempt to fetch the live page
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            }
            response = requests.get(self.calendar_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                events = self.scraper.parse_calendar_table(response.text)
                if events:
                    return events
            
            # Fallback if fetch fails or returns empty (e.g. session redirect)
            # useful for local testing if blocked
            print("Fetching failed or empty, returning mock/fallback data.")
            return self._get_fallback_data()
            
        except Exception as e:
            print(f"Error fetching calendar: {e}")
            return self._get_fallback_data()

    def _get_fallback_data(self):
        return [
            {"name": "Öğrenci Harç", "start_date": "02.02.2026 09:00", "end_date": "06.02.2026 23:59"},
            {"name": "Öğrenci Ek Harç", "start_date": "02.02.2026 09:00", "end_date": "06.02.2026 23:59"},
            {"name": "Mazeretli Öğrenci Harç", "start_date": "09.02.2026 09:00", "end_date": "19.06.2026 23:59"},
            {"name": "Yeni Öğrenci Ders Kayıt", "start_date": "02.02.2026 09:00", "end_date": "06.02.2026 23:59"},
            {"name": "Yeni Öğrenci Danışman Onay", "start_date": "02.02.2026 09:00", "end_date": "09.02.2026 17:00"},
            {"name": "Ders Kayıt", "start_date": "02.02.2026 09:00", "end_date": "06.02.2026 23:59"},
            {"name": "Danışman Onay", "start_date": "02.02.2026 09:00", "end_date": "09.02.2026 17:00"},
            {"name": "Mazeretli Ders Kayıt", "start_date": "09.02.2026 09:00", "end_date": "06.03.2026 23:59"},
            {"name": "Mazeretli Danışman Onay", "start_date": "09.02.2026 09:00", "end_date": "08.03.2026 23:59"},
            {"name": "Yeni Öğrenci Ders Ekle/Bırak", "start_date": "25.02.2026 09:00", "end_date": "27.02.2026 23:59"},
            {"name": "Yeni Öğrenci Ders Ekle/Bırak Onay", "start_date": "26.02.2026 09:00", "end_date": "28.02.2026 23:59"},
            {"name": "Ders Ekle/Bırak", "start_date": "25.02.2026 09:00", "end_date": "27.02.2026 23:59"},
            {"name": "Ders Ekle/Bırak Onay", "start_date": "25.02.2026 09:00", "end_date": "28.02.2026 23:59"},
        ]
