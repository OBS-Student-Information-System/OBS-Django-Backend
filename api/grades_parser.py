"""
Grades Parser for OBS
Parses HTML table from OBS grades page into structured data
"""
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import re


def parse_my_grades(raw_text: str) -> Dict[str, Optional[str]]:
    """
    Parse individual student grades from raw text.
    Example input: "Vize : 60 Final : 80 Bütünleme : --"
    Returns: {"Vize": "60", "Final": "80", "Büt": None}
    """
    grades = {"Vize": None, "Final": None, "Büt": None}
    
    # Trim whitespace and normalize
    text = raw_text.strip()
    
    # DEBUG: Print raw text to see exact format
    print(f"[PARSER] Raw grade text: '{text}'")
    
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
    
    # Parse Bütünleme (Makeup) - HTML uses "Büt" not "Bütünleme"
    but_match = re.search(r'Büt\s*:\s*(\d+|--)', text)
    if but_match:
        val = but_match.group(1)
        grades["Büt"] = None if val == '--' else val
    else:
        print(f"[PARSER] Büt not found in: '{text}'")
    
    print(f"[PARSER] Parsed grades: {grades}")
    return grades


def parse_grades_table(html_content: str) -> List[Dict]:
    """
    Parse the main grades table from OBS HTML.
    Returns list of grade dictionaries.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Find the grades table
    table = soup.find(id='grd_not_listesi')
    if not table:
        raise Exception("Grades table not found (id='grd_not_listesi')")
    
    # Get semester info if available
    term_id = "20251"  # Default fallback
    term_select = soup.find('select', id='cmbDonemler')
    if term_select:
        selected_opt = term_select.find('option', selected=True)
        if selected_opt:
            term_id = selected_opt.get('value', term_id)
    
    grades_list = []
    rows = table.find_all('tr')[1:]  # Skip header row
    
    for row in rows:
        cols = row.find_all('td')
        if len(cols) < 7:  # Need at least 7 columns
            continue
        
        try:
            # Column indices (0-based):
            # 1: Course Code, 2: Course Name, 4: Grades Text, 6: Letter Grade
            course_code = cols[1].get_text(strip=True)
            course_name = cols[2].get_text(strip=True)
            grades_raw = cols[4].get_text(' ', strip=True)
            letter_grade = cols[6].get_text(strip=True)
            
            # Parse individual grades
            my_grades = parse_my_grades(grades_raw)
            
            # Build grade object
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
            # Defensive: skip malformed rows
            print(f"Warning: Failed to parse grade row - {e}")
            continue
    
    return grades_list
