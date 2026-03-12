"""
Scraper for Enrolled Courses (Alınan Dersler): ogr_alinan_dersler.aspx.

Flow: caller.aspx?curPage=103 -> GET frame. If body has term_id, POST __EVENTTARGET
to change term dropdown before parsing. Output: list of enrolled course dicts.
"""
import logging
from typing import Dict, Any, List, Optional

from bs4 import BeautifulSoup

from core.utils import create_session
from core.tenant_config import get_config

logger = logging.getLogger(__name__)


def _is_session_expired(url: str, text: str) -> bool:
    """Detect OBS session expiry by URL or common messages."""
    url_lower = (url or "").lower()
    text_lower = (text or "").lower()
    if "login.aspx" in url_lower or "deferror.aspx" in url_lower:
        return True
    if "oturum süresi doldu" in text_lower or "oturum süresi sona erdi" in text_lower:
        return True
    return False


class EnrolledCoursesScraper:
    """
    Scraper for Alınan Dersler (ogr_alinan_dersler.aspx).
    Caller pattern; optional term postback; parses defensive table structure.
    """

    def __init__(self, session: Optional[Any] = None):
        self.session = session if session else create_session()
        cfg = get_config()
        self._cfg = cfg
        self.caller_url = cfg.scraper.url_for("enrolled_courses_caller")
        self.frame_url = cfg.scraper.url_for("enrolled_courses_frame")
        self._default_referer = cfg.default_referer

    def fetch_enrolled_courses(self, term_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetch enrolled courses. If term_id is provided, simulates term dropdown
        postback before parsing. Returns standard envelope.
        """
        if not self.session.cookies:
            logger.error("No cookies found, cannot fetch enrolled courses.")
            return {
                "status": "error",
                "message": "Oturum bulunamadı",
                "error_code": "NO_SESSION",
            }

        try:
            # Step 1: Access caller page (required OBS navigation flow)
            self.session.headers.update(
                {
                    "Referer": self._default_referer,
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "same-origin",
                }
            )
            logger.info("Accessing Enrolled Courses caller page...")
            self.session.get(
                self.caller_url, timeout=self._cfg.scraper.timeout_seconds
            )

            # Step 2: Load iframe frame with enrolled courses content
            self.session.headers.update(
                {
                    "Referer": self.caller_url,
                    "Sec-Fetch-Dest": "iframe",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "same-origin",
                }
            )
            logger.info("Fetching Enrolled Courses frame...")
            resp = self.session.get(
                self.frame_url,
                timeout=self._cfg.scraper.timeout_seconds,
                allow_redirects=True,
            )

            if resp.status_code != 200:
                logger.error(
                    "Enrolled courses frame failed with status %s", resp.status_code
                )
                return {
                    "status": "error",
                    "message": "Alınan dersler sayfası alınamadı",
                    "error_code": "ENROLLED_COURSES_FETCH_ERROR",
                }

            if _is_session_expired(resp.url, resp.text):
                logger.warning("Session expired while fetching enrolled courses.")
                return {
                    "status": "error",
                    "message": "Oturum süresi doldu",
                    "error_code": "SESSION_EXPIRED",
                }

            html = resp.text
            if term_id:
                html = self._postback_term(html, term_id)
                if isinstance(html, dict):
                    # Already an error envelope (e.g. session expired)
                    return html

            courses = self._parse_enrolled_courses(html)
            return {
                "status": "success",
                "data": courses,
                "message": "Alınan dersler başarıyla getirildi",
            }

        except Exception as exc:
            logger.exception("Error during Enrolled Courses fetch", exc_info=True)
            return {
                "status": "error",
                "message": f"Bağlantı hatası: {exc}",
                "error_code": "ENROLLED_COURSES_SCRAPE_ERROR",
            }

    def _postback_term(self, html: str, term_id: str) -> Any:
        """
        Simulate ASP.NET postback to set term dropdown.
        Returns new HTML, original HTML on graceful fallback, or
        an error envelope dict on session expiry.
        """
        soup = BeautifulSoup(html, "html.parser")
        hidden: Dict[str, str] = {}
        for inp in soup.find_all("input", type="hidden"):
            name = inp.get("name")
            if name:
                hidden[name] = inp.get("value", "")

        cfg = self._cfg
        sel = cfg.selectors
        dropdown_id = sel.get("TERM_DROPDOWN") or sel.get("term_dropdown")

        term_select = None
        if dropdown_id:
            term_select = soup.find("select", id=dropdown_id) or soup.find(
                "select", attrs={"name": dropdown_id}
            )

        if not term_select:
            logger.warning(
                "Term dropdown not found on enrolled courses page; parsing current page."
            )
            return html

        options = term_select.find_all("option", value=True)
        chosen_value: Optional[str] = None
        for opt in options:
            if (opt.get("value") or "").strip() == str(term_id).strip():
                chosen_value = opt.get("value")
                break

        if chosen_value is None and options:
            chosen_value = options[0].get("value")

        if chosen_value is None:
            logger.warning(
                "term_id %s not found in enrolled courses dropdown; using current page.",
                term_id,
            )
            return html

        post_data = {
            **hidden,
            "__EVENTTARGET": dropdown_id,
            "__EVENTARGUMENT": "",
            dropdown_id: chosen_value,
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
        logger.info("Posting term selection %s for enrolled courses...", term_id)
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
        return resp.text if resp.status_code == 200 else html

    def _parse_enrolled_courses(self, html: str) -> List[Dict[str, Any]]:
        """
        Parse enrolled courses table into list of dicts.

        Strategy:
        1. Target `id="grdGenel"` directly to avoid nested-table index shift.
        2. Use `recursive=False` for cell extraction (direct children only).
        3. Skip footer/pager rows (colspan cells).
        4. Fall back to generic table scan if grdGenel is absent.
        """
        soup = BeautifulSoup(html, "html.parser")

        table = soup.find("table", id="grdGenel")
        if not table:
            tables = soup.find_all("table")
            for t in tables:
                hdr = self._find_header_row(t)
                if hdr and self._detect_header_map(hdr):
                    table = t
                    break

        if not table:
            logger.warning("No tables found on enrolled courses page.")
            return []

        tbody = table.find("tbody")
        container = tbody if tbody else table
        all_rows = container.find_all("tr", recursive=False)

        header_row = self._find_header_row(table)
        if not header_row:
            logger.warning("Header row not found in enrolled courses table.")
            return []

        header_map = self._detect_header_map(header_row)
        if not header_map:
            logger.warning("Enrolled courses table with expected headers not found.")
            return []

        target_rows = []
        for tr in all_rows:
            if tr is header_row:
                continue
            tds = tr.find_all("td", recursive=False)
            if not tds:
                continue
            if any(td.get("colspan") for td in tds):
                continue
            target_rows.append(tr)

        if not target_rows:
            logger.info("No data rows found in enrolled courses table.")
            return []

        courses: List[Dict[str, Any]] = []
        for row in target_rows:
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

                is_mandatory = self._parse_is_mandatory(cell_text("is_mandatory"))
                credit = self._parse_number(cell_text("credit"))
                ects = self._parse_number(cell_text("ects"))
                t_u = cell_text("t_u")
                class_year = cell_text("class_year")
                instructor = cell_text("instructor")
                status_text = cell_text("status_text")
                grade_raw = cell_text("grade").strip()
                grade = (
                    grade_raw
                    if grade_raw and grade_raw not in ("-", "--", "—")
                    else "-"
                )

                courses.append(
                    {
                        "course_code": course_code,
                        "course_name": course_name,
                        "is_mandatory": is_mandatory,
                        "credit": credit,
                        "ects": ects,
                        "t_u": t_u,
                        "class_year": class_year,
                        "instructor": instructor,
                        "status_text": status_text,
                        "grade": grade,
                    }
                )
            except Exception as exc:
                logger.warning(
                    "Failed to parse enrolled course row: %s", exc, exc_info=True
                )
                continue

        return courses

    @staticmethod
    def _find_header_row(table):
        """Return the first <tr> containing <th> elements (direct children)."""
        tbody = table.find("tbody")
        container = tbody if tbody else table
        for tr in container.find_all("tr", recursive=False):
            if tr.find("th", recursive=False):
                return tr
        return None

    def _detect_header_map(self, header_row) -> Optional[Dict[str, int]]:
        """
        Inspect header cells and map logical keys to column indices.
        Uses `recursive=False` to avoid picking up nested elements.
        """
        cells = header_row.find_all(["th", "td"], recursive=False)
        labels = [(c.get_text(strip=True) or "").lower() for c in cells]

        def find_index(*keywords: str) -> Optional[int]:
            for i, label in enumerate(labels):
                for kw in keywords:
                    if kw in label:
                        return i
            return None

        header_map: Dict[str, int] = {}
        header_map["course_code"] = find_index("ders kod", "course code")
        header_map["course_name"] = find_index("ders ad", "course name")
        header_map["is_mandatory"] = find_index("z/s", "zorunlu", "seçmeli", "secmeli")
        header_map["credit"] = find_index("krd", "kredi", "credit")
        header_map["ects"] = find_index("akts", "ects")
        header_map["t_u"] = find_index("t+u", "t/u", "teorik", "uygulama")
        header_map["class_year"] = find_index("snf", "sınıf", "sinif", "yıl", "yil")
        header_map["instructor"] = find_index(
            "öğretim elemanı", "ogretim elemani", "öğr. gör", "ogr. gor",
            "öğretim el", "instructor",
        )
        header_map["status_text"] = find_index("durum", "status")
        header_map["grade"] = find_index("not", "harf", "notu", "grade")

        if header_map["course_code"] is None and header_map["course_name"] is None:
            return None
        if header_map["credit"] is None and header_map["ects"] is None:
            return None

        return header_map

    def _parse_is_mandatory(self, text: str) -> Optional[bool]:
        """Map 'Z/S' style text to boolean."""
        if not text:
            return None
        t = text.strip().upper()
        if t.startswith("Z") or "ZORUNLU" in t:
            return True
        if t.startswith("S") or "SEÇMELİ" in t or "SECMELI" in t:
            return False
        return None

    def _parse_number(self, text: str) -> Optional[float]:
        """Parse numeric text like '4', '6,0' into float/int where possible."""
        if not text:
            return None
        cleaned = text.replace(",", ".").strip()
        try:
            if cleaned.isdigit():
                return int(cleaned)
            return float(cleaned)
        except ValueError:
            return None

