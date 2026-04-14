import logging
import re
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup

from core.tenant_config import get_config
from core.utils import create_session

logger = logging.getLogger(__name__)


def _normalize(text: str) -> str:
    value = (text or "").strip().lower()
    value = value.replace("ı", "i")
    value = value.replace("ğ", "g").replace("ş", "s")
    value = value.replace("ö", "o").replace("ü", "u").replace("ç", "c")
    value = re.sub(r"\s+", " ", value)
    return value


def _is_session_expired(url: str, text: str) -> bool:
    url_lower = (url or "").lower()
    text_lower = _normalize(text or "")
    if "login.aspx" in url_lower or "deferror.aspx" in url_lower:
        return True
    return "oturum suresi doldu" in text_lower or "oturum suresi sona erdi" in text_lower


def _extract_first_number(text: str) -> str:
    match = re.search(r"([0-9]+(?:[.,][0-9]+)?)", text or "")
    return match.group(1) if match else ""


def _parse_summary_metrics(text: str) -> Dict[str, str]:
    normalized = (text or "").replace("\xa0", " ")
    values: Dict[str, str] = {
        "general_credit": "",
        "general_ects": "",
        "gpa": "",
        "passed_credit": "",
        "passed_ects": "",
        "excluded_credit": "",
        "excluded_ects": "",
    }

    general_match = re.search(
        r"Genel\s*Kredi\s*:\s*([0-9.,]+)\s*AKTS\s*:\s*([0-9.,]+)\s*Genel\s*Ort\s*:\s*([0-9.,]+)",
        normalized,
        flags=re.IGNORECASE,
    )
    if general_match:
        values["general_credit"] = general_match.group(1)
        values["general_ects"] = general_match.group(2)
        values["gpa"] = general_match.group(3)

    passed_match = re.search(
        r"Başarılı\s*Olunan\s*Kredi\s*:\s*([0-9.,]+)\s*AKTS\s*:\s*([0-9.,]+)",
        normalized,
        flags=re.IGNORECASE,
    )
    if passed_match:
        values["passed_credit"] = passed_match.group(1)
        values["passed_ects"] = passed_match.group(2)

    excluded_match = re.search(
        r"Dahil\s*Olmayan\s*Toplam\s*Kredi\s*:\s*([0-9.,]+)\s*AKTS\s*:\s*([0-9.,]+)",
        normalized,
        flags=re.IGNORECASE,
    )
    if excluded_match:
        values["excluded_credit"] = excluded_match.group(1)
        values["excluded_ects"] = excluded_match.group(2)

    return values


class CurriculumStatusScraper:
    def __init__(self, session: Optional[Any] = None):
        self.session = session if session else create_session()
        cfg = get_config()
        self._cfg = cfg
        self.caller_url = cfg.scraper.url_for("curriculum_status_caller")
        self.frame_url = cfg.scraper.url_for("curriculum_status_frame")
        self._default_referer = cfg.default_referer

    def fetch_curriculum_status(self) -> Dict[str, Any]:
        if not self.session.cookies:
            logger.error("No cookies found for curriculum status.")
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
            caller_resp = self.session.get(
                self.caller_url,
                timeout=self._cfg.scraper.timeout_seconds,
                allow_redirects=True,
            )
            if _is_session_expired(caller_resp.url, caller_resp.text):
                logger.warning("Session expired on curriculum caller page.")
                return {
                    "status": "error",
                    "message": "Oturum süresi doldu",
                    "error_code": "SESSION_EXPIRED",
                }

            self.session.headers.update(
                {
                    "Referer": self.caller_url,
                    "Sec-Fetch-Dest": "iframe",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "same-origin",
                }
            )
            frame_resp = self.session.get(
                self.frame_url,
                timeout=self._cfg.scraper.timeout_seconds,
                allow_redirects=True,
            )
            if frame_resp.status_code != 200:
                logger.error(
                    "Curriculum frame failed with status %s",
                    frame_resp.status_code,
                )
                return {
                    "status": "error",
                    "message": "Müfredat durumu sayfası alınamadı",
                    "error_code": "FETCH_FAILED",
                }

            if _is_session_expired(frame_resp.url, frame_resp.text):
                logger.warning("Session expired on curriculum frame page.")
                return {
                    "status": "error",
                    "message": "Oturum süresi doldu",
                    "error_code": "SESSION_EXPIRED",
                }

            parsed = self._parse_curriculum_page(frame_resp.text)
            return {
                "status": "success",
                "data": parsed,
                "message": "Müfredat durumu başarıyla getirildi",
            }
        except Exception as exc:
            logger.exception(
                "Curriculum status scraping failed",
                extra={"error": str(exc)},
            )
            return {
                "status": "error",
                "message": "Müfredat durumu alınırken hata oluştu",
                "error_code": "CURRICULUM_STATUS_FETCH_ERROR",
            }

    def _parse_curriculum_page(self, html: str) -> Dict[str, Any]:
        soup = BeautifulSoup(html, "html.parser")

        student_name = (soup.find(id="lblAdSoyad") or {}).get_text(strip=True) if soup.find(id="lblAdSoyad") else ""
        curriculum_name = (soup.find(id="lblMufredatAd") or {}).get_text(strip=True) if soup.find(id="lblMufredatAd") else ""

        metrics = _parse_summary_metrics(
            " ".join(
                [
                    (soup.find(id="lblToplamKrediAKTSBilgileriSag") or {}).get_text(" ", strip=True)
                    if soup.find(id="lblToplamKrediAKTSBilgileriSag")
                    else "",
                    (soup.find(id="lblToplamKrediAKTSBilgileri") or {}).get_text(" ", strip=True)
                    if soup.find(id="lblToplamKrediAKTSBilgileri")
                    else "",
                    (soup.find(id="lblToplamKrediAKTSDisiBilgileri") or {}).get_text(" ", strip=True)
                    if soup.find(id="lblToplamKrediAKTSDisiBilgileri")
                    else "",
                ]
            )
        )

        terms = self._parse_terms(soup)
        legend = self._parse_legend(soup)

        return {
            "student_name": student_name,
            "curriculum_name": curriculum_name,
            "overall": metrics,
            "terms": terms,
            "legend": legend,
        }

    def _parse_terms(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        grid = soup.find(id="grd_ders")
        if not grid:
            logger.error("grd_ders table not found while parsing curriculum.")
            return []

        rows = grid.find_all("tr")
        terms: List[Dict[str, Any]] = []
        current_term: Optional[Dict[str, Any]] = None

        for row in rows:
            text = row.get_text(" ", strip=True)
            if not text:
                continue

            cells = row.find_all("td")
            if len(cells) == 1 and cells[0].get("colspan") == "9":
                if "Sınıf" in text and ("Güz" in text or "Bahar" in text):
                    current_term = {
                        "term_name": text,
                        "summary": {
                            "term_required_credit": "",
                            "term_required_ects": "",
                            "course_count": "",
                            "required_count": "",
                            "elective_count": "",
                        },
                        "courses": [],
                    }
                    terms.append(current_term)
                    continue

                if text.startswith("Müfredat Toplam") and current_term is not None:
                    current_term["summary"] = self._parse_term_summary(text)
                    continue

            code_el = row.find("span", id=re.compile(r"^grd_ders_Label1_\d+$"))
            name_el = row.find("span", id=re.compile(r"^grd_ders_lblMufDersAd_\d+$"))
            if not code_el or not name_el or current_term is None:
                continue

            zs_raw = cells[2].get_text(strip=True) if len(cells) > 2 else ""
            credit_raw = cells[3].get_text(strip=True) if len(cells) > 3 else ""
            ects_raw = cells[4].get_text(strip=True) if len(cells) > 4 else ""

            taken_el = row.find("span", id=re.compile(r"^grd_ders_lblAlinanDers_\d+$"))
            taken_text = taken_el.get_text(" ", strip=True) if taken_el else ""

            icon = taken_el.find("i") if taken_el else None
            icon_class = " ".join(icon.get("class", [])) if icon else ""
            icon_title = (icon.get("title") or "").strip() if icon else ""

            course = {
                "curriculum_course_code": code_el.get_text(strip=True),
                "curriculum_course_name": name_el.get_text(strip=True),
                "zs_type": zs_raw,
                "credit": credit_raw,
                "ects": ects_raw,
                "taken_course_text": taken_text,
                "taken_term_code": self._extract_taken_term_code(taken_text),
                "letter": self._extract_letter(taken_text),
                "status": self._resolve_status(icon_class, icon_title, taken_text),
                "is_grouped": row.get("title") == "Gruplanmış Ders",
            }
            current_term["courses"].append(course)

        return terms

    def _parse_term_summary(self, text: str) -> Dict[str, str]:
        return {
            "term_required_credit": self._match_field(text, r"Kredi\s*:\s*([0-9.,]+)"),
            "term_required_ects": self._match_field(text, r"AKTS\s*:\s*([0-9.,]+)"),
            "course_count": self._match_field(text, r"Ders\s*Say\s*:\s*([0-9.,]+)"),
            "required_count": self._match_field(text, r"Zorunlu\s*:\s*([0-9.,]+)"),
            "elective_count": self._match_field(text, r"Seçmeli\s*:\s*([0-9.,]+)"),
        }

    def _match_field(self, text: str, pattern: str) -> str:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        return match.group(1).strip() if match else ""

    def _extract_taken_term_code(self, text: str) -> str:
        match = re.search(r"\[([^\]]+)\]", text or "")
        return match.group(1) if match else ""

    def _extract_letter(self, text: str) -> str:
        if not text:
            return ""
        tokens = re.findall(r"\b[A-Z][A-Z0-9]?\b", (text or "").upper())
        if not tokens:
            return ""
        last = tokens[-1]
        if last in {"Z", "S"}:
            return ""
        return last

    def _resolve_status(self, icon_class: str, icon_title: str, taken_text: str) -> str:
        classes = (icon_class or "").lower()
        title = _normalize(icon_title)
        if "text-success" in classes or "basarili" in title:
            return "passed"
        if "text-danger" in classes or "basarisiz" in title:
            return "failed"
        if "text-warning" in classes:
            return "active_or_excluded"
        if "text-primary" in classes or "muaf" in title:
            return "exempt"
        if "text-secondary" in classes:
            return "pending_or_not_taken"
        if not (taken_text or "").strip():
            return "pending_or_not_taken"
        return "pending_or_not_taken"

    def _parse_legend(self, soup: BeautifulSoup) -> Dict[str, str]:
        return {
            "failed": self._legend_text(soup, "lblBasarisizDersler"),
            "exempt": self._legend_text(soup, "lblMuafDersler"),
            "passed": self._legend_text(soup, "lblBasarilanDersler"),
            "pending": self._legend_text(soup, "lblSonuclanmayanDersler"),
            "active_or_excluded": self._legend_text(soup, "Label4"),
        }

    def _legend_text(self, soup: BeautifulSoup, element_id: str) -> str:
        el = soup.find(id=element_id)
        return el.get_text(" ", strip=True) if el else ""
