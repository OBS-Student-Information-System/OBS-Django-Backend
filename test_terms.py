"""
Test get_available_terms endpoint
"""
import requests
import json

# You need real cookies from a login session
# Get them from your authBox after logging in via the app

url = "http://localhost:8000"

# Test with mock cookies (replace with real ones)
payload = {
    "action": "get_available_terms",
    "cookies": {
        # TODO: Add real cookies here from a successful login
        "ASP.NET_SessionId": "your_session",
        ".ASPXAUTH": "your_auth"
    }
}

print("Testing get_available_terms endpoint...")
print(f"URL: {url}")
print(f"Payload: {json.dumps(payload, indent=2)}")

try:
    response = requests.post(url, json=payload)
    print(f"\nStatus: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
except Exception as e:
    print(f"Error: {e}")
