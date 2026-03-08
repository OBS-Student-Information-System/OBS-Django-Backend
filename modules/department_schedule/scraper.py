"""
Scraper for Department Schedule (Bölüm Programı): std_time_table_dep.aspx.

Flow: caller.aspx?curPage=125 -> GET frame. If body has term_id, POST __EVENTTARGET
to change term dropdown then parse. Output: data[class_year][day] = list of lessons.
is_practice detected via DarkGreen color (style or class).
"""
import logging
import re
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup
from core.utils import create_session
from core.tenant_config import get_config

logger = logging.getLogger(__name__)


def _is_session_expired(url: str, text: str) -> bool:
    url_lower = url.lower()
    text_lower = (text or "").lower()
    if "login.aspx" in url_lower or "deferror.aspx" in url_lower:
        return True
    if "oturum süresi doldu" in text_lower or "oturum süresi sona erdi" in text_lower:
        return True
    return False


def _has_dark_green(el) -> bool:
    """Detect practice row/cell via OBS DarkGreen rule."""
    if not el:
        return False
    style = el.get("style") or ""
    cls = " ".join(el.get("class") or [])
    style_lower = style.lower()
    cls_lower = cls.lower()
    if "darkgreen" in style_lower or "dark green" in style_lower:
        return True
    if "green" in style_lower and "color" in style_lower:
        return True
    if "uygulama" in cls_lower or "practice" in cls_lower:
        return True
    return False


class DepartmentScheduleScraper:
    """
    Scraper for Bölüm Programı (std_time_table_dep.aspx).
    Caller pattern; optional term postback; parse by class year then day.
    """

    def __init__(self, session: Optional[Any] = None):
        self.session = session if session else create_session()
        cfg = get_config()
        self._cfg = cfg
        self.caller_url = cfg.scraper.url_for("department_schedule_caller")
        self.frame_url = cfg.scraper.url_for("department_schedule_frame")
        self._default_referer = cfg.default_referer

    def fetch_department_schedule(self, term_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetches department schedule. If term_id is provided, simulates term dropdown
        postback before parsing. Returns standard envelope.
        """
        if not self.session.cookies:
            logger.error("No cookies found, cannot fetch department schedule.")
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
            logger.info("Accessing Department Schedule caller page...")
            self.session.get(self.caller_url, timeout=self._cfg.scraper.timeout_seconds)

            self.session.headers.update({
                "Referer": self.caller_url,
                "Sec-Fetch-Dest": "iframe",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "same-origin",
            })
            logger.info("Fetching Department Schedule frame...")
            resp = self.session.get(self.frame_url, timeout=self._cfg.scraper.timeout_seconds)

            if resp.status_code != 200:
                logger.error("Department schedule frame failed with status %s", resp.status_code)
                return {
                    "status": "error",
                    "message": "Bölüm programı sayfası alınamadı",
                    "error_code": "DEPARTMENT_SCHEDULE_FETCH_ERROR",
                }

            if _is_session_expired(resp.url, resp.text):
                logger.warning("Session expired while fetching department schedule.")
                return {
                    "status": "error",
                    "message": "Oturum süresi doldu",
                    "error_code": "SESSION_EXPIRED",
                }

            html = resp.text
            if term_id:
                html = self._postback_term(html, term_id)
                if html is None:
                    return {
                        "status": "error",
                        "message": "Dönem seçimi yapılamadı",
                        "error_code": "DEPARTMENT_SCHEDULE_TERM_ERROR",
                    }
                if isinstance(html, dict):
                    return html  # session expired or error envelope

            return self._fetch_all_classes(html)

        except Exception as exc:
            logger.exception("Error during Department Schedule fetch", exc_info=True)
            return {
                "status": "error",
                "message": f"Bağlantı hatası: {exc}",
                "error_code": "DEPARTMENT_SCHEDULE_SCRAPE_ERROR",
            }

    def _postback_term(self, html: str, term_id: str) -> Optional[str]:
        """
        Simulate ASP.NET postback to set term dropdown. Returns new HTML or None on failure.
        Returns a dict (error envelope) if session expired after POST.
        """
        soup = BeautifulSoup(html, "html.parser")
        hidden = {}
        for inp in soup.find_all("input", type="hidden"):
            name = inp.get("name")
            if name:
                hidden[name] = inp.get("value", "")

        select = soup.find("select", id="cmbDonemler")
        if not select:
            logger.warning("Term dropdown not found; parsing current page.")
            return html

        dropdown_id = select.get("id")
        options = select.find_all("option", value=True)
        chosen_value = None
        for opt in options:
            if (opt.get("value") or "").strip() == str(term_id).strip():
                chosen_value = opt.get("value")
                break
        if chosen_value is None and options:
            chosen_value = options[0].get("value")

        if chosen_value is None:
            logger.warning("term_id %s not found in dropdown; using current page.", term_id)
            return html

        post_data = {
            **hidden,
            "__EVENTTARGET": dropdown_id,
            "__EVENTARGUMENT": "",
            dropdown_id: chosen_value,
        }

        self.session.headers.update({
            "Referer": self.frame_url,
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
        })
        logger.info("Posting term selection %s for department schedule...", term_id)
        resp = self.session.post(
            self.frame_url,
            data=post_data,
            timeout=self._cfg.scraper.timeout_seconds,
            allow_redirects=True,
        )
        if _is_session_expired(resp.url, resp.text):
            return {"status": "error", "message": "Oturum süresi doldu", "error_code": "SESSION_EXPIRED"}
        return resp.text if resp.status_code == 200 else None

    def _get_form_post_data(self, soup: BeautifulSoup, overrides: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Collect all form data: hidden inputs and selected option for each select (for postback)."""
        out: Dict[str, str] = {}
        for inp in soup.find_all("input", type="hidden"):
            name = inp.get("name")
            if name:
                out[name] = inp.get("value", "")
        for sel in soup.find_all("select", id=True):
            name = sel.get("name") or sel.get("id")
            if not name:
                continue
            selected_opt = next((o for o in sel.find_all("option", value=True) if o.has_attr("selected")), None)
            opt = selected_opt or sel.find("option", value=True)
            if opt:
                out[name] = (opt.get("value") or "").strip()
        if overrides:
            out.update(overrides)
        return out

    def _get_sinif_options_and_selected(self, soup: BeautifulSoup) -> tuple:
        """Returns (list of (value, label), selected_value). Label normalized: '1.Sınıf' -> '1. Sınıf', 0 -> 'Hazırlık'."""
        select = soup.find("select", id="cmbSinif")
        if not select:
            return [], None
        options = []
        selected = None
        for opt in select.find_all("option", value=True):
            val = (opt.get("value") or "").strip()
            text = (opt.get_text(strip=True) or "").strip()
            if val == "0":
                label = "Hazırlık"
            else:
                label = re.sub(r"^(\d+)\.?\s*Sınıf$", r"\1. Sınıf", text, flags=re.I) or text
            options.append((val, label))
            if opt.has_attr("selected"):
                selected = val
        if selected is None and options:
            selected = options[0][0]
        return options, selected

    def _parse_one_class_from_page(self, html: str) -> Dict[str, List[Dict[str, Any]]]:
        """Parse grd0..grd4 from current page into day '1'..'5' lists. Page shows one class only."""
        soup = BeautifulSoup(html, "html.parser")
        day_lessons: Dict[str, List[Dict[str, Any]]] = {str(d): [] for d in range(1, 6)}
        for day_idx in range(5):
            table = soup.find("table", id=f"grd{day_idx}")
            if not table:
                continue
            day_key = str(day_idx + 1)
            try:
                rows = table.find_all("tr")
                for row in rows[1:]:
                    cells = row.find_all("td")
                    if len(cells) < 4:
                        continue
                    lesson = self._row_to_lesson(cells, row)
                    if lesson:
                        day_lessons[day_key].append(lesson)
            except Exception as exc:
                logger.warning("Parse table grd%s failed: %s", day_idx, exc, exc_info=True)
        return day_lessons

    def _fetch_all_classes(self, initial_html: str) -> Dict[str, Any]:
        """
        Page shows one class at a time (cmbSinif). We postback for each class value
        and merge into data[class_label][day]. Uses exact HTML: cmbSinif, grd0..grd4.
        """
        soup = BeautifulSoup(initial_html, "html.parser")
        options, selected_value = self._get_sinif_options_and_selected(soup)
        if not options:
            one = self._parse_one_class_from_page(initial_html)
            return {"status": "success", "data": {"1. Sınıf": one}, "message": "Bölüm programı başarıyla getirildi"}

        data: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
        current_html = initial_html
        current_soup = soup

        for val, label in options:
            if val == selected_value:
                data[label] = self._parse_one_class_from_page(current_html)
                continue
            post_data = self._get_form_post_data(current_soup, overrides={
                "__EVENTTARGET": "cmbSinif",
                "__EVENTARGUMENT": "",
                "cmbSinif": val,
            })
            self.session.headers.update({
                "Referer": self.frame_url,
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "same-origin",
            })
            try:
                resp = self.session.post(
                    self.frame_url,
                    data=post_data,
                    timeout=self._cfg.scraper.timeout_seconds,
                    allow_redirects=True,
                )
            except Exception as exc:
                logger.warning("Postback cmbSinif=%s failed: %s", val, exc, exc_info=True)
                data[label] = {str(d): [] for d in range(1, 6)}
                continue
            if _is_session_expired(resp.url, resp.text):
                return {"status": "error", "message": "Oturum süresi doldu", "error_code": "SESSION_EXPIRED"}
            if resp.status_code != 200:
                data[label] = {str(d): [] for d in range(1, 6)}
                continue
            current_html = resp.text
            current_soup = BeautifulSoup(current_html, "html.parser")
            data[label] = self._parse_one_class_from_page(current_html)

        return {
            "status": "success",
            "data": data,
            "message": "Bölüm programı başarıyla getirildi",
        }

    def _row_to_lesson(self, cells: List, row) -> Optional[Dict[str, Any]]:
        """Build one lesson dict from a table row. Detects is_practice via DarkGreen."""
        try:
            time_str = (cells[0].get_text(strip=True) or "").strip()
            code = (cells[1].get_text(strip=True) if len(cells) > 1 else "").strip()
            name = (cells[2].get_text(strip=True) if len(cells) > 2 else "").strip()
            location = (cells[3].get_text(strip=True) if len(cells) > 3 else "").strip()
            lecturer = (cells[4].get_text(strip=True) if len(cells) > 4 else "").strip()
            is_practice = False
            for cell in cells:
                if _has_dark_green(cell):
                    is_practice = True
                    break
            if not (time_str or code or name):
                return None
            return {
                "time": time_str or "",
                "code": code,
                "name": name,
                "location": location,
                "lecturer": lecturer,
                "is_practice": is_practice,
            }
        except Exception:
            return None
