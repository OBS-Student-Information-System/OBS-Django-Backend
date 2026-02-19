
from typing import Dict, Any, Optional
import requests
from core.logger import setup_logger
from modules.food.parser import parse_daily_menu

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
            # SSL Verification disabled due to certificate issues
            response = self.session.get(url, timeout=15, verify=False)
            
            if response.status_code != 200:
                logger.error(f"Failed to fetch menu. Status: {response.status_code}")
                return {"error": f"Menüye erişilemedi. Hata kodu: {response.status_code}"}

            return parse_daily_menu(response.content)

        except Exception as e:
            logger.exception("Exception in get_daily_menu")
            return {"error": f"Menü ayrıştırılamadı: {str(e)}"}
