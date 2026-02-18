
from typing import Dict, Any
from modules.food.scraper import FoodScraper
from core.logger import setup_logger

logger = setup_logger(__name__)

class FoodService:
    def __init__(self):
        self.scraper = FoodScraper()

    def get_daily_menu(self, menu_url: str) -> Dict[str, Any]:
        """
        Coordinates fetching the daily menu.
        """
        if not menu_url:
            return {"success": False, "message": "Menu URL is missing."}

        result = self.scraper.get_daily_menu(menu_url)
        
        if "error" in result:
            return {
                "success": False, 
                "message": result["error"]
            }
        
        return {
            "success": True,
            "data": result
        }
