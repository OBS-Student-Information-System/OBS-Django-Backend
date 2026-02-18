
from typing import Dict, Any, Optional
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from core.logger import setup_logger

logger = setup_logger(__name__)

class FoodScraper:
    def __init__(self):
        # We don't need a persistent session for this, as it's a public public page
        # but using a session is good practice for connection pooling if we were to scale
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def get_daily_menu(self, url: str) -> Dict[str, Any]:
        """
        Fetches and parses the daily menu from the given URL.
        Expected URL: https://sksdb.ozal.edu.tr/yemek_listesi (or similar)
        """
        try:
            logger.info(f"Fetching food menu from: {url}")
            response = self.session.get(url, timeout=15)
            
            if response.status_code != 200:
                logger.error(f"Failed to fetch menu. Status: {response.status_code}")
                return {"error": f"Menüye erişilemedi. Hata kodu: {response.status_code}"}

            soup = BeautifulSoup(response.content, 'lxml')
            
            # Parser Logic matching the user's provided HTML snippet:
            # <div class="box"><div class="box__content"><p>FOOD NAME</p></div></div>
            
            # Select all paragraphs inside .box__content
            # equivalent to Dart: document.querySelectorAll('.box .box__content p')
            food_items = soup.select('.box .box__content p')
            
            if not food_items:
                logger.warning("No food items found with selector '.box .box__content p'")
                return {"error": "Menü yapısı değişmiş olabilir, veri bulunamadı."}
            
            # Text cleaning helper
            def clean_text(element):
                return element.get_text(strip=True) if element else "-"

            # Mapping logic (Main -> Side -> Soup -> Dessert) based on user snippet
            # 1. KOFTE (Main)
            # 2. PILAV (Side)
            # 3. CORBA (Soup)
            # 4. HAYDARİ (Side/Appetizer)
            
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
                "calorie": 0 # Not available in snippet
            }

        except Exception as e:
            logger.exception("Exception in get_daily_menu")
            return {"error": f"Menü ayrıştırılamadı: {str(e)}"}
