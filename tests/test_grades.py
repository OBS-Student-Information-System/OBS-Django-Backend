"""
Quick test script for grades endpoint
"""
import requests
import json

# Test get_grades endpoint
url = "http://localhost:8000"

# First, you need cookies from a successful login
# Get them from your Flutter app's Hive storage or from a login test

# Example payload (replace with real cookies from successful login)
payload = {
    "action": "get_grades",
    "cookies": {
        # Add your actual cookies here after logging in
        # Example:
        # "ASP.NET_SessionId": "your_session_id",
        # ".ASPXAUTH": "your_auth_cookie"
    }
}

print("Testing grades endpoint...")
print(f"Payload: {json.dumps(payload, indent=2)}")

try:
    response = requests.post(url, json=payload)
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
except Exception as e:
    print(f"Error: {e}")
