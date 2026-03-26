"""
Interactive Transcript (Native Transcript) Scraper.

Caller pattern:
  caller.aspx?curPage=204 -> v_transkript.aspx (iframe)

This page uses a "left/right challenge" where Fall/Spring are split
into left/right columns. We flatten it into a single list of terms:
  - term_name (e.g., "2024-2025 Güz")
  - term_gpa (ANO)
  - term_ects (Dönem AKTS)
  - courses[]
     - course_code, course_name, credit, ects, score (Ort), letter_grade (Harf)
     - status: failed/exempt/replaced/normal
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from bs4 import BeautifulSoup

from core.tenant_config import get_config
from core.utils import create_session

logger = logging.getLogger(__name__)


def _is_session_expired(url: str, text: str) -> bool:
    url_lower = (url or "").lower()
    text_lower = (text or "").lower()
    if "login.aspx" in url_lower or "deferror.aspx" in url_lower:
        return True
    if "oturum süresi doldu" in text_lower or "oturum süresi sona erdi" in text_lower:
        return True
    return False


def _normalize_for_search(text: str) -> str:
    lowered = (text or "").strip().lower()
    lowered = lowered.replace("ı", "i")
    lowered = lowered.replace("ğ", "g").replace("ş", "s").replace("ö", "o")
    lowered = lowered.replace("ü", "u").replace("ç", "c")
    lowered = re.sub(r"\s+", " ", lowered)
    return lowered


def _parse_color_from_style(style: Optional[str]) -> Optional[str]:
    if not style:
        return None
    m = re.search(r"color\s*:\s*([^;]+)", style, flags=re.IGNORECASE)
    if not m:
        return None
    return (m.group(1) or "").strip()


def _parse_rgb(color_value: str) -> Optional[Tuple[int, int, int]]:
    if not color_value:
        return None

    c = color_value.strip().lower()
    if c.startswith("#"):
        hexv = c[1:]
        if len(hexv) == 3:
            r = int(hexv[0] * 2, 16)
            g = int(hexv[1] * 2, 16)
            b = int(hexv[2] * 2, 16)
            return (r, g, b)
        if len(hexv) == 6:
            r = int(hexv[0:2], 16)
            g = int(hexv[2:4], 16)
            b = int(hexv[4:6], 16)
            return (r, g, b)
        return None

    m = re.match(r"rgb\s*\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*\)", c)
    if m:
        r, g, b = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
        return (r, g, b)

    # Common named colors (minimal set).
    if "steelblue" in c or "dodgerblue" in c or "royalblue" in c:
        # Not exact, but enough for semantic mapping.
        return (70, 130, 180)

    return None


def _classify_status_from_color(color_value: Optional[str]) -> Optional[str]:
    """
    Map inline color -> semantic status.

    Returns: failed/exempt/replaced/None
    """
    rgb = _parse_rgb(color_value or "")
    if not rgb:
        return None

    r, g, b = rgb
    # Red-ish
    if r > 150 and r > g + 50 and r > b + 50:
        return "failed"
    # Blue-ish
    if b > 150 and b > r + 40 and b > g + 20:
        return "exempt"
    # Orange-ish
    if r > 180 and g > 80 and b < 120 and r > g and g > b:
        return "replaced"

    return None


class InteractiveTranscriptScraper:
    def __init__(self, session: Optional[Any] = None):
        self.session = session if session else create_session()
        cfg = get_config()
        self._cfg = cfg
        self.caller_url = cfg.scraper.url_for("interactive_transcript_caller")
        self.frame_url = cfg.scraper.url_for("interactive_transcript_frame")
        self._default_referer = cfg.default_referer

    def fetch_interactive_transcript(self) -> Dict[str, Any]:
        if not self.session.cookies:
            logger.error("No cookies found, cannot fetch interactive transcript.")
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
            logger.info("Accessing interactive transcript caller page...")
            self.session.get(self.caller_url, timeout=self._cfg.scraper.timeout_seconds)

            self.session.headers.update(
                {
                    "Referer": self.caller_url,
                    "Sec-Fetch-Dest": "iframe",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "same-origin",
                }
            )
            logger.info("Fetching interactive transcript frame...")
            resp = self.session.get(
                self.frame_url,
                timeout=self._cfg.scraper.timeout_seconds,
                allow_redirects=True,
            )

            if resp.status_code != 200:
                logger.error(
                    "Interactive transcript frame failed with status %s",
                    resp.status_code,
                )
                return {
                    "status": "error",
                    "message": "İnteraktif transkript sayfası alınamadı",
                    "error_code": "INTERACTIVE_TRANSCRIPT_FETCH_ERROR",
                }

            if _is_session_expired(resp.url, resp.text):
                logger.warning("Session expired while fetching interactive transcript.")
                return {
                    "status": "error",
                    "message": "Oturum süresi doldu",
                    "error_code": "SESSION_EXPIRED",
                }

            data = self._parse_page(resp.text)
            return {
                "status": "success",
                "data": data,
                "message": "İnteraktif transkript başarıyla getirildi",
            }
        except Exception as exc:
            logger.exception(
                "Error during interactive transcript fetch",
                exc_info=True,
            )
            return {
                "status": "error",
                "message": f"Bağlantı hatası: {exc}",
                "error_code": "INTERACTIVE_TRANSCRIPT_SCRAPE_ERROR",
            }

    def _parse_page(self, html: str) -> Dict[str, Any]:
        soup = BeautifulSoup(html, "html.parser")
        overall = self._parse_overall_header(soup)
        terms = self._parse_terms(soup)
        return {
            "cgpa": overall.get("cgpa", ""),
            "total_ects": overall.get("total_ects", ""),
            "terms": terms,
        }

    def _parse_overall_header(self, soup: BeautifulSoup) -> Dict[str, str]:
        def by_id(*ids: str) -> str:
            for _id in ids:
                el = soup.find(id=_id)
                if el:
                    v = (el.get_text(strip=True) or "").strip()
                    if v and v not in {"-", "--", "—"}:
                        return v
            return ""

        # IDs observed in samples: lblAGNO2, lblGenelAKTSToplami2
        cgpa = by_id("lblAGNO2", "lblAGNO")
        total_ects = by_id(
            "lblGenelAKTSToplami2",
            "lblGenelAKTSToplami",
            "lblKrediAkts2",
            "lblKrediAkts",
        )
        return {"cgpa": cgpa, "total_ects": total_ects}

    def _get_baslik_table_from_tr(self, tr) -> Optional[BeautifulSoup]:
        for td in tr.find_all("td", recursive=False):
            if not td.get("colspan"):
                continue
            baslik = td.find("table", attrs={"name": "baslik"})
            if baslik:
                return baslik
        return None

    def _parse_term_header_from_baslik(
        self, baslik_table
    ) -> Tuple[Optional[str], Optional[str]]:
        tr = baslik_table.find("tr")
        if tr:
            tds = tr.find_all("td", recursive=False)
        else:
            tds = baslik_table.find_all("td")

        if len(tds) < 2:
            return None, None

        left = (tds[0].get_text(" ", strip=True) or "").strip()
        right = (tds[1].get_text(" ", strip=True) or "").strip()
        left = left if left else None
        right = right if right else None
        return left, right

    def _extract_ano_and_donem_akts(self, text: str) -> Tuple[str, str]:
        """
        Return (term_gpa, term_ects) from a summary-side text.
        Expected fragments:
          ANO: 3,06
          Dönem AKTS: 30
        """
        norm = _normalize_for_search(text)

        # ANO
        ano_match = re.search(r"ano\s*:\s*([0-9]+(?:[.,][0-9]+)?)", norm, flags=re.IGNORECASE)
        ano = (ano_match.group(1) if ano_match else "").strip()

        # Dönem AKTS
        akts_match = re.search(
            r"donem\s*akts\s*:\s*([0-9]+(?:[.,][0-9]+)?)",
            norm,
            flags=re.IGNORECASE,
        )
        donem_akts = (akts_match.group(1) if akts_match else "").strip()
        return ano, donem_akts

    def _parse_terms(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        table = soup.find("table", id="grd_genel")
        if not table:
            logger.warning("grd_genel table not found on interactive transcript page.")
            return []

        tbody = table.find("tbody")
        container = tbody if tbody else table
        outer_rows = container.find_all("tr", recursive=False)

        terms: List[Dict[str, Any]] = []
        active_left_idx: Optional[int] = None
        active_right_idx: Optional[int] = None

        left_code_prefix = re.compile(r"^grd_genel_btnDersKod_\d+")
        right_code_prefix = re.compile(r"^grd_genel_btnDersKod2_\d+")

        left_name_prefix = re.compile(r"^grd_genel_lblDersAd_\d+")
        right_name_prefix = re.compile(r"^grd_genel_lblDersAd2_\d+")

        left_credit_prefix = re.compile(r"^grd_genel_lblKredi_\d+")
        right_credit_prefix = re.compile(r"^grd_genel_lblKredi2_\d+")

        left_ects_prefix = re.compile(r"^grd_genel_lblAKTS_\d+")
        right_ects_prefix = re.compile(r"^grd_genel_lblAKTS2_\d+")

        left_score_prefix = re.compile(r"^grd_genel_lblOrt_\d+")
        right_score_prefix = re.compile(r"^grd_genel_lblOrt2_\d+")

        left_letter_prefix = re.compile(r"^grd_genel_lblHarf_\d+")
        right_letter_prefix = re.compile(r"^grd_genel_lblHarf2_\d+")

        def _find_first_by_id_regex(tr, id_regex: re.Pattern) -> Optional[Any]:
            el = tr.find(lambda tag: tag and tag.name in {"span", "a"} and tag.get("id") and id_regex.match(tag.get("id")))
            return el

        for tr in outer_rows:
            baslik_table = self._get_baslik_table_from_tr(tr)
            if baslik_table:
                baslik_text = baslik_table.get_text(" ", strip=True)
                # Summary row: includes ANO: and Dönem AKTS:
                if "ano" in _normalize_for_search(baslik_text) and "akts" in _normalize_for_search(baslik_text):
                    left_term_text, right_term_text = self._extract_term_summary_sides(baslik_table)
                    if active_left_idx is not None and left_term_text:
                        term_gpa, term_ects = self._extract_ano_and_donem_akts(left_term_text)
                        terms[active_left_idx]["term_gpa"] = term_gpa
                        terms[active_left_idx]["term_ects"] = term_ects
                    if active_right_idx is not None and right_term_text:
                        term_gpa, term_ects = self._extract_ano_and_donem_akts(right_term_text)
                        terms[active_right_idx]["term_gpa"] = term_gpa
                        terms[active_right_idx]["term_ects"] = term_ects
                    continue

                # Term header row: contains e.g. "2024-2025 Güz/Bahar/Muaf"
                left_name, right_name = self._parse_term_header_from_baslik(baslik_table)
                # Reset active indices on each header.
                active_left_idx = None
                active_right_idx = None
                if left_name:
                    active_left_idx = len(terms)
                    terms.append(
                        {
                            "term_name": left_name,
                            "term_gpa": "",
                            "term_ects": "",
                            "courses": [],
                        }
                    )
                if right_name:
                    active_right_idx = len(terms)
                    terms.append(
                        {
                            "term_name": right_name,
                            "term_gpa": "",
                            "term_ects": "",
                            "courses": [],
                        }
                    )
                continue

            # Course data row: detect by existence of code links.
            left_code_el = _find_first_by_id_regex(tr, left_code_prefix)
            right_code_el = _find_first_by_id_regex(tr, right_code_prefix)
            if not left_code_el and not right_code_el:
                continue

            # Parse left side course
            if left_code_el and active_left_idx is not None:
                course = self._parse_course_from_row_side(
                    tr=tr,
                    side="left",
                    code_el=left_code_el,
                    name_el_regex=left_name_prefix,
                    credit_el_regex=left_credit_prefix,
                    ects_el_regex=left_ects_prefix,
                    score_el_regex=left_score_prefix,
                    letter_el_regex=left_letter_prefix,
                )
                if course:
                    terms[active_left_idx]["courses"].append(course)

            # Parse right side course
            if right_code_el and active_right_idx is not None:
                course = self._parse_course_from_row_side(
                    tr=tr,
                    side="right",
                    code_el=right_code_el,
                    name_el_regex=right_name_prefix,
                    credit_el_regex=right_credit_prefix,
                    ects_el_regex=right_ects_prefix,
                    score_el_regex=right_score_prefix,
                    letter_el_regex=right_letter_prefix,
                )
                if course:
                    terms[active_right_idx]["courses"].append(course)

        return terms

    def _extract_term_summary_sides(self, baslik_table) -> Tuple[str, str]:
        """
        Summary-side text is stored in the nested baslik table.
        For left/right split columns:
          td[0] -> left summary side
          td[1] -> right summary side
        """
        tr = baslik_table.find("tr")
        if tr:
            tds = tr.find_all("td", recursive=False)
        else:
            tds = baslik_table.find_all("td")

        left_text = (tds[0].get_text(" ", strip=True) if len(tds) > 0 else "") or ""
        right_text = (tds[1].get_text(" ", strip=True) if len(tds) > 1 else "") or ""
        return left_text, right_text

    def _get_text_or_empty(self, el: Optional[Any]) -> str:
        if not el:
            return ""
        return (el.get_text(strip=True) or "").strip()

    def _parse_course_from_row_side(
        self,
        tr,
        side: str,
        code_el,
        name_el_regex: re.Pattern,
        credit_el_regex: re.Pattern,
        ects_el_regex: re.Pattern,
        score_el_regex: re.Pattern,
        letter_el_regex: re.Pattern,
    ) -> Optional[Dict[str, Any]]:
        course_code = self._get_text_or_empty(code_el)
        if not course_code:
            return None

        course_name_el = tr.find(
            lambda tag: tag
            and tag.name == "span"
            and tag.get("id")
            and name_el_regex.match(tag.get("id"))
        )
        credit_el = tr.find(
            lambda tag: tag
            and tag.name == "span"
            and tag.get("id")
            and credit_el_regex.match(tag.get("id"))
        )
        ects_el = tr.find(
            lambda tag: tag
            and tag.name == "span"
            and tag.get("id")
            and ects_el_regex.match(tag.get("id"))
        )
        score_el = tr.find(
            lambda tag: tag
            and tag.name == "span"
            and tag.get("id")
            and score_el_regex.match(tag.get("id"))
        )
        letter_el = tr.find(
            lambda tag: tag
            and tag.name == "span"
            and tag.get("id")
            and letter_el_regex.match(tag.get("id"))
        )

        course_name = self._get_text_or_empty(course_name_el)
        credit = self._get_text_or_empty(credit_el)
        ects = self._get_text_or_empty(ects_el)
        score = self._get_text_or_empty(score_el)
        letter_grade = self._get_text_or_empty(letter_el)

        # Normalize missing markers.
        if score in {"-", "--", "—"}:
            score = ""
        if letter_grade in {"-", "--", "—"}:
            letter_grade = ""

        title = (code_el.get("title") or "").strip()

        # Status detection priority:
        # 1) title keywords (Muaf / Değiştirilen)
        # 2) inline color of score/letter (red/blue/orange)
        status = self._detect_semantic_status(
            title=title,
            score_style=score_el.get("style") if score_el else None,
            letter_style=letter_el.get("style") if letter_el else None,
        )

        if not any([course_code, course_name, credit, ects]):
            return None

        return {
            "course_code": course_code,
            "course_name": course_name,
            "credit": credit,
            "ects": ects,
            "score": score,
            "letter_grade": letter_grade,
            "status": status,
        }

    def _detect_semantic_status(
        self,
        title: str,
        score_style: Optional[str],
        letter_style: Optional[str],
    ) -> str:
        title_norm = _normalize_for_search(title)
        if "muaf" in title_norm:
            return "exempt"
        if "degis" in title_norm and "tir" in title_norm:
            # Handles both Değiştirilen and Degistirilen.
            return "replaced"

        # Inline style detection.
        score_color = _parse_color_from_style(score_style)
        letter_color = _parse_color_from_style(letter_style)
        color_candidate = score_color or letter_color
        if color_candidate:
            mapped = _classify_status_from_color(color_candidate)
            if mapped:
                return mapped

        return "normal"

