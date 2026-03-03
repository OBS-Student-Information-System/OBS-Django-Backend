import logging
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup
from core.utils import create_session
from core.tenant_config import get_config
import urllib.parse

logger = logging.getLogger(__name__)


class AdvisorInfoScraper:
    """
    Scraper for the 'Danışman Bilgileri' iframe (ogr_danisman.aspx).

    This page is a static profile card (no grids). We must:
    - Warm up via caller.aspx?curPage=102
    - Fetch ogr_danisman.aspx inside the std frame
    - Extract strongly-typed fields via specific element IDs
    - Normalize the advisor photo URL to an absolute URL
    """

    def __init__(self, session: Optional[Any] = None):
        self.session = session if session else create_session()
        cfg = get_config()
        self._cfg = cfg
        # New endpoints defined in config/tenant.json
        self.caller_url = cfg.scraper.url_for("advisor_info_caller")
        self.frame_url = cfg.scraper.url_for("advisor_info_frame")
        self._default_referer = cfg.default_referer

    def fetch_advisor_info(self) -> Dict[str, Any]:
        """
        Fetches the advisor info frame and parses it into a JSON-friendly dict.

        Returns a dict with:
            status: "success" | "error"
            data: {adi_soyadi, fakulte, bolum, program, telefon, eposta, foto_url}
            message, error_code
        """
        if not self.session.cookies:
            logger.error("No cookies found, cannot fetch advisor info.")
            return {
                "status": "error",
                "message": "Oturum bulunamadı",
                "error_code": "NO_SESSION",
            }

        try:
            # Step 1: Hit caller to initialize OBS internal state
            self.session.headers.update({
                "Referer": self._default_referer,
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "same-origin",
            })
            logger.info("Accessing Advisor Info caller page...")
            self.session.get(self.caller_url, timeout=self._cfg.scraper.timeout_seconds)

            # Step 2: Fetch the actual iframe content
            self.session.headers.update({
                "Referer": self.caller_url,
                "Sec-Fetch-Dest": "iframe",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "same-origin",
            })
            logger.info("Fetching Advisor Info frame...")
            resp = self.session.get(self.frame_url, timeout=self._cfg.scraper.timeout_seconds)

            if resp.status_code != 200:
                logger.error(
                    "Failed to fetch Advisor Info frame. Status code: %s",
                    resp.status_code,
                )
                return {
                    "status": "error",
                    "message": "Danışman bilgileri sayfası alınamadı",
                    "error_code": "ADVISOR_INFO_FETCH_ERROR",
                }

            # Session expiry: redirect to login.aspx
            if "login.aspx" in resp.url.lower():
                logger.warning("Session expired while fetching advisor info.")
                return {
                    "status": "error",
                    "message": "Oturum süresi doldu",
                    "error_code": "SESSION_EXPIRED",
                }

            return self._parse_advisor_info(resp.text)

        except Exception as exc:
            logger.exception("Error during Advisor Info fetch")
            return {
                "status": "error",
                "message": f"Bağlantı hatası: {exc}",
                "error_code": "ADVISOR_INFO_SCRAPE_ERROR",
            }

    def _parse_advisor_info(self, html: str) -> Dict[str, Any]:
        """
        Parses the advisor profile card HTML.

        This page is not a grid; we explicitly target known IDs:
        - imgPhoto, lblAdSoyad, lblFakAd, lblBolum, lblProgram, lblTel, lblEposta

        Missing elements are treated as empty strings to support
        "advisor not assigned" scenarios without crashing.
        """
        soup = BeautifulSoup(html, "html.parser")

        def get_span_text(element_id: str) -> str:
            el = soup.find(id=element_id)
            if not el:
                return ""
            return el.get_text(strip=True)

        try:
            raw_tel = get_span_text("lblTel")
            telefon = raw_tel.strip()

            eposta = get_span_text("lblEposta")

            foto_url = ""
            img = soup.find("img", id="imgPhoto")
            if img and img.get("src"):
                src = img.get("src")
                # Normalize relative URLs like ../zfs.aspx?... to absolute
                foto_url = urllib.parse.urljoin(self._cfg.scraper.base_url + "/", src)

            data = {
                "adi_soyadi": get_span_text("lblAdSoyad"),
                "fakulte": get_span_text("lblFakAd"),
                "bolum": get_span_text("lblBolum"),
                "program": get_span_text("lblProgram"),
                "telefon": telefon,
                "eposta": eposta,
                "foto_url": foto_url,
            }

            logger.info("Successfully parsed Advisor Info.")
            return {
                "status": "success",
                "data": data,
            }

        except Exception as exc:
            logger.exception("Error parsing Advisor Info HTML")
            return {
                "status": "error",
                "message": "Danışman bilgileri ayrıştırma hatası",
                "error_code": "ADVISOR_INFO_PARSE_ERROR",
            }

    def fetch_advisor_schedule(self) -> Dict[str, Any]:
        """
        Fetches the advisor's schedule by simulating __doPostBack('btnYazdir','')
        on the ogr_danisman.aspx frame.

        The returned HTML is parsed using the existing schedule parser so that
        the schema matches the standard ScheduleItem/WeeklySchedule structure.
        """
        if not self.session.cookies:
            logger.error("No cookies found, cannot fetch advisor schedule.")
            return {
                "status": "error",
                "message": "Oturum bulunamadı",
                "error_code": "NO_SESSION",
            }

        try:
            # Step 1: Warm up caller
            self.session.headers.update({
                "Referer": self._default_referer,
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "same-origin",
            })
            logger.info("Accessing Advisor Info caller page for schedule...")
            self.session.get(self.caller_url, timeout=self._cfg.scraper.timeout_seconds)

            # Step 2: Fetch frame to obtain viewstate / hidden fields
            self.session.headers.update({
                "Referer": self.caller_url,
                "Sec-Fetch-Dest": "iframe",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "same-origin",
            })
            logger.info("Fetching Advisor Info frame before schedule postback...")
            frame_resp = self.session.get(
                self.frame_url, timeout=self._cfg.scraper.timeout_seconds
            )
            frame_resp.raise_for_status()

            if "login.aspx" in frame_resp.url.lower():
                logger.warning("Session expired while preparing advisor schedule.")
                return {
                    "status": "error",
                    "message": "Oturum süresi doldu",
                    "error_code": "SESSION_EXPIRED",
                }

            soup = BeautifulSoup(frame_resp.text, "html.parser")
            hidden_fields = {}
            for hidden in soup.find_all("input", type="hidden"):
                name = hidden.get("name")
                if name:
                    hidden_fields[name] = hidden.get("value", "")

            # Step 3: Simulate __doPostBack('btnYazdir','')
            post_data = {
                **hidden_fields,
                "__EVENTTARGET": "btnYazdir",
                "__EVENTARGUMENT": "",
            }

            self.session.headers.update({
                "Referer": self.frame_url,
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "same-origin",
            })
            logger.info("Posting btnYazdir to fetch advisor schedule...")
            resp = self.session.post(
                self.frame_url,
                data=post_data,
                timeout=self._cfg.scraper.timeout_seconds,
                allow_redirects=True,
            )
            resp.raise_for_status()

            if "login.aspx" in resp.url.lower():
                logger.warning("Session expired during advisor schedule fetch.")
                return {
                    "status": "error",
                    "message": "Oturum süresi doldu",
                    "error_code": "SESSION_EXPIRED",
                }

            schedule = self._parse_advisor_schedule_html(resp.text)
            return {
                "status": "success",
                "data": schedule,
            }

        except Exception as exc:
            logger.exception("Error fetching advisor schedule")
            return {
                "status": "error",
                "message": f"Danışman ders programı alınamadı: {exc}",
                "error_code": "ADVISOR_SCHEDULE_FETCH_ERROR",
            }

    def _parse_advisor_schedule_html(self, html: str) -> Dict[str, Any]:
        """
        Parses the advisor timetable HTML (oe_time_table.aspx) into the same
        WeeklySchedule JSON shape used by the student schedule endpoint.

        OBS renders one table per day:
          grd0 -> Monday ("1"), grd1 -> Tuesday ("2"), ..., grd5 -> Saturday ("6")
        Each table has columns: Saat, Ders Kodu, Ders Adı, Derslik.
        """
        soup = BeautifulSoup(html, "html.parser")
        schedule: Dict[str, Any] = {}

        # Map table index to string day key used in frontend (1..6)
        for idx in range(6):
            table = soup.find("table", id=f"grd{idx}")
            if not table:
                continue

            rows = table.find_all("tr")
            if len(rows) <= 1:
                continue

            lessons = []
            for row in rows[1:]:
                cells = row.find_all("td")
                if len(cells) < 4:
                    continue

                time = cells[0].get_text(strip=True)
                code = cells[1].get_text(strip=True)
                name = cells[2].get_text(strip=True)
                location = cells[3].get_text(strip=True)

                if not (time or code or name or location):
                    continue

                lessons.append(
                    {
                        "time": time,
                        "code": code,
                        "name": name,
                        "location": location,
                        # Lecturer bilgisi tabloda ayrıca yok; opsiyonel olduğu için boş bırakıyoruz.
                        "lecturer": "",
                        "is_practice": False,
                    }
                )

            if lessons:
                day_key = str(idx + 1)  # "1".."6"
                schedule[day_key] = lessons

        return schedule

