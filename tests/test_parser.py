import sys
import os
import json
sys.path.insert(0, os.path.abspath('.'))
from modules.student_file.scraper import StudentFileScraper

html = open(r'c:\Users\erenk\OneDrive\Desktop\-\Projeler\OBS\OBS-Docs\egitimbilgileriresponse.html', 'r', encoding='utf-8').read()
scraper = StudentFileScraper()
fragment = scraper._extract_updatepanel_html(html)
print(f"Fragment len: {len(fragment)}")
data = scraper._parse_grid(fragment)
print("Data JSON:")
print(json.dumps(data, indent=2, ensure_ascii=False))
