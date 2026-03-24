"""
Scraper for Offered Department Courses (Acilan Bolum Dersleri): program_dersleri.aspx.

Flow:
1) GET caller.aspx?curPage=104
2) GET program_dersleri.aspx as iframe
3) Optionally POST "Tumunu Goster" to fetch all rows in one page
4) Parse grdDersler table defensively via dynamic header mapping
"""

import logging
import re
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup

from core.tenant_config import get_config
from core.utils import create_session

logger = logging.getLogger(__name__)


def _is_session_expired(url: str, text: str) -> bool:
    """Detect OBS session expiry by URL or common page messages."""
    url_lower = (url or "").lower()
    text_lower = (text or "").lower()
    if "login.aspx" in url_lower or "deferror.aspx" in url_lower:
        return True
    if "oturum süresi doldu" in text_lower or "oturum süresi sona erdi" in text_lower:
        return True
    return False


class OfferedCoursesScraper:
    """Scraper for Acilan Bolum Dersleri (program_dersleri.aspx)."""

    def __init__(self, session: Optional[Any] = None):
        self.session = session if session else create_session()
        cfg = get_config()
        self._cfg = cfg
        self.caller_url = cfg.scraper.url_for("offered_courses_caller")
        self.frame_url = cfg.scraper.url_for("offered_courses_frame")
        self._default_referer = cfg.default_referer

    def fetch_offered_courses(self) -> Dict[str, Any]:
        """Fetch offered courses using caller-frame pattern and parse table rows."""
        if not self.session.cookies:
            logger.error("No cookies found, cannot fetch offered courses.")
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
            logger.info("Accessing Offered Courses caller page...")
            self.session.get(self.caller_url, timeout=self._cfg.scraper.timeout_seconds)

            self.session.headers.update(
                {
                    "Referer": self.caller_url,
                    "Sec-Fetch-Dest": "iframe",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "same-origin",
                }
            )
            logger.info("Fetching Offered Courses frame...")
            resp = self.session.get(
                self.frame_url,
                timeout=self._cfg.scraper.timeout_seconds,
                allow_redirects=True,
            )

            if resp.status_code != 200:
                logger.error("Offered courses frame failed with status %s", resp.status_code)
                return {
                    "status": "error",
                    "message": "Açılan dersler sayfası alınamadı",
                    "error_code": "OFFERED_COURSES_FETCH_ERROR",
                }

            if _is_session_expired(resp.url, resp.text):
                return {
                    "status": "error",
                    "message": "Oturum süresi doldu",
                    "error_code": "SESSION_EXPIRED",
                }

            html = self._postback_show_all(resp.text)
            if isinstance(html, dict):
                return html

            courses = self._parse_offered_courses(html)
            return {
                "status": "success",
                "data": courses,
                "message": "Açılan dersler başarıyla getirildi",
            }
        except Exception as exc:
            logger.exception("Error during Offered Courses fetch", exc_info=True)
            return {
                "status": "error",
                "message": f"Bağlantı hatası: {exc}",
                "error_code": "OFFERED_COURSES_SCRAPE_ERROR",
            }

    def _postback_show_all(self, html: str) -> Any:
        """
        Try ASP.NET postback for "Tumunu Goster" button.
        If not available, return original HTML.
        """
        soup = BeautifulSoup(html, "html.parser")
        btn = soup.find("a", id="grdDersler_btnTumGoster")
        if not btn:
            return html

        href = btn.get("href", "")
        match = re.search(r"__doPostBack\('([^']+)'", href)
        event_target = match.group(1) if match else ""
        if not event_target:
            return html

        hidden: Dict[str, str] = {}
        for inp in soup.find_all("input", type="hidden"):
            name = inp.get("name")
            if name:
                hidden[name] = inp.get("value", "")

        post_data = {
            **hidden,
            "__EVENTTARGET": event_target,
            "__EVENTARGUMENT": "",
        }

        self.session.headers.update(
            {
                "Referer": self.frame_url,
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "same-origin",
            }
        )
        logger.info("Posting offered courses 'show all' action...")
        resp = self.session.post(
            self.frame_url,
            data=post_data,
            timeout=self._cfg.scraper.timeout_seconds,
            allow_redirects=True,
        )
        if _is_session_expired(resp.url, resp.text):
            return {
                "status": "error",
                "message": "Oturum süresi doldu",
                "error_code": "SESSION_EXPIRED",
            }
        if resp.status_code != 200:
            logger.warning(
                "Show all postback failed with status %s, parsing first page.",
                resp.status_code,
            )
            return html
        return resp.text

    def _parse_offered_courses(self, html: str) -> List[Dict[str, Any]]:
        """
        Parse offered courses table into flat list.
        Defensive parser with dynamic header map and footer filtering.
        """
        soup = BeautifulSoup(html, "html.parser")

        table = soup.find("table", id="grdDersler")
        if not table:
            for candidate in soup.find_all("table"):
                header_row = self._find_header_row(candidate)
                if header_row and self._detect_header_map(header_row):
                    table = candidate
                    break

        if not table:
            logger.warning("No table found for offered courses.")
            return []

        header_row = self._find_header_row(table)
        if not header_row:
            logger.warning("Header row not found in offered courses table.")
            return []

        header_map = self._detect_header_map(header_row)
        if not header_map:
            logger.warning("Offered courses table with expected headers not found.")
            return []

        tbody = table.find("tbody")
        container = tbody if tbody else table
        rows = container.find_all("tr", recursive=False)

        data_rows = []
        for tr in rows:
            if tr is header_row:
                continue
            tds = tr.find_all("td", recursive=False)
            if not tds:
                continue
            if any(td.get("colspan") for td in tds):
                continue
            data_rows.append(tr)

        courses: List[Dict[str, Any]] = []
        for row in data_rows:
            try:
                cells = row.find_all("td", recursive=False)
                if not cells:
                    continue

                def cell_text(key: str, _cells=cells) -> str:
                    idx = header_map.get(key)
                    if idx is None or idx >= len(_cells):
                        return ""
                    return (_cells[idx].get_text(strip=True) or "").strip()

                course_code = cell_text("course_code")
                course_name = cell_text("course_name")
                if not (course_code or course_name):
                    continue

                row_data = {
                    "branch": cell_text("branch"),
                    "course_code": course_code,
                    "course_name": course_name,
                    "class_year": cell_text("class_year"),
                    "u_hours": self._parse_number(cell_text("u_hours")),
                    "l_hours": self._parse_number(cell_text("l_hours")),
                    "t_hours": self._parse_number(cell_text("t_hours")),
                    "is_mandatory": self._parse_is_mandatory(cell_text("is_mandatory")),
                    "credit": self._parse_number(cell_text("credit")),
                    "ects": self._parse_number(cell_text("ects")),
                }
                courses.append(row_data)
            except Exception as exc:
                logger.warning("Failed to parse offered course row: %s", exc, exc_info=True)
                continue

        return courses

    @staticmethod
    def _find_header_row(table):
        """Return first row that has direct child TH nodes."""
        tbody = table.find("tbody")
        container = tbody if tbody else table
        for tr in container.find_all("tr", recursive=False):
            if tr.find("th", recursive=False):
                return tr
        return None

    def _detect_header_map(self, header_row) -> Optional[Dict[str, int]]:
        """
        Build a dynamic header map by matching known TR/EN keywords.
        This avoids strict index assumptions.
        """
        cells = header_row.find_all(["th", "td"], recursive=False)
        labels_raw = [(c.get_text(strip=True) or "").lower() for c in cells]
        labels_normalized = [self._normalize_header_label(v) for v in labels_raw]

        def find_contains(*keywords: str) -> Optional[int]:
            for i, label in enumerate(labels_normalized):
                for kw in keywords:
                    if kw in label:
                        return i
            return None

        def find_exact(*keywords: str) -> Optional[int]:
            normalized_keys = {self._normalize_header_label(v) for v in keywords}
            for i, label in enumerate(labels_normalized):
                if label in normalized_keys:
                    return i
            return None

        header_map: Dict[str, int] = {
            "branch": find_contains("şb", "sube", "branch"),
            "course_code": find_contains("ders kod", "course code"),
            "course_name": find_contains("ders ad", "course name"),
            "class_year": find_contains("sınıf", "sinif", "class"),
            "u_hours": find_exact("u"),
            "l_hours": find_exact("l"),
            "t_hours": find_exact("t"),
            "is_mandatory": find_exact("z"),
            "credit": find_contains("krd", "kredi", "credit"),
            "ects": find_contains("akts", "ects"),
        }

        if header_map["course_code"] is None and header_map["course_name"] is None:
            return None
        if header_map["credit"] is None and header_map["ects"] is None:
            return None

        return header_map

    @staticmethod
    def _normalize_header_label(value: str) -> str:
        """Normalize header text for resilient matching."""
        lowered = (value or "").strip().lower()
        lowered = re.sub(r"\s+", " ", lowered)
        return lowered.strip(".:;-_ ")

    def _parse_is_mandatory(self, text: str) -> Optional[bool]:
        """Map Z column values (1/2, Z/S, text) to bool."""
        if not text:
            return None
        normalized = text.strip().upper()
        if normalized in {"1", "Z"} or "ZORUNLU" in normalized:
            return True
        if normalized in {"0", "2", "S"}:
            return False
        if "SECMELI" in normalized or "SEÇMELI" in normalized or "SEÇMELİ" in normalized:
            return False
        return None

    def _parse_number(self, text: str) -> Optional[float]:
        """Convert numeric cells to int/float when possible."""
        if not text:
            return None
        cleaned = text.replace(",", ".").strip()
        try:
            value = float(cleaned)
            if value.is_integer():
                return int(value)
            return value
        except ValueError:
            return None
