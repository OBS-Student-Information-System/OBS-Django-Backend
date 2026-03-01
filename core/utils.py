"""
Shared utility functions.
"""
import requests
from core.tenant_config import get_config
from core.exceptions import SessionExpiredError
from core.logger import setup_logger

_logger = setup_logger("core.utils")


def create_session():
    """Create a configured requests Session with tenant-specific headers."""
    cfg = get_config()
    session = requests.Session()
    session.headers.update(cfg.default_headers)
    session.headers.update({
        "Referer": cfg.login_url,
        "Origin": cfg.obs_domain,
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
    base = get_config().base_url
    return base + src.lstrip("/") if src.startswith("/") else base + src


def check_session_expiry(response: requests.Response) -> None:
    """
    Check if an OBS response indicates the session has expired.

    Raises SessionExpiredError if any expiry signal is detected:
    - Redirect to login.aspx
    - Redirect to deferror.aspx
    - Response body contains login form markers

    Call this after every authenticated GET/POST in scrapers.
    """
    url_lower = response.url.lower()

    if "login.aspx" in url_lower:
        _logger.warning("Session expired: redirected to login.aspx (%s)", response.url)
        raise SessionExpiredError("Oturum süresi doldu, lütfen tekrar giriş yapın.")

    if "deferror.aspx" in url_lower:
        _logger.warning("Session expired: redirected to deferror.aspx (%s)", response.url)
        raise SessionExpiredError("Sunucu oturum hatası (DefError).")

    text_lower = response.text[:2000].lower()
    if "frmlogin" in text_lower or "frmogrlogin" in text_lower:
        _logger.warning("Session expired: login form detected in response body")
        raise SessionExpiredError("Oturum süresi doldu (login form detected).")
