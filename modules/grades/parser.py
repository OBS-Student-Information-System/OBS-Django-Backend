"""
Grades Parser.
Parses HTML table from OBS grades page into structured data.
"""
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import re

from core.config import SELECTORS

def parse_my_grades(raw_text: str) -> Dict[str, Optional[str]]:
    """Parse individual student grades from raw text."""
    grades: Dict[str, Optional[str]] = {"Vize": None, "Final": None, "Büt": None}
    text = raw_text.strip()
    
    # Parse Vize
    vize_match = re.search(r'Vize\s*:\s*(\d+|--)', text)
    if vize_match:
        val = vize_match.group(1)
        grades["Vize"] = None if val == '--' else val
    
    # Parse Final
    final_match = re.search(r'Final\s*:\s*(\d+|--)', text)
    if final_match:
        val = final_match.group(1)
        grades["Final"] = None if val == '--' else val
    
    # Parse Bütünleme
    but_match = re.search(r'Büt\s*:\s*(\d+|--)', text)
    if but_match:
        val = but_match.group(1)
        grades["Büt"] = None if val == '--' else val
    
    return grades

def parse_grades_table(html_content: str) -> List[Dict]:
    """Parse the main grades table from OBS HTML."""
    soup = BeautifulSoup(html_content, 'lxml')
    
    table = soup.find(id=SELECTORS["GRADES_TABLE"])
    if not table:
        return [] # Return empty list instead of raising exception
    
    # Get semester info
    term_id = "20251"
    term_select = soup.find('select', id=SELECTORS["TERM_DROPDOWN"])
    if term_select:
        selected_opt = term_select.find('option', selected=True)
        if selected_opt:
            term_id = selected_opt.get('value', term_id)
    
    grades_list = []
    rows = table.find_all('tr')[1:] # Skip header
    
    for row in rows:
        cols = row.find_all('td')
        if len(cols) < 7:
            continue
        
        try:
            course_code = cols[1].get_text(strip=True)
            course_name = cols[2].get_text(strip=True)
            grades_raw = cols[4].get_text(' ', strip=True)
            letter_grade = cols[6].get_text(strip=True)
            
            my_grades = parse_my_grades(grades_raw)
            
            grade_obj = {
                "course_code": course_code,
                "course_name": course_name,
                "term_id": term_id,
                "letter_grade": letter_grade if letter_grade and letter_grade != '--' else None,
                "midterm": my_grades["Vize"],
                "final": my_grades["Final"],
                "makeup": my_grades["Büt"]
            }
            
            grades_list.append(grade_obj)
            
        except Exception as e:
            logger.warning(f"Failed to parse grade row: {e}")
            continue
    
    return grades_list
