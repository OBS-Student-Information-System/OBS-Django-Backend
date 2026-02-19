"""
Food Parser Module.
Handles parsing of daily food menu HTML.
"""
from bs4 import BeautifulSoup
from typing import Dict, Any, Optional
from datetime import datetime

def parse_daily_menu(html_content: bytes) -> Dict[str, Any]:
    """Parse daily menu from HTML."""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Parser Logic matching the user's provided HTML snippet:
    # <div class="box"><div class="box__content"><p>FOOD NAME</p></div></div>
    
    # Select all paragraphs inside .box__content
    food_items = soup.select('.box .box__content p')
    
    if not food_items:
        return {"error": "Menü yapısı değişmiş olabilir, veri bulunamadı."}
    
    # Text cleaning helper
    def clean_text(element):
        return element.get_text(strip=True) if element else "-"

    # Mapping logic (Main -> Side -> Soup -> Dessert)
    main_dish = clean_text(food_items[0]) if len(food_items) > 0 else "-"
    side_dish = clean_text(food_items[1]) if len(food_items) > 1 else "-"
    soup_name = clean_text(food_items[2]) if len(food_items) > 2 else "-"
    dessert = clean_text(food_items[3]) if len(food_items) > 3 else "-"
    
    today_str = datetime.now().strftime('%d.%m.%Y')
    
    return {
        "date": today_str,
        "mainDish": main_dish,
        "sideDish": side_dish,
        "soup": soup_name,
        "dessert": dessert,
        "calorie": 0
    }
