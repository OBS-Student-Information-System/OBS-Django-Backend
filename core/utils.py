"""
Shared utility functions.
"""
import requests
from core.config import DEFAULT_HEADERS, LOGIN_URL, BASE_URL

def create_session():
    """Create a configured requests Session."""
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)
    session.headers.update({
        "Referer": LOGIN_URL,
        "Origin": "https://obs.ozal.edu.tr",
    })
    return session

def get_hidden_inputs(soup):
    """Extract hidden inputs from a BeautifulSoup object."""
    data = {}
    for inp in soup.find_all("input", type="hidden"):
        if inp.get("name"):
            data[inp.get("name")] = inp.get("value", "")
    return data

def fix_url(src):
    """Normalize relative URLs to absolute URLs."""
    if not src:
        return ""
    if src.startswith("http"):
        return src
    return BASE_URL + src.lstrip("/") if src.startswith("/") else BASE_URL + src
