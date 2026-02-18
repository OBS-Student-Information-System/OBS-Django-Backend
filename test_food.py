
import sys
import os
import traceback

# Add current directory to path
sys.path.append(os.getcwd())

print("Script started", file=sys.stderr, flush=True)

try:
    from modules.food.service import FoodService
    print("Import successful", file=sys.stderr, flush=True)

    def test_food_menu():
        url = "https://sksdb.ozal.edu.tr/yemek_listesi"
        print(f"Testing Food Service with URL: {url}", file=sys.stderr, flush=True)
        
        service = FoodService()
        result = service.get_daily_menu(url)
        
        print("\n--- RESULT ---", file=sys.stderr, flush=True)
        print(result, file=sys.stderr, flush=True)

    if __name__ == "__main__":
        test_food_menu()

except Exception as e:
    print(f"CRITICAL ERROR: {e}", file=sys.stderr, flush=True)
    traceback.print_exc(file=sys.stderr)
