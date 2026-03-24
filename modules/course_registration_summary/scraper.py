"""
Scraper for Course Registration Summary (Ders Kayit Ozeti): ders_kayit_ozet.aspx.

Flow:
1) GET caller.aspx?curPage=200
2) GET ders_kayit_ozet.aspx as iframe
3) Parse warning, approvals, info summary, and selected courses table defensively
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


class CourseRegistrationSummaryScraper:
    """Scraper for Ders Kayıt Özeti page."""

    def __init__(self, session: Optional[Any] = None):
        self.session = session if session else create_session()
        cfg = get_config()
        self._cfg = cfg
        self.caller_url = cfg.scraper.url_for("course_registration_summary_caller")
        self.frame_url = cfg.scraper.url_for("course_registration_summary_frame")
        self._default_referer = cfg.default_referer

    def fetch_course_registration_summary(self) -> Dict[str, Any]:
        """Fetch course registration summary with caller-frame flow."""
        if not self.session.cookies:
            logger.error("No cookies found, cannot fetch course registration summary.")
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
            logger.info("Accessing Course Registration Summary caller page...")
            self.session.get(self.caller_url, timeout=self._cfg.scraper.timeout_seconds)

            self.session.headers.update(
                {
                    "Referer": self.caller_url,
                    "Sec-Fetch-Dest": "iframe",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "same-origin",
                }
            )
            logger.info("Fetching Course Registration Summary frame...")
            resp = self.session.get(
                self.frame_url,
                timeout=self._cfg.scraper.timeout_seconds,
                allow_redirects=True,
            )

            if resp.status_code != 200:
                logger.error(
                    "Course registration summary frame failed with status %s",
                    resp.status_code,
                )
                return {
                    "status": "error",
                    "message": "Ders kayıt özeti sayfası alınamadı",
                    "error_code": "COURSE_REG_SUMMARY_FETCH_ERROR",
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
                "message": "Ders kayıt özeti başarıyla getirildi",
            }
        except Exception as exc:
            logger.exception("Error during Course Registration Summary fetch", exc_info=True)
            return {
                "status": "error",
                "message": f"Bağlantı hatası: {exc}",
                "error_code": "COURSE_REG_SUMMARY_SCRAPE_ERROR",
            }

    def _parse_page(self, html: str) -> Dict[str, Any]:
        soup = BeautifulSoup(html, "html.parser")
        return {
            "warning_message": self._parse_warning_message(soup, html),
            "student_approval": self._parse_student_approval(soup),
            "advisor_approval": self._parse_advisor_approval(soup),
            "info_summary": self._parse_info_summary(soup),
            "courses": self._parse_courses(soup),
        }

    def _parse_warning_message(self, soup: BeautifulSoup, html: str) -> str:
        """Extract alert/warning message if present."""
        try:
            info_span = soup.find(id="lblBilgilendirme")
            if info_span:
                text = (info_span.get_text(" ", strip=True) or "").strip()
                if text:
                    return text

            alert_box = soup.find("div", id="divBilgilendirme")
            if alert_box:
                text = (alert_box.get_text(" ", strip=True) or "").strip()
                text = re.sub(r"^\s*uyarı\s*", "", text, flags=re.IGNORECASE).strip()
                if text:
                    return text

            script_match = re.search(r"ProlizMessage\(`(.+?)`,`Uyarı`", html, re.DOTALL)
            if script_match:
                raw = script_match.group(1)
                cleaned = re.sub(r"<br\s*/?>", " ", raw, flags=re.IGNORECASE)
                cleaned = re.sub(r"\s+", " ", cleaned).strip(" `")
                return cleaned.strip()
        except Exception as exc:
            logger.warning("Failed to parse warning message: %s", exc, exc_info=True)
        return ""

    def _parse_student_approval(self, soup: BeautifulSoup) -> str:
        try:
            node = soup.find(id="lblDurum")
            return (node.get_text(" ", strip=True) or "").strip() if node else ""
        except Exception as exc:
            logger.warning("Failed to parse student approval: %s", exc, exc_info=True)
            return ""

    def _parse_advisor_approval(self, soup: BeautifulSoup) -> str:
        try:
            node = soup.find(id="lblDanOnay")
            return (node.get_text(" ", strip=True) or "").strip() if node else ""
        except Exception as exc:
            logger.warning("Failed to parse advisor approval: %s", exc, exc_info=True)
            return ""

    def _parse_info_summary(self, soup: BeautifulSoup) -> Dict[str, str]:
        """
        Parse top info table into a flat dictionary.
        Includes known keys (gpa/general_balance etc.) + additional label/value pairs.
        """
        result: Dict[str, str] = {
            "gpa": "",
            "general_balance": "",
            "previous_balance": "",
            "term_fee": "",
            "total_payable": "",
            "total_paid": "",
        }

        table = soup.find("table", id="tblOgrInfoBar")
        if not table:
            logger.warning("Info summary table tblOgrInfoBar not found.")
            return result

        tbody = table.find("tbody")
        container = tbody if tbody else table
        rows = container.find_all("tr", recursive=False)

        for row in rows:
            try:
                cells = row.find_all("td", recursive=False)
                if not cells:
                    continue

                pairs = [(0, 1), (2, 3)]
                for label_idx, value_idx in pairs:
                    if label_idx >= len(cells) or value_idx >= len(cells):
                        continue

                    label_raw = cells[label_idx].get_text(" ", strip=True) or ""
                    value_raw = cells[value_idx].get_text(" ", strip=True) or ""
                    label_norm = self._normalize(label_raw)
                    value = value_raw.strip()

                    if not label_norm:
                        continue

                    if "genel ortalama" in label_norm:
                        result["gpa"] = value
                        continue
                    if "genel bakiye" in label_norm:
                        result["general_balance"] = value
                        continue
                    if "onceki donem bakiye" in label_norm:
                        result["previous_balance"] = value
                        continue
                    if "donemlik ucret" in label_norm:
                        result["term_fee"] = value
                        continue
                    if "odenmesi gereken toplam ucret" in label_norm:
                        result["total_payable"] = value
                        continue
                    if "odenen toplam ucret" in label_norm:
                        result["total_paid"] = value
                        continue

                    key = self._to_snake_case(label_norm)
                    if key and key not in result:
                        result[key] = value
            except Exception as exc:
                logger.warning("Failed to parse info summary row: %s", exc, exc_info=True)
                continue

        return result

    def _parse_courses(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        table = soup.find("table", id="grdDersKayit")
        if not table:
            for candidate in soup.find_all("table"):
                header_row = self._find_header_row(candidate)
                if header_row and self._detect_header_map(header_row):
                    table = candidate
                    break

        if not table:
            logger.warning("Courses table not found.")
            return []

        header_row = self._find_header_row(table)
        if not header_row:
            logger.warning("Header row not found in courses table.")
            return []

        header_map = self._detect_header_map(header_row)
        if not header_map:
            logger.warning("Courses table with expected headers not found.")
            return []

        tbody = table.find("tbody")
        container = tbody if tbody else table
        rows = container.find_all("tr", recursive=False)

        out: List[Dict[str, Any]] = []
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

                code = cell_text("course_code")
                name = cell_text("course_name")
                if not (code or name):
                    continue

                course = {
                    "course_code": code,
                    "course_name": name,
                    "is_mandatory": self._parse_is_mandatory(cell_text("is_mandatory")),
                    "t_u": cell_text("t_u"),
                    "credit": self._parse_number(cell_text("credit")),
                    "ects": self._parse_number(cell_text("ects")),
                    "class_year": cell_text("class_year"),
                }
                out.append(course)
            except Exception as exc:
                logger.warning("Failed to parse course row: %s", exc, exc_info=True)
                continue

        return out

    @staticmethod
    def _find_header_row(table):
        tbody = table.find("tbody")
        container = tbody if tbody else table
        for tr in container.find_all("tr", recursive=False):
            if tr.find("th", recursive=False):
                return tr
        return None

    def _detect_header_map(self, header_row) -> Optional[Dict[str, int]]:
        cells = header_row.find_all(["th", "td"], recursive=False)
        labels = [self._normalize(c.get_text(" ", strip=True) or "") for c in cells]

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
            "course_code": find_index("ders kod", "course code"),
            "course_name": find_index("ders ad", "course name"),
            "is_mandatory": find_exact("z/s", "zs"),
            "t_u": find_index("t+u", "tu"),
            "credit": find_index("krd", "kredi", "credit"),
            "ects": find_index("akts", "ects"),
            "class_year": find_index("snf", "sinif", "sınıf", "class"),
        }

        if header_map["course_code"] is None and header_map["course_name"] is None:
            return None
        if header_map["credit"] is None and header_map["ects"] is None:
            return None

        return {k: v for k, v in header_map.items() if v is not None}

    @staticmethod
    def _normalize(text: str) -> str:
        lowered = (text or "").strip().lower()
        lowered = lowered.replace("\xa0", " ")
        lowered = lowered.replace("ı", "i").replace("ğ", "g").replace("ş", "s")
        lowered = lowered.replace("ö", "o").replace("ü", "u").replace("ç", "c")
        lowered = re.sub(r"\s+", " ", lowered)
        return lowered.strip()

    def _to_snake_case(self, text: str) -> str:
        cleaned = re.sub(r"[^a-z0-9\s]", " ", text)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned.replace(" ", "_")

    def _parse_is_mandatory(self, text: str) -> Optional[bool]:
        if not text:
            return None
        t = self._normalize(text).upper()
        if t in {"Z", "1"} or "ZORUNLU" in t:
            return True
        if t in {"S", "0", "2"} or "SECMELI" in t:
            return False
        return None

    def _parse_number(self, text: str) -> Optional[float]:
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
