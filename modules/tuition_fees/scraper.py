"""
Scraper for Tuition & Fees (Harc Bilgileri): ogrenci_harc_bilgileri_devlet.aspx.

Flow:
1) GET caller.aspx?curPage=110
2) GET ogrenci_harc_bilgileri_devlet.aspx (iframe)
3) Parse summary and transactions tables defensively
"""

import logging
import re
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup

from core.tenant_config import get_config
from core.utils import create_session

logger = logging.getLogger(__name__)


def _is_session_expired(url: str, text: str) -> bool:
    """Detect OBS session expiry by URL or known text patterns."""
    url_lower = (url or "").lower()
    text_lower = (text or "").lower()
    if "login.aspx" in url_lower or "deferror.aspx" in url_lower:
        return True
    if "oturum süresi doldu" in text_lower or "oturum süresi sona erdi" in text_lower:
        return True
    return False


class TuitionFeesScraper:
    """Scraper for Harc Bilgileri page."""

    def __init__(self, session: Optional[Any] = None):
        self.session = session if session else create_session()
        cfg = get_config()
        self._cfg = cfg
        self.caller_url = cfg.scraper.url_for("tuition_fees_caller")
        self.frame_url = cfg.scraper.url_for("tuition_fees_frame")
        self._default_referer = cfg.default_referer

    def fetch_tuition_fees(self) -> Dict[str, Any]:
        """Fetch tuition fees summary + transaction rows in standard envelope."""
        if not self.session.cookies:
            logger.error("No cookies found, cannot fetch tuition fees.")
            return {
                "status": "error",
                "message": "Oturum bulunamadı",
                "error_code": "NO_SESSION",
            }

        try:
            self.session.headers.update(
                {
                    "Referer": self._default_referer,
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "same-origin",
                }
            )
            logger.info("Accessing Tuition Fees caller page...")
            self.session.get(self.caller_url, timeout=self._cfg.scraper.timeout_seconds)

            self.session.headers.update(
                {
                    "Referer": self.caller_url,
                    "Sec-Fetch-Dest": "iframe",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "same-origin",
                }
            )
            logger.info("Fetching Tuition Fees frame...")
            resp = self.session.get(
                self.frame_url,
                timeout=self._cfg.scraper.timeout_seconds,
                allow_redirects=True,
            )

            if resp.status_code != 200:
                logger.error("Tuition fees frame failed with status %s", resp.status_code)
                return {
                    "status": "error",
                    "message": "Harç bilgileri sayfası alınamadı",
                    "error_code": "TUITION_FEES_FETCH_ERROR",
                }

            if _is_session_expired(resp.url, resp.text):
                return {
                    "status": "error",
                    "message": "Oturum süresi doldu",
                    "error_code": "SESSION_EXPIRED",
                }

            data = self._parse_page(resp.text)
            return {
                "status": "success",
                "data": data,
                "message": "Harç bilgileri başarıyla getirildi",
            }
        except Exception as exc:
            logger.exception("Error during Tuition Fees fetch", exc_info=True)
            return {
                "status": "error",
                "message": f"Bağlantı hatası: {exc}",
                "error_code": "TUITION_FEES_SCRAPE_ERROR",
            }

    def _parse_page(self, html: str) -> Dict[str, Any]:
        """Parse both summary and transaction sections."""
        soup = BeautifulSoup(html, "html.parser")
        summary = self._parse_summary(soup)
        transactions = self._parse_transactions(soup)
        return {
            "summary": summary,
            "transactions": transactions,
        }

    def _parse_summary(self, soup: BeautifulSoup) -> Dict[str, str]:
        """
        Parse top fee summary table into stable keys.
        Falls back to empty strings if rows/cells are missing.
        """
        result = {
            "previous_balance": "",
            "term_fee": "",
            "total_payable": "",
            "total_paid": "",
            "general_balance": "",
        }

        table = soup.find("table", id="tblOgrInfoBar")
        if not table:
            logger.warning("Summary table tblOgrInfoBar not found.")
            return result

        tbody = table.find("tbody")
        container = tbody if tbody else table
        rows = container.find_all("tr", recursive=False)

        for row in rows:
            try:
                cells = row.find_all("td", recursive=False)
                if len(cells) < 2:
                    continue

                label_text = self._normalize(cells[0].get_text(" ", strip=True))
                value_text = (cells[1].get_text(" ", strip=True) or "").strip()

                if not label_text:
                    continue

                if "önceki dönem bakiye" in label_text or "onceki donem bakiye" in label_text:
                    result["previous_balance"] = value_text
                elif "dönemlik ücret" in label_text or "donemlik ucret" in label_text:
                    result["term_fee"] = value_text
                elif (
                    "ödenmesi gereken toplam ücret" in label_text
                    or "odenmesi gereken toplam ucret" in label_text
                ):
                    result["total_payable"] = value_text
                elif "ödenen toplam ücret" in label_text or "odenen toplam ucret" in label_text:
                    result["total_paid"] = value_text
                elif "genel bakiye" in label_text:
                    result["general_balance"] = value_text
            except Exception as exc:
                logger.warning("Failed to parse summary row: %s", exc, exc_info=True)
                continue

        return result

    def _parse_transactions(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Parse bottom grid into transaction dictionaries."""
        table = soup.find("table", id="grdHarclar")
        if not table:
            logger.warning("Transactions table grdHarclar not found.")
            return []

        header_row = self._find_header_row(table)
        if not header_row:
            logger.warning("Header row not found in grdHarclar.")
            return []

        header_map = self._detect_header_map(header_row)
        if not header_map:
            logger.warning("Could not detect expected headers in grdHarclar.")
            return []

        tbody = table.find("tbody")
        container = tbody if tbody else table
        rows = container.find_all("tr", recursive=False)

        out: List[Dict[str, str]] = []
        for row in rows:
            try:
                if row is header_row:
                    continue
                cells = row.find_all("td", recursive=False)
                if not cells:
                    continue
                if any(td.get("colspan") for td in cells):
                    continue

                def cell_text(key: str, _cells=cells) -> str:
                    idx = header_map.get(key)
                    if idx is None or idx >= len(_cells):
                        return ""
                    return (_cells[idx].get_text(" ", strip=True) or "").strip()

                tx = {
                    "term": cell_text("term"),
                    "type": cell_text("type"),
                    "category": cell_text("category"),
                    "amount": cell_text("amount"),
                    "refund": cell_text("refund"),
                    "accrual_date": cell_text("accrual_date"),
                    "payment_date": cell_text("payment_date"),
                }

                if not any(tx.values()):
                    continue
                out.append(tx)
            except Exception as exc:
                logger.warning("Failed to parse transaction row: %s", exc, exc_info=True)
                continue

        return out

    @staticmethod
    def _find_header_row(table):
        """Return first row containing direct TH children."""
        tbody = table.find("tbody")
        container = tbody if tbody else table
        for tr in container.find_all("tr", recursive=False):
            if tr.find("th", recursive=False):
                return tr
        return None

    def _detect_header_map(self, header_row) -> Optional[Dict[str, int]]:
        """Detect grid header indices by normalized label text."""
        cells = header_row.find_all(["th", "td"], recursive=False)
        labels = [self._normalize(c.get_text(" ", strip=True)) for c in cells]

        def find_exact(*keywords: str) -> Optional[int]:
            normalized = {self._normalize(k) for k in keywords}
            for i, label in enumerate(labels):
                if label in normalized:
                    return i
            return None

        def find_index(*keywords: str) -> Optional[int]:
            for i, label in enumerate(labels):
                for kw in keywords:
                    if self._normalize(kw) in label:
                        return i
            return None

        header_map: Dict[str, Optional[int]] = {
            "term": find_index("dönemi", "donemi", "dönem", "donem"),
            "type": find_index("tipi", "tip"),
            "category": find_index("türü", "turu", "tür", "tur"),
            "amount": find_exact("tutar"),
            "refund": find_index("iade tutar", "iade"),
            "accrual_date": find_index("tahakkuk tarihi", "tahakkuk"),
            "payment_date": find_index("ödeme tarihi", "odeme"),
        }

        # Require core fields for valid mapping
        if header_map["term"] is None and header_map["type"] is None:
            return None
        if header_map["amount"] is None and header_map["accrual_date"] is None:
            return None

        return {k: v for k, v in header_map.items() if v is not None}

    @staticmethod
    def _normalize(text: str) -> str:
        lowered = (text or "").strip().lower()
        lowered = lowered.replace("ı", "i")
        lowered = lowered.replace("ğ", "g").replace("ş", "s")
        lowered = lowered.replace("ö", "o").replace("ü", "u").replace("ç", "c")
        lowered = re.sub(r"\s+", " ", lowered)
        return lowered.strip()
