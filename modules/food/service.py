
from typing import Dict, Any
from modules.food.scraper import FoodScraper
from core.logger import setup_logger
from core.tenant_config import get_config

logger = setup_logger(__name__)

class FoodService:
    def __init__(self, scraper=None):
        self.scraper = scraper or FoodScraper()

    def get_daily_menu(self, menu_url: str) -> Dict[str, Any]:
        """
        Coordinates fetching the daily menu.
        """
        if not menu_url:
            menu_url = get_config().food_menu_url

        result = self.scraper.get_daily_menu(menu_url)
        
        if "error" in result:
            return {
                "status": "error", 
                "message": result["error"]
            }
        
        return {
            "status": "success",
            "data": result
        }
