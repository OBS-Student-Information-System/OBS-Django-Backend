import requests
from bs4 import BeautifulSoup
import re

# We will use the standard OBS entrypoint to just fetch the login page or any page to see if IDs changed.
url = "https://obs.ozal.edu.tr/oibs/std/login.aspx"

response = requests.get(url, verify=False)
soup = BeautifulSoup(response.text, 'html.parser')

print("Fetching login page just to see if the structure is reachable without auth...")
# Find all inputs
inputs = soup.find_all('input')
for inp in inputs:
    print(f"Input Name: {inp.get('name')}, ID: {inp.get('id')}")
