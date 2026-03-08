"""
Scraper for the GPA History (Dönem Ortalamaları) module.

Flow: caller.aspx?curPage=122 → ogrenci_donem_ortalamalari.aspx (frame).
Parses table #grdOrtalamasi: Dönem Adı, Aldığı Ders Sayısı, Toplam Kredi,
Toplam AKTS, Dönem Ort. (YANO), Genel Not Ort. (AGNO).
Uses defensive parsing and Turkish decimal format (comma).
"""
import logging
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup
from core.utils import create_session
from core.tenant_config import get_config

logger = logging.getLogger(__name__)

def _parse_turkish_decimal(value: str) -> Optional[float]:
    """
    Parse a numeric cell: Turkish decimal (e.g. '2,70' or '21,5').
    Returns None for empty, '--', or invalid.
    """
    if not value or not isinstance(value, str):
        return None
    raw = value.strip()
    if not raw or raw == "--":
        return None
    try:
        normalized = raw.replace(",", ".")
        return float(normalized)
    except ValueError:
        return None


def _parse_turkish_int(value: str) -> Optional[int]:
    """Parse integer (e.g. '7' or '20'). Returns None for '--' or invalid."""
    parsed = _parse_turkish_decimal(value)
    if parsed is None:
        return None
    try:
        return int(parsed) if parsed == int(parsed) else int(parsed)
    except (ValueError, TypeError):
        return None


class GpaHistoryScraper:
    """
    Scraper for the 'Dönem Ortalamaları' (GPA History) iframe.

    - Warms up via caller.aspx?curPage=122
    - Fetches ogrenci_donem_ortalamalari.aspx
    - Parses table #grdOrtalamasi with defensive handling for missing/odd rows
    """

    def __init__(self, session: Optional[Any] = None):
        self.session = session if session else create_session()
        cfg = get_config()
        self._cfg = cfg
        self.caller_url = cfg.scraper.url_for("gpa_history_caller")
        self.frame_url = cfg.scraper.url_for("gpa_history_frame")
        self._default_referer = cfg.default_referer

    def fetch_gpa_history(self) -> Dict[str, Any]:
        """
        Fetches the GPA history frame and parses it into a list of term records.

        Returns envelope: status, data (list of term dicts), message, error_code.
        """
        if not self.session.cookies:
            logger.error("No cookies found, cannot fetch GPA history.")
            return {
                "status": "error",
                "message": "Oturum bulunamadı",
                "error_code": "NO_SESSION",
            }

        try:
            self.session.headers.update({
                "Referer": self._default_referer,
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "same-origin",
            })
            logger.info("Accessing GPA History caller page...")
            self.session.get(self.caller_url, timeout=self._cfg.scraper.timeout_seconds)

            self.session.headers.update({
                "Referer": self.caller_url,
                "Sec-Fetch-Dest": "iframe",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "same-origin",
            })
            logger.info("Fetching GPA History frame...")
            resp = self.session.get(self.frame_url, timeout=self._cfg.scraper.timeout_seconds)

            if resp.status_code != 200:
                logger.error(
                    "Failed to fetch GPA History frame. Status code: %s",
                    resp.status_code,
                )
                return {
                    "status": "error",
                    "message": "Dönem ortalamaları sayfası alınamadı",
                    "error_code": "GPA_HISTORY_FETCH_ERROR",
                }

            # Session expiry: redirect to login or explicit expiry message in body
            if "login.aspx" in resp.url.lower():
                logger.warning("Session expired (redirect to login) while fetching GPA history.")
                return {
                    "status": "error",
                    "message": "Oturum süresi doldu",
                    "error_code": "SESSION_EXPIRED",
                }
            text_lower = (resp.text or "").lower()
            if "oturum süresi doldu" in text_lower or "oturum süresi sona erdi" in text_lower:
                logger.warning("Session expired (body text) while fetching GPA history.")
                return {
                    "status": "error",
                    "message": "Oturum süresi doldu",
                    "error_code": "SESSION_EXPIRED",
                }

            return self._parse_gpa_table(resp.text)

        except Exception as exc:
            logger.exception("Error during GPA History fetch", exc_info=True)
            return {
                "status": "error",
                "message": f"Bağlantı hatası: {exc}",
                "error_code": "GPA_HISTORY_SCRAPE_ERROR",
            }

    def _parse_gpa_table(self, html: str) -> Dict[str, Any]:
        """
        Parse table #grdOrtalamasi.
        Columns: Dönem Adı, Aldığı Ders Sayısı, Toplam Kredi, Toplam AKTS,
                 Dönem Ortalaması (YANO), Genel Not Ortalaması (AGNO).
        """
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table", id="grdOrtalamasi")
        if not table:
            # Fallback: any table with class grdStyle
            table = soup.find("table", class_=lambda c: c and "grdStyle" in c)
        if not table:
            logger.warning("GPA table (grdOrtalamasi or grdStyle) not found.")
            return {
                "status": "success",
                "data": [],
                "message": "Ortalama geçmişi başarıyla getirildi",
            }

        rows = table.find_all("tr")
        if not rows:
            return {"status": "success", "data": [], "message": "Ortalama geçmişi başarıyla getirildi"}

        # First row is header; rest are data or footer (single cell with colspan)
        result: List[Dict[str, Any]] = []
        for row in rows[1:]:
            cells = row.find_all("td")
            if len(cells) != 6:
                # Footer row (e.g. pager) has one td with colspan
                continue
            try:
                term_name = (cells[0].get_text(strip=True) or "").strip()
                if not term_name:
                    continue

                total_courses = _parse_turkish_int(cells[1].get_text(strip=True))
                total_credits = _parse_turkish_decimal(cells[2].get_text(strip=True))
                total_ects = _parse_turkish_decimal(cells[3].get_text(strip=True))
                yano = _parse_turkish_decimal(cells[4].get_text(strip=True))
                agno = _parse_turkish_decimal(cells[5].get_text(strip=True))

                result.append({
                    "term_name": term_name,
                    "yano": yano if yano is not None else 0.0,
                    "agno": agno if agno is not None else 0.0,
                    "total_credits": int(round(total_credits)) if total_credits is not None else 0,
                    "total_ects": int(round(total_ects)) if total_ects is not None else 0,
                    "total_courses": total_courses if total_courses is not None else 0,
                })
            except Exception as exc:
                logger.warning(
                    "GPA history row parse failed, skipping row: %s",
                    exc,
                    exc_info=True,
                )
                continue

        logger.info("Parsed %d GPA history terms.", len(result))
        return {
            "status": "success",
            "data": result,
            "message": "Ortalama geçmişi başarıyla getirildi",
        }
